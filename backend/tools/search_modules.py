from tools.db import modules_collection, model
from functools import lru_cache


def search_modules(query: str, departments: list[str] = None, min_level: int = None, n_results: int = 5) -> list[dict]:
    embedded_query = model.encode(query).tolist()

    filters = []
    if departments:
        filters.append({"department": {"$in": departments}})
    if min_level and min_level > 0:
        filters.append({"course_level": {"$gte": min_level}})

    where = None
    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}

    query_result = modules_collection.query(
        query_embeddings=[embedded_query],
        n_results=n_results,
        include=["metadatas", "distances"],
        where=where,
    )

    results = []
    for metadata, distance in zip(query_result['metadatas'][0], query_result['distances'][0]):
        results.append({
            **metadata,
            "score": round(1 - distance, 4)
        })
    return results


@lru_cache(maxsize=512)
def get_module_by_code(code: str) -> dict | None:
    module = modules_collection.get(ids=[code], include=["metadatas"])
    if module and module["metadatas"]:
        return module["metadatas"][0]
    return None
