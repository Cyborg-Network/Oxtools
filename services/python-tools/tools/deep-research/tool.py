"""
Deep Research Agent — Tool Entry Point
=======================================
This is the entry point loaded by the unified runner.
The actual agent logic lives in agents.py and prompts.py.
"""

from agents import build_graph, ResearchState
from config import OXLO_API_KEY

# ─── MANIFEST ──────────────────────────────────────────────────────────
MANIFEST = {
    "id": "deep-research",
    "name": "Deep Research Agent",
    "description": "Multi-agent research system with real-time web search via Tavily",
    "author": "Oxlo Team",
    "version": "2.0.0",
    "requires": ["langgraph", "langchain-openai", "langchain-core", "tavily-python"],
}


# ─── RUN (called by the unified runner) ──────────────────────────────
async def run(data: dict):
    """
    Execute the deep research pipeline.
    Returns an async generator that streams progress + final report.
    """
    if not OXLO_API_KEY:
        return {"error": "OXLO_API_KEY not configured"}

    query = data.get("query", "")
    if not query.strip():
        return {"error": "Query cannot be empty"}

    depth = data.get("depth", "standard")
    max_iter = {"quick": 1, "standard": 2, "deep": 3}.get(depth, 2)

    graph = build_graph()
    initial: ResearchState = {
        "query": query,
        "sub_questions": [],
        "search_results": [],
        "analysis": "",
        "verification": "",
        "gaps": [],
        "iteration": 0,
        "max_iterations": max_iter,
        "final_report": "",
        "status": "starting",
    }

    async def stream():
        async for event in graph.astream(initial):
            for node_name, node_output in event.items():
                status = node_output.get("status", "processing")
                yield f"[{node_name}] {status}\n"
                if node_name == "writer" and "final_report" in node_output:
                    yield "\n---REPORT_START---\n"
                    yield node_output["final_report"]

    return stream()
