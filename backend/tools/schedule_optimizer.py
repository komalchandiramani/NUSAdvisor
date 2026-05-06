"""
Optimize course schedule across remaining semesters.

Flow:
  1. Get career-recommended courses using career_recommender_tool
  2. Parse prerequisite chains to understand dependencies
  3. Build prerequisite DAG and topologically sort
  4. Distribute courses across semesters with load balancing
  5. Return semester-by-semester schedule with workload per semester
"""

from config import CHROMA_PERSIST_DIR
import chromadb
import re
from typing import Set
from tools.career_recommender_tool import career_recommender_tool


# Load ChromaDB collection at module level
db = chromadb.PersistentClient(CHROMA_PERSIST_DIR)
collection = db.get_or_create_collection(name="nus_modules")


def parse_prerequisites(prereq_string: str) -> Set[str]:
    """
    Extract course codes from prerequisite string.

    Handles: "CS1101S", "CS1101S AND CS2030S", "CS1101S OR CS1231S", etc.
    Returns set of all prerequisite course codes (union of AND/OR branches).

    Args:
        prereq_string: Prerequisite string from module metadata

    Returns:
        Set of course codes that are prerequisites
    """
    if not prereq_string:
        return set()

    # Find all 5-6 character codes (like CS1101S, MA1101G)
    pattern = r'\b[A-Z]{2,4}\d{4}[A-Z]?\b'
    codes = re.findall(pattern, prereq_string.upper())
    return set(codes)


def get_module_data(code: str) -> dict | None:
    """
    Fetch module metadata and embedding from ChromaDB.

    Args:
        code: Module code (e.g., "CS1101S")

    Returns:
        Dict with metadata and credits, or None if not found
    """
    result = collection.get(
        ids=[code.upper()],
        include=["metadatas"]
    )

    if not result or not result["metadatas"]:
        return None

    metadata = result["metadatas"][0]
    return {
        "code": code.upper(),
        "title": metadata.get("title", ""),
        "credits": int(metadata.get("credits", 4)),
        "prerequisites": parse_prerequisites(metadata.get("prerequisite", "")),
        "preclusion": metadata.get("preclusion", ""),
    }


def topological_sort_with_balance(
    courses: list[str],
    completed: Set[str],
    semesters_left: int,
    target_credits_per_semester: int = 16
) -> dict:
    """
    Topologically sort courses and distribute across semesters.

    Args:
        courses: List of course codes to schedule
        completed: Set of already-completed course codes
        semesters_left: Number of remaining semesters
        target_credits_per_semester: Target workload per semester (default 16)

    Returns:
        Dict mapping semester -> list of course codes
    """
    schedule = {f"sem_{i+1}": [] for i in range(semesters_left)}

    # Build course info map
    course_info = {}
    for code in courses:
        info = get_module_data(code)
        if info:
            course_info[code] = info
        else:
            # If module not found, assume no prerequisites and 4 credits
            course_info[code] = {
                "code": code,
                "title": "Unknown",
                "credits": 4,
                "prerequisites": set(),
                "preclusion": ""
            }

    # Track which courses can be taken (prerequisites satisfied)
    remaining = set(courses)
    scheduled = set()
    credits_per_sem = {f"sem_{i+1}": 0 for i in range(semesters_left)}

    # Greedy scheduling: iterate through semesters and assign courses
    for sem_idx in range(semesters_left):
        sem_name = f"sem_{sem_idx + 1}"
        available = []

        # Find courses whose prerequisites are all satisfied
        for code in remaining:
            prereqs = course_info[code]["prerequisites"]
            # All prerequisites must either be completed or already scheduled
            if prereqs <= (completed | scheduled):
                available.append((code, course_info[code]["credits"]))

        # Sort by credits (ascending) to fit more courses
        available.sort(key=lambda x: x[1])

        # Greedily pack courses into this semester
        for code, credits in available:
            # Check if adding this course keeps us near target
            new_total = credits_per_sem[sem_name] + credits
            # Allow up to 20 credits per semester (realistic cap)
            if new_total <= 20:
                schedule[sem_name].append(code)
                credits_per_sem[sem_name] += credits
                scheduled.add(code)
                remaining.remove(code)

    # Handle any remaining courses (overscheduled)
    if remaining:
        # Add leftover courses to the last semester or distribute
        leftover = list(remaining)
        for code in leftover:
            # Find semester with least load
            min_sem = min(
                schedule.keys(),
                key=lambda s: credits_per_sem[s]
            )
            schedule[min_sem].append(code)
            credits_per_sem[min_sem] += course_info[code]["credits"]

    # Add workload info
    semesters = list(schedule.keys())
    for sem in semesters:
        schedule[f"{sem}_credits"] = credits_per_sem[sem]
        schedule[f"{sem}_count"] = len(schedule[sem])

    return schedule


def schedule_optimizer(
    semesters_left: int,
    completed_courses: list[str],
    career_goal: str,
    constraints: dict = None
) -> dict:
    """
    Create an optimized course schedule across remaining semesters.

    Args:
        semesters_left: Number of semesters remaining
        completed_courses: List of already-completed course codes
        career_goal: Target career role
        constraints: Optional dict with max_credits_per_sem, etc.

    Returns:
        {
            "schedule": {
                "sem_1": [course codes],
                "sem_1_credits": 16,
                "sem_1_count": 4,
                ...
            },
            "total_courses": int,
            "career_goal": str,
            "feasible": bool,
            "warnings": [str]
        }
    """
    if not constraints:
        constraints = {}

    completed_set = set(c.upper() for c in completed_courses)
    warnings = []

    # Get career recommendations
    recommendations = career_recommender_tool(career_goal, completed_courses)

    if "error" in recommendations:
        return {
            "schedule": {f"sem_{i+1}": [] for i in range(semesters_left)},
            "error": recommendations["error"],
            "feasible": False
        }

    # Collect all recommended courses (all tiers)
    all_recommended = []
    for tier in ["tier_1", "tier_2", "tier_3"]:
        for course in recommendations.get(tier, []):
            all_recommended.append(course["code"])

    if not all_recommended:
        warnings.append("No courses recommended for this career goal")

    # Create schedule
    schedule = topological_sort_with_balance(
        all_recommended,
        completed_set,
        semesters_left,
        constraints.get("target_credits_per_sem", 16)
    )

    # Calculate totals
    total_courses = sum(
        len(courses) for sem, courses in schedule.items()
        if isinstance(courses, list)
    )

    # Feasibility check
    feasible = total_courses == len(all_recommended)
    if not feasible:
        unscheduled = len(all_recommended) - total_courses
        warnings.append(f"{unscheduled} courses could not fit in {semesters_left} semesters")

    return {
        "schedule": schedule,
        "career_goal": recommendations.get("matched_role", career_goal),
        "total_courses_recommended": len(all_recommended),
        "total_courses_scheduled": total_courses,
        "semesters_left": semesters_left,
        "feasible": feasible,
        "warnings": warnings,
        "course_recommendations": {
            "tier_1": [c["code"] for c in recommendations.get("tier_1", [])],
            "tier_2": [c["code"] for c in recommendations.get("tier_2", [])],
            "tier_3": [c["code"] for c in recommendations.get("tier_3", [])],
        }
    }
