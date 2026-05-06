"""
Analyze skill gaps for a career goal.

Flow:
  1. Match career goal to a job role
  2. Get required skills by tier (foundation/intermediate/advanced)
  3. Infer completed skills from completed courses
  4. Find missing skills per tier
  5. Rank by importance (tier level) and suggest courses
"""

from config import CHROMA_PERSIST_DIR
import chromadb
from tools.career_recommender_tool import match_career_goal, get_skills_by_tier
from search import search_modules


# Load ChromaDB collection at module level
db = chromadb.PersistentClient(CHROMA_PERSIST_DIR)
collection = db.get_or_create_collection(name="nus_modules")


def infer_skills_from_course(code: str) -> set:
    """
    Infer which skills a course teaches based on its metadata.

    Args:
        code: Module code

    Returns:
        Set of skill names likely covered by this course
    """
    result = collection.get(
        ids=[code.upper()],
        include=["metadatas"]
    )

    if not result or not result["metadatas"]:
        return set()

    metadata = result["metadatas"][0]
    title = metadata.get("title", "").lower()
    description = metadata.get("description", "").lower()

    # Keywords that map to skills
    skill_keywords = {
        "data analysis": ["data", "analysis", "analytics", "statistics", "stat"],
        "python": ["python"],
        "machine learning": ["machine learning", "ml", "neural", "deep learning", "classification", "regression"],
        "databases": ["database", "sql", "nosql", "mongodb", "postgres"],
        "software engineering": ["software", "engineering", "design", "architecture", "pattern"],
        "web development": ["web", "html", "css", "javascript", "react", "frontend", "backend"],
        "cloud computing": ["cloud", "aws", "azure", "gcp", "docker", "kubernetes"],
        "algorithm design": ["algorithm", "algorithms", "data structure", "complexity"],
        "statistics": ["statistics", "statistical", "probability", "distribution"],
        "visualization": ["visualization", "visual", "chart", "plot", "graph", "tableau", "power bi"],
    }

    found_skills = set()
    combined_text = title + " " + description

    for skill, keywords in skill_keywords.items():
        for keyword in keywords:
            if keyword in combined_text:
                found_skills.add(skill)
                break

    return found_skills


def get_completed_skills(completed_courses: list[str]) -> set:
    """
    Aggregate skills from all completed courses.

    Args:
        completed_courses: List of module codes

    Returns:
        Set of all skills covered by completed courses
    """
    completed_skills = set()
    for code in completed_courses:
        skills = infer_skills_from_course(code)
        completed_skills.update(skills)

    return completed_skills


def skill_gap_analyzer(completed_courses: list[str], career_goal: str) -> dict:
    """
    Analyze skill gaps for a career goal.

    Args:
        completed_courses: List of already-completed module codes
        career_goal: Target career role

    Returns:
        {
            "career_goal": "matched role",
            "total_required_skills": int,
            "completed_skills": [...],
            "gaps": {
                "tier_1": [{"skill": "...", "importance": "foundation", ...}, ...],
                "tier_2": [...],
                "tier_3": [...]
            },
            "coverage": {
                "tier_1": "X/Y",
                "tier_2": "X/Y",
                "tier_3": "X/Y",
                "overall": "percentage"
            }
        }
    """
    # Match career goal
    matched_role = match_career_goal(career_goal)
    if matched_role is None:
        return {
            "error": f"No matching role found for '{career_goal}'. Try a more specific job title."
        }

    # Get required skills by tier
    required_tiers = get_skills_by_tier(matched_role)

    # Get completed skills
    completed_skills = get_completed_skills(completed_courses)

    # Find gaps and coverage per tier
    gaps = {"tier_1": [], "tier_2": [], "tier_3": []}
    coverage = {}

    for tier_key, required_skills in required_tiers.items():
        # Remove duplicates from required_skills
        unique_required = list(set(required_skills))

        # Find missing skills
        missing = [s for s in unique_required if s not in completed_skills]

        # Build gap entries with course suggestions
        for skill in missing:
            courses = search_modules(skill, n_results=2)
            gaps[tier_key].append({
                "skill": skill,
                "importance": tier_key,
                "suggested_courses": [
                    {"code": c.get("code"), "title": c.get("title"), "score": round(c.get("score", 0), 3)}
                    for c in courses
                ]
            })

        # Calculate coverage
        completed_in_tier = sum(1 for s in unique_required if s in completed_skills)
        coverage[tier_key] = f"{completed_in_tier}/{len(unique_required)}"

    # Overall coverage
    total_required = sum(len(set(s)) for s in required_tiers.values())
    total_completed = len(completed_skills)
    overall_pct = int((total_completed / total_required * 100)) if total_required > 0 else 0

    return {
        "career_goal": matched_role,
        "total_required_skills": total_required,
        "completed_skills_count": len(completed_skills),
        "completed_skills": sorted(list(completed_skills)),
        "gaps": gaps,
        "coverage": {
            **coverage,
            "overall": f"{overall_pct}%"
        },
        "gap_count": {
            "tier_1": len(gaps["tier_1"]),
            "tier_2": len(gaps["tier_2"]),
            "tier_3": len(gaps["tier_3"]),
            "total": sum(len(v) for v in gaps.values())
        }
    }
