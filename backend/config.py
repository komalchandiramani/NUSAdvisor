from datetime import datetime
from pathlib import Path
import os

NUSMODS_BASE_URL = "https://api.nusmods.com/v2"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "data" / "chromadb"))
MODULES_COLLECTION = "nus_modules"
DEPARTMENTS_COLLECTION = "nus_departments"
CHROMA_SPACE = "cosine"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SKILLS_DATASET_PATH = "../jobsandskills-skillsfuture-skills-framework-dataset.xlsx"


def get_current_academic_year() -> str:
    today = datetime.now()
    year_start = today.year if today.month >= 8 else today.year - 1
    return f"{year_start}-{year_start + 1}"
