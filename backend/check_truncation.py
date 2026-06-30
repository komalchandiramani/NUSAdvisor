"""
Audit which module documents would be truncated by the embedding model.

The model truncates by TOKENS (not words/chars) at `max_seq_length`, and that
limit already includes special tokens like [CLS]/[SEP]. So we tokenize each
doc_text WITH special tokens using the model's own tokenizer and compare the
count directly to max_seq_length.

Usage:
    python check_truncation.py
"""

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from config import EMBEDDING_MODEL, get_current_academic_year
from ingest import (
    fetch_module_list,
    fetch_module_detail,
    build_document_text,
)


def main():
    year = get_current_academic_year()
    model = SentenceTransformer(EMBEDDING_MODEL)
    max_len = model.max_seq_length
    tokenizer = model.tokenizer

    print(f"Model: {EMBEDDING_MODEL}")
    print(f"max_seq_length: {max_len} tokens (text budget after special tokens)\n")

    modules = fetch_module_list(year)

    over_limit = []
    token_counts = []

    for m in tqdm(modules, desc="Checking", total=len(modules)):
        detail = fetch_module_detail(year, m["moduleCode"])
        if not detail:
            continue

        doc_text = build_document_text(detail)

        # Tokenize exactly as the model would, including special tokens.
        n_tokens = len(tokenizer.encode(doc_text, add_special_tokens=True))
        token_counts.append(n_tokens)

        if n_tokens > max_len:
            over_limit.append((m["moduleCode"], n_tokens))

    # ── Report ──────────────────────────────────
    print(f"\nChecked {len(token_counts)} modules.")
    if token_counts:
        print(f"Token length — min: {min(token_counts)}, "
              f"max: {max(token_counts)}, "
              f"avg: {sum(token_counts) // len(token_counts)}")

    if over_limit:
        over_limit.sort(key=lambda x: -x[1])
        print(f"\n⚠️  {len(over_limit)} modules EXCEED {max_len} tokens "
              f"(text past token {max_len} is dropped from the embedding):")
        for code, n in over_limit[:30]:
            print(f"  {code}: {n} tokens  (losing ~{n - max_len})")
        if len(over_limit) > 30:
            print(f"  ... and {len(over_limit) - 30} more")
    else:
        print(f"\n✅ No modules exceed {max_len} tokens. Nothing is truncated.")


if __name__ == "__main__":
    main()
