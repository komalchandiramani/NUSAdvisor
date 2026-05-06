import re
import time
from tools.search_modules import get_module_by_code
from prompts import RELEVANCE_PROMPT, EXTRACT_CODES_PROMPT
from google import genai
from dotenv import load_dotenv
import os
import ast

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def tool_calling_eval(input, output) -> float:
    if output is None:
        return 0.0

    expected = input.get("expected_tools", [])
    if isinstance(expected, str):
        expected = ast.literal_eval(expected)

    called = [tc["tool_name"] for tc in output.get("tool_calls", [])]

    if not all(t in called for t in expected):
        return 0.0

    indices = [called.index(t) for t in expected]
    if indices != sorted(indices):
        return 0.0

    return 1.0


def call_efficiency_eval(output) -> float:
    if output is None:
        return 0.0
    tool_calls = output.get("tool_calls", [])
    search_calls = [tc["tool_args"] for tc in tool_calls if tc["tool_name"] == "search_modules_tool"]

    if len(search_calls) <= 1:
        return 1.0

    # check if any earlier call's args are a subset of a later call's args
    for i in range(len(search_calls)):
        for j in range(i + 1, len(search_calls)):
            earlier = {k: v for k, v in search_calls[i].items() if v is not None}
            later = {k: v for k, v in search_calls[j].items() if v is not None}
            if earlier.items() <= later.items():
                return 0.0

    return 1.0


def course_exists_eval(output) -> float:
    if output is None:
        return 0.0

    final_output = output.get("final_output", "")
    if not final_output:
        return 1.0

    # Codes that came verbatim from tool responses are real NUS codes — they may
    # simply be missing from our DB (e.g. YSC*, R-suffix legacy codes, D/T variants).
    # Exclude them so we only penalise codes the LLM independently invented.
    # Use {0,2} suffix to also capture two-letter variants like CS2103DE.
    tool_response_codes = set()
    for tr in output.get("tool_responses", []):
        tool_response_codes.update(re.findall(r'\b[A-Z]{2,4}\d{4}[A-Z]{0,3}\b', tr.get("tool_response", "")))

    prompt = EXTRACT_CODES_PROMPT.format(text=final_output)
    try:
        response = _client.models.generate_content(
            model=os.getenv("GEMINI_MODEL"),
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        import json
        text = response.text.strip().replace("```json", "").replace("```", "")
        codes = json.loads(text)
    except Exception:
        codes = re.findall(r'\b[A-Z]{2,4}\d{4}[A-Z]{0,3}\b', final_output)

    if not codes:
        return 1.0

    codes_to_check = [c for c in codes if c not in tool_response_codes]
    if not codes_to_check:
        return 1.0

    valid = [c for c in codes_to_check if get_module_by_code(c) is not None]
    return len(valid) / len(codes_to_check)


def search_relevance_eval(input, output) -> bool:
    if output is None:
        return False

    question = input.get("question")
    if not isinstance(question, str):
        messages = input.get("messages", [])
        question = " / ".join(messages) if isinstance(messages, list) else ""

    prompt = RELEVANCE_PROMPT.format(
        question=question,
        response=output.get("final_output", "")
    )

    label, _ = gemini_judge(prompt, ["relevant", "irrelevant"])
    return label == "relevant"


def courses_state_eval(input, output) -> float:
    if output is None:
        return 0.0
    expected_taken = input.get("expected_courses_taken", [])
    expected_planned = input.get("expected_courses_planned", [])
    if isinstance(expected_taken, str):
        expected_taken = ast.literal_eval(expected_taken)
    elif not isinstance(expected_taken, list):
        expected_taken = []
    if isinstance(expected_planned, str):
        expected_planned = ast.literal_eval(expected_planned)
    elif not isinstance(expected_planned, list):
        expected_planned = []
    if not expected_taken and not expected_planned:
        return 1.0
    actual_taken = output.get("courses_taken", [])
    actual_planned = output.get("courses_planned", [])
    if not all(c in actual_taken for c in expected_taken):
        return 0.0
    if not all(c in actual_planned for c in expected_planned):
        return 0.0
    return 1.0


def gemini_judge(prompt: str, rails: list[str], retries: int = 3, backoff: float = 5.0) -> tuple[str, str]:
    last_err = None
    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            text = response.text
            for rail in rails:
                if f'"{rail}"' in text.lower() or f'label: {rail}' in text.lower():
                    return rail, text
            return rails[-1], text
        except Exception as e:
            last_err = e
            print(f"gemini_judge failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    return rails[-1], f"ERROR: {last_err}"
