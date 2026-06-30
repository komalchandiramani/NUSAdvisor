"""
Run the AGENT evals (EVAL_QUESTIONS) and dump per-question scores to CSV.

Standalone alternative to run_evals.py: no Phoenix server needed, results land
in a CSV you can open in Sheets. Runs each dataset entry through the real agent
(chat_with_log / chat_multi_turn) and applies the existing evaluators.py
functions. NOTE: makes live Gemini calls (agent loop + two LLM-judge evaluators).

Usage:
    python -m evals.run_agent_csv --csv evals/results/before_agent.csv
"""

import sys
import os
import ast
import csv
import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import chat_with_log, chat_multi_turn
from evals.dataset import EVAL_QUESTIONS
from evals.evaluators import (
    tool_calling_eval, call_efficiency_eval, course_exists_eval,
    search_relevance_eval, courses_state_eval,
)

# name -> (fn, takes_input). All return a number except search_relevance (bool).
EVALUATORS = [
    ("tool_calling",    lambda i, o: tool_calling_eval(i, o)),
    ("call_efficiency", lambda i, o: call_efficiency_eval(o)),
    ("course_exists",   lambda i, o: course_exists_eval(o)),
    ("search_relevance", lambda i, o: 1.0 if search_relevance_eval(i, o) else 0.0),
    ("courses_state",   lambda i, o: courses_state_eval(i, o)),
]


def run_task(entry: dict):
    messages = entry.get("messages")
    if isinstance(messages, str):
        try:
            messages = ast.literal_eval(messages)
        except Exception:
            messages = None
    fn = (lambda: chat_multi_turn(messages)) if isinstance(messages, list) \
        else (lambda: chat_with_log(entry["question"]))
    with ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return ex.submit(fn).result(timeout=120)
        except FuturesTimeout:
            print(f"  ⚠️  timeout: {entry.get('question') or entry.get('messages')}")
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, metavar="PATH", help="Output CSV path")
    args = parser.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.csv)), exist_ok=True)

    eval_names = [name for name, _ in EVALUATORS]
    rows = []

    for n, entry in enumerate(EVAL_QUESTIONS, 1):
        label = entry.get("question") or str(entry.get("messages", ""))
        print(f"[{n}/{len(EVAL_QUESTIONS)}] {label[:70]}")
        output = run_task(entry)

        scores = {}
        for name, fn in EVALUATORS:
            try:
                scores[name] = fn(entry, output)
            except Exception as e:
                print(f"    evaluator {name} errored: {e}")
                scores[name] = ""

        actual_tools = [tc["tool_name"] for tc in (output or {}).get("tool_calls", [])]
        rows.append({
            "question": label,
            "expected_tools": entry.get("expected_tools", ""),
            "actual_tools": actual_tools,
            **scores,
            "final_output": ((output or {}).get("final_output") or "")[:300],
        })

    # ── Write per-question CSV ───────────────────────────────
    cols = ["question", "expected_tools", "actual_tools"] + eval_names + ["final_output"]
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # ── Aggregate to console ─────────────────────────────────
    print(f"\n{'EVALUATOR':<20} {'MEAN':>7}  PASSED")
    print("-" * 40)
    for name in eval_names:
        vals = [r[name] for r in rows if isinstance(r[name], (int, float))]
        if vals:
            print(f"{name:<20} {sum(vals)/len(vals):>6.1%}  ({int(sum(vals))}/{len(vals)})")
    print(f"\n📄 Wrote {len(rows)} rows to {args.csv}")


if __name__ == "__main__":
    main()
