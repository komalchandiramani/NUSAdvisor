import chromadb
from sentence_transformers import SentenceTransformer
from config import (CHROMA_PERSIST_DIR, EMBEDDING_MODEL, DEPARTMENTS_COLLECTION, 
                    MODULES_COLLECTION, CHROMA_SPACE)

# One client, one model — shared across all tools
model = SentenceTransformer(EMBEDDING_MODEL)
db = chromadb.PersistentClient(CHROMA_PERSIST_DIR)

modules_collection = db.get_or_create_collection(name=MODULES_COLLECTION, metadata={"hnsw:space": CHROMA_SPACE})
dept_collection = db.get_or_create_collection(name=DEPARTMENTS_COLLECTION, metadata={"hnsw:space": CHROMA_SPACE})