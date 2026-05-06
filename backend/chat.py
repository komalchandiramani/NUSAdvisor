from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from typing import TypedDict, List, Annotated
import operator
import os
from dotenv import load_dotenv
from tools.search_modules import search_modules
from tools.find_departments import find_departments
import uuid
from typing import Optional
from prompts import SYS_PROMPT

load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")



@tool
def search_modules_tool(
    query: str,
    departments: Optional[list[str]] = None,
    min_level: Optional[int] = None,
    n_results: int = 5,
) -> dict:
    """Search for NUS courses by semantic query with optional filters.

    Use this to find courses about a topic. You can filter by department
    and minimum course level.

    Args:
        query: Natural language search query (e.g., 'machine learning',
               'cloud computing', 'full stack web development')
        departments: Filter by department names. Common values include:
               'Computer Science', 'Mathematics', 'Statistics and Data Science',
               'Information Systems and Analytics', 'Industrial Systems 
               Engineering and Management', 'Electrical and Computer Engineering'.
               Pass None to search all departments.
        min_level: Minimum course level (1000, 2000, 3000, 4000, 5000, 6000).
               Course levels at NUS:
                - Undergraduate: 1000-4000 level (sometimes 5000)
                - Master's: 5000-6000 level (mostly 5000)
                - PhD: 5000-6000 level
               Pass None to search all levels.
        n_results: Number of results to return (default 5, max 20).

    Returns:
        List of matching courses with code, title, department,
        credits, prerequisites, and relevance score.
    """
     
    results = search_modules(
        query=query,
        departments=departments or [],
        min_level=min_level or 0,
        n_results=n_results,
    )
    return {"courses": results, "count": len(results)}


@tool
def find_departments_tool(search_term: str, top_k: int = 5) -> dict:
    """Find NUS departments relevant to a keyword or topic using semantic search.

    Call this BEFORE search_modules_tool when:
    The user mentions a specific department, faculty, or school
       (e.g., 'computing', 'SoC', 'business school', 'FASS')

    Two modes:
    1. Pass a search_term to find relevant departments by semantic search.
    2. Pass search_term=None to get ALL departments grouped by faculty.
       Use this when the query is broad or cross-disciplinary and you want
       to browse all available departments before deciding which to search.

    Args:
        search_term: A keyword, topic, abbreviation, or department/faculty name.
                     Examples: 'computing', 'SoC', 'AI', 'machine learning',
                     'business', 'engineering', 'data science', 'economics'
        top_k: Number of results for semantic search (default 5, ignored when
               search_term is None).

    Returns the most relevant department names ranked by similarity.
    You MUST use these exact department names in search_modules_tool.
    """
    return find_departments(search_term, top_k=top_k)


tools = [search_modules_tool, find_departments_tool]

class AdvisorState(TypedDict):
    messages: Annotated[list, operator.add]


class NUSAdvisorAgent:

    def __init__(self, model, tools, system=""):
        self.system = system
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)

        graph = StateGraph(AdvisorState)
        graph.add_node("llm", self.call_llm)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges(
            "llm",
            self.exists_action,
            {True: "action", False: END}
        )
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")

        checkpointer = MemorySaver()
        self.graph = graph.compile(checkpointer=checkpointer)

    def exists_action(self, state: AdvisorState):
        result = state["messages"][-1]
        return len(result.tool_calls) > 0

    def call_llm(self, state: AdvisorState):
        messages = state["messages"]
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {"messages": [message]}

    def take_action(self, state: AdvisorState):
        tool_calls = state["messages"][-1].tool_calls
        results = []
        for t in tool_calls:
            if t["name"] not in self.tools:
                result = "Tool not found, please retry with a valid tool name."
            else:
                result = self.tools[t["name"]].invoke(t["args"])
            results.append(
                ToolMessage(tool_call_id=t["id"], name=t["name"], content=str(result))
            )
        return {"messages": results}
    

# model = ChatGroq(
#     model="llama-3.3-70b-versatile",
#     groq_api_key=os.getenv("GROQ_API_KEY")
# )

model = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL"),
    google_api_key=os.getenv("GEMINI_API_KEY")
)

abot = NUSAdvisorAgent(model, tools, system=SYS_PROMPT)


def _extract_text(content) -> str:
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def chat_with_log(user_message: str) -> dict:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    messages = [HumanMessage(content=user_message)]
    result = abot.graph.invoke({"messages": messages}, config=config)

    tool_calls = []
    tool_responses = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"tool_name": tc["name"], "tool_args": tc["args"]})
        if isinstance(msg, ToolMessage):
            tool_responses.append({"tool_name": msg.name, "tool_response": msg.content})

    return {
        "final_output": _extract_text(result["messages"][-1].content),
        "tool_calls": tool_calls,
        "tool_responses": tool_responses,
    }


def chat(user_message: str, session_id: str) -> str:
    config = {"configurable": {"thread_id": session_id}}
    result = abot.graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config
    )
    return _extract_text(result["messages"][-1].content)


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "test"}}
    result = abot.graph.invoke(
        {"messages": [HumanMessage(content="What is an introductory machine learning course offered by school of computing?")]},
        config=config
    )
    print(_extract_text(result["messages"][-1].content))
