"""
Recommend NUS courses for a target career goal using SkillsFuture data.

Flow:
  career_goal + completed_courses
    → fuzzy match goal to 1,910 job roles in SkillsFuture dataset
    → get required skills grouped into tiers (foundation/intermediate/advanced)
    → search_modules(skill) for each skill gap
    → return ranked course recommendations per tier
"""

import openpyxl
from rapidfuzz import process as fuzz_process
from config import SKILLS_DATASET_PATH
from search import search_modules


# ── Load SkillsFuture data once at module level ───────────

def _load_skills_data() -> dict[str, list[tuple[str, int]]]:
    """
    Parse the SkillsFuture Excel into:
        { "Data Scientist": [("Data Analytics", 3), ("Python", 2), ...], ... }
    Uses sheet: Job Role_TCS_CCS
    Columns: Sector, Track, Job Role, TSC_CCS Title, TSC_CCS Type, Proficiency Level, Code
    """
    wb = openpyxl.load_workbook(SKILLS_DATASET_PATH, read_only=True, data_only=True)
    ws = wb["Job Role_TCS_CCS"]

    data = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # skip header
        _, _, job_role, skill_title, _, proficiency_level, _ = row
        if not job_role or not skill_title:
            continue
        if job_role not in data:
            data[job_role] = []
        try:
            level = int(proficiency_level)
        except (TypeError, ValueError):
            level = 0
        data[job_role].append((skill_title, level))

    return data


# Loaded once when the module is first imported
SKILLS_DATA = _load_skills_data()
ALL_ROLES = list(SKILLS_DATA.keys())


# ── Helper functions ──────────────────────────────────────

def match_career_goal(career_goal: str, score_cutoff: int = 60) -> str | None:
    """
    Fuzzy match user's career goal string to a job role in the dataset.

    Returns the best matching job role string, or None if no good match found.
    """
    result = fuzz_process.extractOne(career_goal, ALL_ROLES, score_cutoff=score_cutoff)
    return result[0] if result is not None else None


def get_skills_by_tier(job_role: str) -> dict[str, list[str]]:
    """
    Group skills for a job role into three tiers by proficiency level.

    Tier mapping:
        tier_1 (foundation):    proficiency levels 1-2
        tier_2 (intermediate):  proficiency levels 3-4
        tier_3 (advanced):      proficiency levels 5-6
    """
    tiers = {"tier_1": [], "tier_2": [], "tier_3": []}

    for skill, level in SKILLS_DATA.get(job_role, []):
        if level <= 2:
            tiers["tier_1"].append(skill)
        elif level <= 4:
            tiers["tier_2"].append(skill)
        else:
            tiers["tier_3"].append(skill)

    return tiers


def career_recommender_tool(career_goal: str, completed_courses: list[str]) -> dict:
    """
    Recommend NUS courses for a career goal, skipping already-completed courses.

    Args:
        career_goal: Target career (e.g., "Data Scientist", "UX Designer")
        completed_courses: List of module codes already done (e.g., ["CS1101S", "CS2040S"])

    Returns:
        {
            "matched_role": "Data Scientist",
            "tier_1": [{"code": ..., "title": ..., "score": ...}, ...],
            "tier_2": [...],
            "tier_3": [...],
        }
        Or {"error": "..."} if no matching role found.
    """
    matched_role = match_career_goal(career_goal)
    if matched_role is None:
        return {"error": f"No matching role found for '{career_goal}'. Try a more specific job title."}

    tiers = get_skills_by_tier(matched_role)
    completed_set = set(c.upper() for c in completed_courses)

    result = {"matched_role": matched_role, "tier_1": [], "tier_2": [], "tier_3": []}

    for tier_key, skills in tiers.items():
        seen_codes = set()
        for skill in skills:
            courses = search_modules(skill, n_results=3)
            for course in courses:
                code = course.get("code", "").upper()
                # Skip if already completed or already added in this tier
                if code in completed_set or code in seen_codes:
                    continue
                seen_codes.add(code)
                result[tier_key].append({
                    "code": code,
                    "title": course.get("title", ""),
                    "score": round(course.get("score", 0), 3),
                    "matched_skill": skill,
                })

        # Sort each tier by relevance score descending
        result[tier_key].sort(key=lambda x: x["score"], reverse=True)

    return result
