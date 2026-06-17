"""
Deep Research Agent — Agent Nodes & Graph
==========================================
Contains the LangGraph state, agent nodes, and graph builder.
Each node is one specialist agent in the research pipeline:
  Planner → Searcher → Analyzer → Verifier → Writer
"""

import json
import logging
from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import (
    OXLO_API_KEY, OXLO_BASE_URL, TAVILY_API_KEY,
    PLANNER_MODEL, SEARCHER_MODEL, ANALYZER_MODEL, VERIFIER_MODEL, WRITER_MODEL,
)
from prompts import (
    PLANNER_PROMPT, SEARCHER_PROMPT, ANALYZER_PROMPT, VERIFIER_PROMPT, WRITER_PROMPT,
)

logger = logging.getLogger("deep-research")


# ─── State Schema ──────────────────────────────────────────────────────

class ResearchState(TypedDict):
    """Shared state flowing through the research graph."""
    query: str
    sub_questions: list[str]
    search_results: Annotated[list[dict], add]
    analysis: str
    verification: str
    gaps: list[str]
    iteration: int
    max_iterations: int
    final_report: str
    status: str


# ─── Helpers ───────────────────────────────────────────────────────────

def get_llm(model: str, temperature: float = 0.3) -> ChatOpenAI:
    """Create an LLM instance pointing to Oxlo API."""
    return ChatOpenAI(
        model=model,
        api_key=OXLO_API_KEY,
        base_url=OXLO_BASE_URL,
        temperature=temperature,
        max_tokens=4096,
    )


def get_tavily():
    """Create Tavily client for web search. Returns None if no API key."""
    if not TAVILY_API_KEY:
        logger.warning("[Tavily] No API key — web search disabled")
        return None
    from tavily import TavilyClient
    return TavilyClient(api_key=TAVILY_API_KEY)


# ─── Agent Nodes ───────────────────────────────────────────────────────

def planner_node(state: ResearchState) -> dict:
    """Break down the query into focused sub-questions."""
    logger.info(f"[Planner] Breaking down: {state['query'][:80]}...")
    llm = get_llm(PLANNER_MODEL, 0.2)

    response = llm.invoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"Research query: {state['query']}"),
    ])

    try:
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        sub_questions = json.loads(content)
        if not isinstance(sub_questions, list):
            sub_questions = [state["query"]]
    except (json.JSONDecodeError, IndexError):
        sub_questions = [state["query"]]

    logger.info(f"[Planner] Generated {len(sub_questions)} sub-questions")
    return {"sub_questions": sub_questions, "status": "planning_complete"}


def searcher_node(state: ResearchState) -> dict:
    """Search the web for real-time data, then synthesize with LLM."""
    logger.info(f"[Searcher] Researching {len(state['sub_questions'])} questions...")
    tavily = get_tavily()
    llm = get_llm(SEARCHER_MODEL, 0.3)
    results = []

    for i, question in enumerate(state["sub_questions"]):
        web_context = _search_web(tavily, question, i)

        response = llm.invoke([
            SystemMessage(content=SEARCHER_PROMPT),
            HumanMessage(
                content=f"Question: {question}\n\n--- WEB RESULTS ---\n{web_context}\n--- END ---\n\n"
                         "Analyze these results and provide a comprehensive, well-sourced answer."
            ),
        ])

        results.append({
            "question": question,
            "answer": response.content,
            "web_sources": web_context[:1000],
            "index": i,
        })

    logger.info(f"[Searcher] Gathered {len(results)} results")
    return {"search_results": results, "status": "search_complete"}


def _search_web(tavily, question: str, index: int) -> str:
    """Execute Tavily web search for a single question."""
    if not tavily:
        return "\n(No web search configured — using model knowledge only)\n"

    try:
        logger.info(f"[Searcher] Web search Q{index+1}: {question[:60]}...")
        response = tavily.search(
            query=question,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
        )

        context = ""
        if response.get("answer"):
            context += f"\n**Tavily AI Answer:**\n{response['answer']}\n"

        for j, result in enumerate(response.get("results", [])[:5]):
            title = result.get("title", "Unknown")
            url = result.get("url", "")
            content = result.get("content", "")[:500]
            score = result.get("score", 0)
            context += f"\n**Source {j+1}** [{title}]({url}) (relevance: {score:.2f}):\n{content}\n"

        logger.info(f"[Searcher] Found {len(response.get('results', []))} results for Q{index+1}")
        return context

    except Exception as e:
        logger.warning(f"[Searcher] Tavily failed for Q{index+1}: {e}")
        return "\n(Web search failed — using model knowledge only)\n"


def analyzer_node(state: ResearchState) -> dict:
    """Analyze results, extract insights, identify gaps."""
    logger.info("[Analyzer] Analyzing research results...")
    llm = get_llm(ANALYZER_MODEL, 0.2)

    results_text = "\n\n".join([
        f"### Q{r['index']+1}: {r['question']}\n{r['answer']}"
        for r in state["search_results"]
    ])

    response = llm.invoke([
        SystemMessage(content=ANALYZER_PROMPT),
        HumanMessage(content=f"Original query: {state['query']}\n\nResearch results:\n{results_text}"),
    ])

    gaps = []
    try:
        if '```json' in response.content:
            json_block = response.content.split('```json')[1].split('```')[0]
            gaps = json.loads(json_block).get("gaps", [])
    except Exception:
        pass

    logger.info(f"[Analyzer] Found {len(gaps)} knowledge gaps")
    return {"analysis": response.content, "gaps": gaps, "status": "analysis_complete"}


def verifier_node(state: ResearchState) -> dict:
    """Cross-check facts and verify claims."""
    logger.info("[Verifier] Cross-checking claims...")
    llm = get_llm(VERIFIER_MODEL, 0.1)

    response = llm.invoke([
        SystemMessage(content=VERIFIER_PROMPT),
        HumanMessage(content=f"Original query: {state['query']}\n\nAnalysis to verify:\n{state['analysis']}"),
    ])

    logger.info("[Verifier] Verification complete")
    return {
        "verification": response.content,
        "status": "verification_complete",
        "iteration": state["iteration"] + 1,
    }


def writer_node(state: ResearchState) -> dict:
    """Synthesize all research into a final report."""
    logger.info("[Writer] Generating final report...")
    llm = get_llm(WRITER_MODEL, 0.4)

    response = llm.invoke([
        SystemMessage(content=WRITER_PROMPT),
        HumanMessage(content=(
            f"Original query: {state['query']}\n\n"
            f"Research Results:\n{json.dumps([{'q': r['question'], 'a': r['answer'][:800], 'sources': r.get('web_sources', '')[:300]} for r in state['search_results']], indent=2)}\n\n"
            f"Analysis:\n{state['analysis']}\n\n"
            f"Verification:\n{state['verification']}"
        )),
    ])

    logger.info("[Writer] Report generated")
    return {"final_report": response.content, "status": "complete"}


# ─── Routing ───────────────────────────────────────────────────────────

def should_iterate(state: ResearchState) -> str:
    """Decide: do another research pass or proceed to writing."""
    if state["iteration"] >= state["max_iterations"]:
        return "write"
    if len(state.get("gaps", [])) > 0:
        return "search"
    return "write"


# ─── Graph Builder ─────────────────────────────────────────────────────

def build_graph():
    """Build the LangGraph research workflow."""
    wf = StateGraph(ResearchState)

    wf.add_node("planner", planner_node)
    wf.add_node("searcher", searcher_node)
    wf.add_node("analyzer", analyzer_node)
    wf.add_node("verifier", verifier_node)
    wf.add_node("writer", writer_node)

    wf.set_entry_point("planner")
    wf.add_edge("planner", "searcher")
    wf.add_edge("searcher", "analyzer")
    wf.add_edge("analyzer", "verifier")
    wf.add_conditional_edges(
        "verifier", should_iterate,
        {"search": "searcher", "write": "writer"},
    )
    wf.add_edge("writer", END)

    return wf.compile()
