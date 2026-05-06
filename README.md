# NUSAdvisor

A conversational academic advisor for NUS students. Ask it about courses in plain English — it searches across all 7,100+ NUS modules semantically, filters by department and level, and holds multi-turn conversations so you can refine your search naturally.

Built with LangGraph, Gemini, ChromaDB, and the official NUSMods v2 API.

---

## Features

- **Semantic course search** — ask in plain English and the agent searches across all 7,100+ NUS modules by meaning, not just keywords
- **Department-aware filtering** — mention a faculty or school ("SoC", "business school", "FASS") and the agent resolves the exact department before searching
- **Level filtering** — specify undergraduate, Master's, or PhD and the agent filters by course level automatically
- **Multi-turn memory** — follow-up questions work naturally; the agent remembers what you asked earlier in the session
- **Course tracking** — tell the agent which courses you've already taken and it won't recommend them again; add courses you're planning and it uses them for sequencing and prerequisite suggestions
- **Prerequisite awareness** — when recommending courses from your planned list, the agent checks whether prerequisites are satisfied by your completed courses and flags any gaps

---

## What it does

Ask questions like:
- *"What machine learning courses does NUS offer?"*
- *"Find undergraduate computer vision modules in the School of Computing"*
- *"What are the graduate-level NLP courses in Computing or Engineering?"*
- *"I'm a CS undergrad interested in finance, what crossover courses are there?"*

The agent reasons about your question, identifies relevant departments if needed, and searches the full NUS module catalogue semantically — returning courses with codes, descriptions, prerequisites, and credit counts.

---

## Architecture

```
User message
  └── LangGraph agent (Gemini)
        ├── find_departments_tool  → semantic search over NUS departments
        │                            (used when user mentions a faculty/school)
        └── search_modules_tool   → semantic search over 7,126 NUS modules
                                     (filters: department, course level, n_results)
```

Multi-turn memory: each conversation session retains context via LangGraph's `MemorySaver` — follow-up questions work naturally without repeating yourself.

Data pipeline: `NUSMods v2 API → sentence-transformers (all-MiniLM-L6-v2) → ChromaDB`

---

## Stack

| Component | Choice |
|-----------|--------|
| LLM | Gemini (via `langchain-google-genai`) |
| Orchestration | LangGraph |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Embeddings | `all-MiniLM-L6-v2` (384-dim) |
| Backend | FastAPI + uvicorn |
| Course data | NUSMods v2 API (public, no auth needed) |
| Evaluation | Arize Phoenix + custom evaluators |

---

## Setup

```bash
git clone <repo-url>
cd NUSAdvisor

python3 -m venv venv
source venv/bin/activate

pip install -r backend/requirements.txt
```

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
GROQ_API_KEY=your_key_here      # optional fallback
```

### Ingest NUS modules (first time only)

```bash
cd backend
python ingest.py
```

This fetches all NUS modules from the NUSMods API, embeds them, and stores them in ChromaDB. Takes ~15 minutes on first run.

---

## Running

### API server
```bash
cd backend
uvicorn api:app --reload
# Docs at http://localhost:8000/docs
```

### API endpoints
```
GET  /health
POST /chat    {"message": "What ML courses are there?", "session_id": "abc123"}
POST /search  {"query": "machine learning", "n_results": 5}
GET  /modules/{code}
```

### Test the agent directly
```bash
cd backend
python chat.py
```

---

## Project structure

```
backend/
├── chat.py          # LangGraph agent — tools, graph, chat(), chat_with_log()
├── api.py           # FastAPI app
├── ingest.py        # NUSMods API → embeddings → ChromaDB
├── prompts.py       # System prompt and evaluator prompts
├── config.py        # Constants and paths
├── tools/
│   ├── db.py               # Shared ChromaDB client + embedding model
│   ├── search_modules.py   # Semantic module search + lookup
│   └── find_departments.py # Semantic department search
└── evals/
    ├── dataset.py      # Evaluation questions with expected tool calls
    ├── evaluators.py   # tool_calling, course_exists, search_relevance, call_efficiency
    ├── tracing.py      # Phoenix setup + LangChain instrumentation
    └── run_evals.py    # Experiment runner
```

---

## Evaluation

The project includes an evaluation framework built on [Arize Phoenix](https://phoenix.arize.com/).

Start the Phoenix server:
```bash
python -m phoenix.server.main serve
```

Run evaluations:
```bash
cd backend
python evals/run_evals.py
```

View results at `http://localhost:6006`.

Evaluators:
- **tool_calling_eval** — did the agent call the right tools in the right order?
- **course_exists_eval** — are all course codes mentioned in the response real NUS modules?
- **search_relevance_eval** — is the response relevant to the student's question?
- **call_efficiency_eval** — did the agent avoid redundant tool calls?
