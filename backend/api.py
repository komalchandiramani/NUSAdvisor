"""
NUSAdvisor+ FastAPI backend.

Usage:
    uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from search import search_modules, get_module_by_code
from chat import chat

app = FastAPI(title="NUSAdvisor+")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


class ChatRequest(BaseModel):
    message: str
    session_id: str


# ── Routes ───────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search")
def search(req: SearchRequest):
    """Semantic search over all NUS modules."""
    results = search_modules(req.query, req.n_results)
    return {"results": results}


@app.get("/modules/{code}")
def get_module(code: str):
    """Look up a single module by code (e.g. CS1101S)."""
    module = get_module_by_code(code.upper())
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {code} not found")
    return module


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """Chat with the NUSAdvisor+ LangGraph agent."""
    response = chat(req.message, req.session_id)
    return {"response": response}
