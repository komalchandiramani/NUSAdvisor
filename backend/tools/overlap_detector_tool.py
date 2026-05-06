"""
Detect overlapping/redundant courses in a list using hybrid similarity.

Combines embedding similarity (semantic overlap) + metadata similarity (structural overlap)
to identify courses that teach similar content or have similar prerequisites.
"""

from config import CHROMA_PERSIST_DIR
import chromadb
import numpy as np
from rapidfuzz.distance import Levenshtein


# Load model and collection at module level (once, not per request)
db = chromadb.PersistentClient(CHROMA_PERSIST_DIR)
collection = db.get_or_create_collection(name="nus_modules")


def compute_embedding_similarity(emb_a: list, emb_b: list) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        emb_a: Embedding vector for course A
        emb_b: Embedding vector for course B

    Returns:
        Similarity score (0-1), where 1 = identical
    """
    # Convert to numpy arrays
    a = np.array(emb_a)
    b = np.array(emb_b)

    # Cosine similarity = dot(a,b) / (norm(a) * norm(b))
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = dot_product / (norm_a * norm_b)
    # Cosine similarity ranges [-1, 1], normalize to [0, 1]
    return max(0, (similarity + 1) / 2)



def compute_metadata_similarity(metadata_a: dict, metadata_b: dict) -> float:
    """
    Compute metadata-based similarity (0-1 scale).

    Factors:
    - Title/description similarity (65%)
    - Credit similarity (15%)
    - Department match (20%)

    Args:
        metadata_a: Metadata for course A
        metadata_b: Metadata for course B

    Returns:
        Overall metadata similarity (0-1)
    """

    title_a = metadata_a.get("title", "")
    title_b = metadata_b.get("title", "")

    # Levenshtein distance between titles
    l_dist = Levenshtein.distance(title_a, title_b)
    max_len = max(len(title_a), len(title_b))
    title_sim = 1.0 if max_len == 0 else (1 - (l_dist / max_len))

    # Credit similarity (normalize to 0-1)
    credits_a = int(metadata_a.get("credits", 0))
    credits_b = int(metadata_b.get("credits", 0))

    if credits_a == 0 and credits_b == 0:
        credit_sim = 1.0
    elif credits_a == 0 or credits_b == 0:
        credit_sim = 0.0
    else:
        credit_diff = abs(credits_a - credits_b)
        credit_sim = max(0, 1 - (credit_diff / max(credits_a, credits_b)))

    # Exact department match 
    dept_a = metadata_a.get("department", "").lower()
    dept_b = metadata_b.get("department", "").lower()
    dept_sim = 1.0 if dept_a == dept_b else 0.0

    weights = {
        'title': 0.65,
        'credit': 0.15,
        'dept': 0.20,
    }

    overall = (
        weights['title'] * title_sim +
        weights['credit'] * credit_sim +
        weights['dept'] * dept_sim
    )

    return overall


def overlap_detector_tool(course_codes: list[str], similarity_threshold: float = 0.5) -> list[dict]:
    """
    Find overlapping/redundant courses in a list.

    Args:
        course_codes: List of course codes to compare (e.g., ["CS1101S", "CS1231S"])
        similarity_threshold: Minimum similarity to report (default 0.5)

    Returns:
        List of course pairs with high overlap, sorted by overall_similarity (descending)

    Raises:
        ValueError: If fewer than 2 courses provided
    """
    if len(course_codes) < 2:
        raise ValueError("Need at least 2 courses to detect overlap")

    modules_data = {} 

    for code in course_codes:
        result = collection.get(
            ids=[code.upper()],
            include=["metadatas", "embeddings"]
        )

        if not result or not result["metadatas"]:
            print(f"Warning: Course {code} not found, skipping")
            continue

        modules_data[code.upper()] = {
            "metadata": result["metadatas"][0],
            "embedding": result["embeddings"][0] if result["embeddings"] is not None else None
        }

    if len(modules_data) < 2:
        raise ValueError("Less than 2 valid courses found in the database")

    # Compute pairwise similarities
    overlaps = []
    codes = list(modules_data.keys())

    for i, code_a in enumerate(codes):
        for code_b in codes[i+1:]:
            data_a = modules_data[code_a]
            data_b = modules_data[code_b]

            # Embedding similarity
            if data_a["embedding"] is not None and data_b["embedding"] is not None:
                emb_sim = compute_embedding_similarity(
                    data_a["embedding"],
                    data_b["embedding"]
                )
            else:
                emb_sim = 0.0

            # Metadata similarity
            meta_sim = compute_metadata_similarity(
                data_a["metadata"],
                data_b["metadata"]
            )

            # Weighted overall similarity
            overall_sim = 0.7 * emb_sim + 0.3 * meta_sim

            if overall_sim >= similarity_threshold:
                overlaps.append({
                    "course_a": code_a,
                    "course_b": code_b,
                    "embedding_similarity": round(emb_sim, 3),
                    "metadata_similarity": round(meta_sim, 3),
                    "overall_similarity": round(overall_sim, 3),
                    "details": {
                        "title_a": data_a["metadata"].get("title"),
                        "title_b": data_b["metadata"].get("title"),
                        "credits_a": data_a["metadata"].get("credits"),
                        "credits_b": data_b["metadata"].get("credits"),
                        "dept_a": data_a["metadata"].get("department"),
                        "dept_b": data_b["metadata"].get("department"),
                    }
                })

    # Sort by overall similarity (highest first)
    overlaps.sort(key=lambda x: x["overall_similarity"], reverse=True)

    return overlaps
