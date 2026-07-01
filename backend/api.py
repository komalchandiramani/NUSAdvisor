from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from tools.search_modules import search_modules, get_module_by_code
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from chat import create_agent, achat, _extract_text, NUSAdvisorAgent, model
from prompts import TITLE_PROMPT

abot: NUSAdvisorAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global abot
    abot = await create_agent()
    yield


app = FastAPI(title="NUSAdvisor+", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://d2k55gvobdiojf.cloudfront.net"],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


class ChatRequest(BaseModel):
    message: str
    session_id: str
    is_first_message: bool = False


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/search")
async def search(req: SearchRequest):
    results = search_modules(req.query, req.n_results)
    return {"results": results}


@router.get("/modules/{code}")
async def get_module(code: str):
    module = get_module_by_code(code.upper())
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {code} not found")
    return module


@router.get("/history")
async def history_endpoint(session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    state = await abot.graph.aget_state(config) # reads the asyncsqliterserver state, no checkpointer => no state, we get an error
    messages = []
    for msg in state.values.get("messages", []):
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage) and msg.content:
            messages.append({"role": "assistant", "content": _extract_text(msg.content)})
    return {"messages": messages}


### not streaming version, returns the whole response all at once
@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    response = await achat(req.message, req.session_id, abot)
    return {"response": response}

### generate a title based on the message content
### limit the title to 40 characters
async def generate_title(message: str) -> str:
    try:
        result = await model.ainvoke([HumanMessage(content=TITLE_PROMPT.format(message=message))])
        return _extract_text(result.content).strip()
    except Exception:
        return message[:40]


### streaming version of chat endpoint, uses SSE - Server Sent Events
### SSE - is a web standard ofr the server to push a stream of data to
### the client over a single, long-lived HTTP connection
@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    async def generate():
        config = {"configurable": {"thread_id": req.session_id}}
        async for chunk, _ in abot.graph.astream(
            {"messages": [HumanMessage(content=req.message)]},
            config,
            stream_mode="messages"
        ):
            if isinstance(chunk, AIMessageChunk):
                text = _extract_text(chunk.content)
                if text:
                    yield f"data: {json.dumps({'token': text})}\n\n"
            else:
                yield ": ping\n\n"  ## in SSE, line starting with : is a comment, keeps the http connection alive during non-llm messages
        if req.is_first_message:
            title = await generate_title(req.message)
            yield f"data: {json.dumps({'title': title})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


app.include_router(router)