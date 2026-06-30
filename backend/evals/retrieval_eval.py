"""
Retrieval eval — measures `search_modules` IN ISOLATION (no agent, no LLM).

Deterministic IR metrics against labeled ground truth (RETRIEVAL_QUERIES in
dataset.py). We have exact relevance labels (module codes), so we compute the
real metrics rather than LLM-estimating them (which is why this isn't RAGAS).

Metrics:
  recall@k : fraction of a query's relevant codes found within the top-k results
  hit@k    : 1 if ANY relevant code is in the top-k, else 0 (known-item retrieval)
  MRR      : mean reciprocal rank of the FIRST relevant code (rank diagnostics —
             tells you WHERE the right module landed, not just whether it's there)

Usage:
    python -m evals.retrieval_eval            # run the eval
    python -m evals.retrieval_eval --verify   # only check labels still exist in DB
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.search_modules import search_modules, get_module_by_code
from evals.dataset import RETRIEVAL_QUERIES

K_VALUES = [1, 3, 5, 10]


def verify_labels() -> bool:
    """Warn on any labeled code that no longer exists in ChromaDB (e.g. after a
    re-ingest). A missing label silently caps recall below 1.0, so check first."""
    missing = []
    for entry in RETRIEVAL_QUERIES:
        for code in entry["relevant"]:
            if get_module_by_code(code) is None:
                missing.append((entry["query"], code))
    if missing:
        print("⚠️  Labeled codes missing from DB (fix these or recall is understated):")
        for query, code in missing:
            print(f"    [{query}] -> {code}")
        return False
    print(f"✅ All labels valid ({sum(len(e['relevant']) for e in RETRIEVAL_QUERIES)} codes across {len(RETRIEVAL_QUERIES)} queries).")
    return True


def evaluate_query(entry: dict, max_k: int) -> dict:
    """Run one query and compute its per-query metrics + rank diagnostics."""
    relevant = set(entry["relevant"])
    results = search_modules(
        query=entry["query"],
        departments=entry.get("departments") or [],
        min_level=entry.get("min_level") or 0,
        n_results=max_k,
    )
    ranked_codes = [r["code"] for r in results]

    # rank (1-indexed) of each relevant code, or None if not retrieved at all
    ranks = {code: (ranked_codes.index(code) + 1 if code in ranked_codes else None)
             for code in relevant}

    recall_at = {}
    hit_at = {}
    precision_at = {}
    for k in K_VALUES:
        found = sum(1 for code in relevant if code in ranked_codes[:k])
        recall_at[k] = found / len(relevant)
        hit_at[k] = 1.0 if found > 0 else 0.0
        # precision@k: of the k returned, how many are labeled relevant.
        # NOTE: only meaningful with reasonably COMPLETE labels. With sparse
        # canonical labels, precision@k is capped at |relevant|/k and measures
        # label gaps, not retrieval quality. Expand labels (--inspect) first.
        precision_at[k] = found / k

    first_rank = min((r for r in ranks.values() if r is not None), default=None)
    rr = 1.0 / first_rank if first_rank else 0.0

    return {"query": entry["query"], "ranks": ranks, "results": results,
            "recall_at": recall_at, "hit_at": hit_at, "precision_at": precision_at, "rr": rr}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Only verify labels exist, don't run the eval")
    parser.add_argument("--inspect", action="store_true",
                        help="Print full top-k per query (relevant marked ✓) to pool/expand labels")
    parser.add_argument("--csv", default=None, metavar="PATH",
                        help="Also write per-query metrics to PATH (Sheets-friendly)")
    args = parser.parse_args()

    if args.verify:
        verify_labels()
        return

    if args.inspect:
        max_k = max(K_VALUES)
        for entry in RETRIEVAL_QUERIES:
            relevant = set(entry["relevant"])
            results = search_modules(
                query=entry["query"],
                departments=entry.get("departments") or [],
                min_level=entry.get("min_level") or 0,
                n_results=max_k,
            )
            filt = f"  [dept={entry['departments']}, min_level={entry.get('min_level')}]" if entry.get("departments") else ""
            print(f"\n▼ {entry['query']}{filt}   (labeled relevant: {sorted(relevant)})")
            for i, r in enumerate(results, 1):
                mark = "✓" if r["code"] in relevant else " "
                print(f"  {mark} {i:>2}. {r['code']:<8} {r['title'][:50]:<50} {r['score']}")
        return

    verify_labels()  # always sanity-check labels before scoring
    max_k = max(K_VALUES)

    # Tag each query by group: filtered = "realistic", unfiltered = "hard-probe".
    # They measure different things, so they get separate aggregates.
    for entry in RETRIEVAL_QUERIES:
        entry["_group"] = "realistic" if entry.get("departments") else "hard-probe"
    per_query = [(e["_group"], evaluate_query(e, max_k)) for e in RETRIEVAL_QUERIES]

    # ── Per-query rank diagnostics ───────────────────────────
    print(f"\nPer-query (rank of each relevant code; '-' = not in top {max_k}):")
    for group, r in per_query:
        ranks_str = ", ".join(f"{c}@{rk if rk else '-'}" for c, rk in r["ranks"].items())
        flag = "" if r["hit_at"][5] else "  ❌ MISS@5"
        print(f"  [{group:<10}] {r['query']:<34} {ranks_str}{flag}")

    # ── Aggregate metrics, per group + overall ───────────────
    def print_aggregate(label, rows):
        if not rows:
            return
        n = len(rows)
        print(f"\n{label} ({n} queries):")
        print(f"  {'k':>3} | {'recall@k':>9} | {'hit@k':>6} | {'precision@k':>11}")
        print(f"  {'-'*3}-+-{'-'*9}-+-{'-'*6}-+-{'-'*11}")
        for k in K_VALUES:
            mr = sum(r["recall_at"][k] for r in rows) / n
            mh = sum(r["hit_at"][k] for r in rows) / n
            mp = sum(r["precision_at"][k] for r in rows) / n
            print(f"  {k:>3} | {mr:>9.3f} | {mh:>6.3f} | {mp:>11.3f}")
        print(f"  MRR: {sum(r['rr'] for r in rows) / n:.3f}")

    print_aggregate("REALISTIC (filtered — production-like)",
                    [r for g, r in per_query if g == "realistic"])
    print_aggregate("HARD-PROBE (unfiltered — embedding-sensitivity)",
                    [r for g, r in per_query if g == "hard-probe"])
    print_aggregate("OVERALL", [r for _, r in per_query])
    print("\n  ⚠️  precision@k is understated until labels are complete — run --inspect to pool/expand labels.")

    if args.csv:
        write_csv(per_query, args.csv)
        print(f"\n  📄 Wrote per-query metrics to {args.csv}")


def write_csv(per_query, path):
    """One row per query, all metrics flattened — open directly in Sheets."""
    import csv
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    cols = (["group", "query", "ranks"]
            + [f"recall@{k}" for k in K_VALUES]
            + [f"hit@{k}" for k in K_VALUES]
            + [f"precision@{k}" for k in K_VALUES]
            + ["reciprocal_rank"])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for group, r in per_query:
            ranks_str = "; ".join(f"{c}@{rk if rk else '-'}" for c, rk in r["ranks"].items())
            row = ([group, r["query"], ranks_str]
                   + [round(r["recall_at"][k], 4) for k in K_VALUES]
                   + [round(r["hit_at"][k], 4) for k in K_VALUES]
                   + [round(r["precision_at"][k], 4) for k in K_VALUES]
                   + [round(r["rr"], 4)])
            w.writerow(row)


if __name__ == "__main__":
    main()