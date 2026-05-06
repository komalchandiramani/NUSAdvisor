import re
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
        # fall back to regex if LLM fails
        codes = re.findall(r'\b[A-Z]{2,4}\d{4}[A-Z]?\b', final_output)

    if not codes:
        return 1.0

    valid = [c for c in codes if get_module_by_code(c) is not None]
    return len(valid) / len(codes)


def search_relevance_eval(input, output) -> bool:
    if output is None:
        return False

    prompt = RELEVANCE_PROMPT.format(
        question=input["question"],
        response = output.get("final_output", "")
    )

    label, _ = gemini_judge(prompt, ["relevant", "irrelevant"])
    return label == "relevant"



def gemini_judge(prompt: str, rails: list[str]) -> tuple[str, str]:
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
        print(f"gemini_judge failed: {e}")
        return rails[-1], f"ERROR: {e}"
    
