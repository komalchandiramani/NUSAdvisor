"""
Fetch modules from NUSMods API, embed them, store in ChromaDB.

Usage:
    python ingest.py
    python ingest.py --dry-run
"""

import argparse
import json
import time
from pathlib import Path
from tqdm import tqdm

import requests

import chromadb
from sentence_transformers import SentenceTransformer
import re

from config import (
    NUSMODS_BASE_URL,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    get_current_academic_year,
)


# ── API fetching ────────────────────────────

def fetch_module_list(year: str) -> list[dict]:
    resp = requests.get(f"{NUSMODS_BASE_URL}/{year}/moduleList.json", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_module_detail(year: str, code: str) -> dict | None:
    resp = requests.get(f"{NUSMODS_BASE_URL}/{year}/modules/{code}.json", timeout=30)
    return resp.json() if resp.status_code == 200 else None


def fetch_department_dict(year: str) -> dict[str, str]:
    """Return {department_name: faculty_name} for all NUS departments."""
    resp = requests.get(f"{NUSMODS_BASE_URL}/{year}/facultyDepartments.json", timeout=30)
    resp.raise_for_status()
    faculty_departments: dict[str, list[str]] = resp.json()
    return {dept: faculty for faculty, depts in faculty_departments.items() for dept in depts}


def build_metadata(mod: dict) -> dict:
    """Build metadata dict for ChromaDB storage. This gets stored alongside
    the embedding so you can filter/display results without re-fetching."""
    semesters = [sd.get("semester") for sd in mod.get("semesterData", [])]
    m = re.search(r"\d", mod["moduleCode"])
    level = int(m.group()) * 1000 if m else 0
                  
    return {
        "code": mod["moduleCode"],
        "title": mod["title"],
        "credits": int(mod.get("moduleCredit", 0)),
        "department": mod.get("department", ""),
        "faculty": mod.get("faculty", ""),
        "prerequisite": mod.get("prerequisite") or "",
        "preclusion": mod.get("preclusion") or "",
        "semesters": json.dumps(semesters),
        "description": (mod.get("description") or "")[:500],
        "course_level": level,
    }



# Combine moduleCode, title, description, prerequisites, workload into one string.
def build_document_text(mod: dict) -> str:

    parts = [
        f"{mod['moduleCode']}: {mod['title']}",
        mod.get("description") or "",
    ]

    if mod.get("prerequisite"):
        parts.append(f"Prerequisites:  {mod['prerequisite']}")
    if mod.get("workload"):
        parts.append(f"Workload: {mod.get('workload')}")

    return "\n".join(parts)




# ── Initialize ChromaDB ──────────────────────────
def init_chromadb():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    mods_collection = chroma_client.get_or_create_collection(
        name="nus_modules", 
        metadata={"hnsw:space": "cosine"}
    )
    dept_collection = chroma_client.get_or_create_collection(
        name="nus_departments",
        metadata={"hnsw:space": "cosine"}
    )
    
    return mods_collection, dept_collection


# ── Load the embedding model ─────────────────────
def load_embedding_model():
    model = SentenceTransformer(EMBEDDING_MODEL)
    return model


# ── Main ingestion logic ─────────────────────────────────
def run_ingest(dry_run: bool = False):
    year = get_current_academic_year()
    print(f"Academic year: {year}")

    print("Fetching department dictionary...")
    dept_dict = fetch_department_dict(year)

    dept_path = Path(CHROMA_PERSIST_DIR).parent / "departments.json"
    dept_path.parent.mkdir(parents=True, exist_ok=True)

    dept_path.write_text(json.dumps(dept_dict, indent=2, sort_keys=True))
    print(f"Saved {len(dept_dict)} departments across {len(set(dept_dict.values()))} faculties → {dept_path}")

    print("Fetching module list...")
    all_modules = fetch_module_list(year)
    print(f"Found {len(all_modules)} total modules")

    if dry_run:
        for m in all_modules[:20]:
            print(f"  {m['moduleCode']}: {m['title']}")
        if len(all_modules) > 20:
            print(f"  ... and {len(all_modules) - 20} more")
        return

    model = load_embedding_model()
    mods_collection, dept_collection = init_chromadb()


    # ── Embed departments into ChromaDB ──────────────────
    print("Embedding departments...")
    dept_ids, dept_docs, dept_embeddings, dept_metadatas = [], [], [], []
    for dept, faculty in dept_dict.items():
        doc_text = f"{dept}, Faculty of {faculty}"
        embedding = model.encode(doc_text, normalize_embeddings=True).tolist()

        dept_ids.append(dept)
        dept_docs.append(doc_text)
        dept_embeddings.append(embedding)
        dept_metadatas.append({
            "department": dept,
            "faculty": faculty,
        })

    dept_collection.upsert(
        ids=dept_ids,
        embeddings=dept_embeddings,
        metadatas=dept_metadatas,
        documents=dept_docs,
    )
    print(f"Embedded {len(dept_ids)} departments into ChromaDB (collection: nus_departments)")


    # ── Embed modules into ChromaDB ──────────────────
    ids, documents, embeddings, metadatas = [], [], [], []
    failed = []

    for m in tqdm(all_modules, desc="Embedding modules", total=len(all_modules)):
        detail = fetch_module_detail(year, m["moduleCode"])
        if not detail:
            failed.append(m["moduleCode"])
            continue

        doc_text = build_document_text(detail) 

        #Encode doc_text into an embedding vector
        embedding = model.encode(doc_text, normalize_embeddings=True).tolist()

        ids.append(m["moduleCode"])
        documents.append(doc_text)
        embeddings.append(embedding)
        metadatas.append(build_metadata(detail))

        time.sleep(0.05)

    # Upsert everything into ChromaDB in batches of 100 ──────────
    batch_size = 100
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        mods_collection.upsert(
            ids = ids[start:end],
            embeddings = embeddings[start:end],
            metadatas = metadatas[start:end],
            documents = documents[start:end]
        )
    print(f"Embedded {len(ids)} modules into ChromaDB (collection: nus_modules)")

    current_codes = set(ids)
    existing = mods_collection.get(include=[])
    stale = [id for id in existing["ids"] if id not in current_codes]
    if stale:
        mods_collection.delete(ids=stale)
        print(f"Removed {len(stale)} stale modules: {', '.join(stale)}")

    print(f"\nDone! {len(ids)} modules processed, {len(failed)} failed.")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview modules without embedding")
    args = parser.parse_args()
    run_ingest(dry_run=args.dry_run)
