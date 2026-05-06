from tools.db import dept_collection, model

def find_departments(search_term: str = None, top_k: int = 5) -> dict:
    if search_term is None:
        all_data = dept_collection.get(include=["metadatas"])
        
        faculty_groups = {}
        for metadata in all_data["metadatas"]:
            faculty = metadata["faculty"]
            dept = metadata["department"]
            faculty_groups.setdefault(faculty, []).append(dept)
        
        grouped = [
            {"faculty": faculty, "departments": sorted(depts)}
            for faculty, depts in sorted(faculty_groups.items())
        ]
        
        total = sum(len(g["departments"]) for g in grouped)
        return {
            "grouped_by_faculty": grouped,
            "total_departments": total,
            "total_faculties": len(grouped),
        }
    
    query_embedding = model.encode(search_term).tolist()

    results = dept_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "distances"],
    )

    departments = []
    for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
        departments.append({
            "department": metadata["department"],
            "faculty": metadata["faculty"],
            "similarity": round(1 - distance, 4),
        })

    return {
        "departments": [d["department"] for d in departments],
        "details": departments,
        "count": len(departments),
    }