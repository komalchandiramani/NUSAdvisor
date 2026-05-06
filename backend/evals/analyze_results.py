"""
Fetch and display eval results + trace summary for a given experiment.

Usage:
    python -m evals.analyze_results --experiment <experiment_id>

Defaults to the latest experiment on the nusadvisor-test-v3 dataset.
"""
import sys
import os
import argparse
import json
import subprocess
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from phoenix.client import Client

PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://127.0.0.1:6006")
DATASET_NAME = "nusadvisor-test-v3"


def get_latest_experiment_id(client: Client) -> str:
    experiments = list(client.experiments.list(dataset_name=DATASET_NAME))
    if not experiments:
        raise RuntimeError(f"No experiments found for dataset '{DATASET_NAME}'")
    latest = sorted(experiments, key=lambda e: e.get("created_at", ""), reverse=True)[0]
    return latest["id"]


def fetch_runs(experiment_id: str) -> list:
    result = subprocess.run(
        ["npx", "--yes", "@arizeai/phoenix-cli@latest", "experiment", "get", experiment_id,
         "--format", "raw", "--no-progress"],
        capture_output=True, text=True,
        env={**os.environ, "PHOENIX_HOST": PHOENIX_HOST},
    )
    start = result.stdout.find('[{"example_id"')
    if start == -1:
        raise RuntimeError(f"Unexpected output:\n{result.stdout[:500]}\n{result.stderr[:500]}")
    return json.loads(result.stdout[start:])


def print_summary(runs: list):
    scores = defaultdict(list)
    for run in runs:
        for ann in run.get("annotations", []):
            if ann.get("score") is not None:
                scores[ann["name"]].append(ann["score"])

    print(f"\n{'='*55}")
    print(f"{'EVALUATOR':<30} {'SCORE':>7}  PASSED")
    print(f"{'='*55}")
    for name, vals in sorted(scores.items()):
        avg = sum(vals) / len(vals)
        print(f"{name:<30} {avg:>6.1%}  ({int(sum(vals))}/{len(vals)})")
    print()


def print_failures(runs: list):
    fails = defaultdict(list)
    for run in runs:
        q = run["input"].get("question") or str(run["input"].get("messages", ""))
        for ann in run.get("annotations", []):
            if ann.get("score") is not None and ann["score"] < 1.0:
                fails[ann["name"]].append({
                    "question": q[:120],
                    "expected_tools": run["input"].get("expected_tools", ""),
                    "actual_tools": [tc["tool_name"] for tc in (run.get("output") or {}).get("tool_calls", [])],
                    "score": ann["score"],
                    "label": ann.get("label"),
                    "output_snippet": ((run.get("output") or {}).get("final_output") or "")[:200],
                })

    for eval_name, cases in sorted(fails.items()):
        print(f"\n{'='*60}")
        print(f"FAILING: {eval_name}  ({len(cases)} failures)")
        print("="*60)
        for c in cases:
            print(f"\n  Q: {c['question']}")
            print(f"  Expected tools : {c['expected_tools']}")
            print(f"  Actual tools   : {c['actual_tools']}")
            print(f"  Score: {c['score']:.3f}  Label: {c['label']}")
            print(f"  Output: {c['output_snippet']}")


def fetch_traces(project_name: str, limit: int = 50) -> list:
    result = subprocess.run(
        ["npx", "@arizeai/phoenix-cli@latest", "trace", "list",
         "--limit", str(limit), "--format", "raw", "--no-progress"],
        capture_output=True, text=True,
        env={**os.environ, "PHOENIX_HOST": PHOENIX_HOST, "PHOENIX_PROJECT": project_name},
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Could not parse traces: {result.stdout[:300]}")
        return []


def print_trace_summary(traces: list):
    if not traces:
        print("No traces found.")
        return

    statuses = defaultdict(int)
    durations = []
    errors = []
    for t in traces:
        statuses[t.get("status", "UNKNOWN")] += 1
        if t.get("duration"):
            durations.append(t["duration"])
        if t.get("status") == "ERROR":
            errors.append(t)

    print(f"\n{'='*55}")
    print("TRACE SUMMARY")
    print(f"{'='*55}")
    print(f"Total traces : {len(traces)}")
    for s, count in sorted(statuses.items()):
        print(f"  {s:<10}: {count}")
    if durations:
        print(f"Duration     : avg={sum(durations)/len(durations)/1000:.1f}s  "
              f"min={min(durations)/1000:.1f}s  max={max(durations)/1000:.1f}s")
    if errors:
        print(f"\nERROR traces ({len(errors)}):")
        for e in errors:
            spans = e.get("spans", [])
            err_spans = [s for s in spans if s.get("status_code") == "ERROR"]
            for sp in err_spans:
                msg = (sp.get("attributes") or {}).get("exception.message", "")
                print(f"  [{e['traceId'][:12]}] {sp['name']}: {msg[:120]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default=None, help="Experiment ID (defaults to latest)")
    parser.add_argument("--traces", action="store_true", help="Also fetch and display traces")
    args = parser.parse_args()

    client = Client()

    exp_id = args.experiment
    if not exp_id:
        print(f"Fetching latest experiment for '{DATASET_NAME}'...")
        exp_id = get_latest_experiment_id(client)

    exp = client.experiments.get(experiment_id=exp_id)
    print(f"\nExperiment : {exp_id}")
    print(f"Dataset    : {DATASET_NAME}")
    print(f"Runs       : {exp.get('successful_run_count')}/{exp.get('example_count')} successful")
    print(f"Project    : {exp.get('project_name')}")

    print("\nFetching runs (this may take a moment)...")
    runs = fetch_runs(exp_id)

    print_summary(runs)
    print_failures(runs)

    if args.traces:
        project = exp.get("project_name", "")
        print(f"\nFetching traces from project '{project}'...")
        traces = fetch_traces(project)
        print_trace_summary(traces)


if __name__ == "__main__":
    main()
