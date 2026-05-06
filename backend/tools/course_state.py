from tools.search_modules import get_module_by_code


def _update_course_list(current: list[str], codes: list[str], action: str) -> tuple[list[str], list[str]]:
    if action == "clear":
        return [], []
    valid = [c for c in codes if get_module_by_code(c) is not None]
    invalid = [c for c in codes if c not in valid]
    if action == "add":
        return current + [c for c in valid if c not in current], invalid
    return [c for c in current if c not in valid], invalid
