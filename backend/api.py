"""
NUSAdvisor+ FastAPI backend.

Usage:
    uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from tools.search_modules import search_modules, get_module_by_code
from langchain_core.messages import HumanMessage, AIMessage
from chat import chat, abot, _extract_text

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


@app.get("/history")
def history_endpoint(session_id: str):
    """Return prior messages for a session so the frontend can restore chat history."""
    config = {"configurable": {"thread_id": session_id}}
    state = abot.graph.get_state(config)
    messages = []
    for msg in state.values.get("messages", []):
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage) and msg.content:
            messages.append({"role": "assistant", "content": _extract_text(msg.content)})
    return {"messages": messages}


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """Chat with the NUSAdvisor+ LangGraph agent."""
    response = chat(req.message, req.session_id)
    return {"response": response}
