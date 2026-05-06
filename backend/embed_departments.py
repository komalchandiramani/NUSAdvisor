# embed_departments.py (or run in a notebook cell)

import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

# Load what you already have
model = SentenceTransformer(EMBEDDING_MODEL)
dept_dict = json.loads(Path("data/departments.json").read_text())

# Connect to existing ChromaDB and create new collection
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
dept_collection = chroma_client.get_or_create_collection(
    name="nus_departments",
    metadata={"hnsw:space": "cosine"}
)

# Embed and upsert
dept_ids, dept_docs, dept_embeddings, dept_metadatas = [], [], [], []

for dept, faculty in dept_dict.items():
    doc_text = f"{dept}, Faculty of {faculty}"
    embedding = model.encode(doc_text).tolist()

    dept_ids.append(dept)
    dept_docs.append(doc_text)
    dept_embeddings.append(embedding)
    dept_metadatas.append({"department": dept, "faculty": faculty})

dept_collection.upsert(
    ids=dept_ids,
    embeddings=dept_embeddings,
    metadatas=dept_metadatas,
    documents=dept_docs,
)

print(f"Done! Embedded {len(dept_ids)} departments into ChromaDB (nus_departments)")