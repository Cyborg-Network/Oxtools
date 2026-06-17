"""
JSON to Schema V2 — Tool Entry Point
======================================
This is the entry point loaded by the unified runner.
The actual agent logic lives in agents.py, compilers.py, and prompts.py.

Architecture:
  compilers.py  — Deterministic SQL/Prisma/Mongoose/Drizzle generators
  agents.py     — LangGraph StateGraph with 5 specialist nodes
  prompts.py    — Agent prompts separated for A/B testing
  config.py     — Model assignments and output format config
"""

import json

from schema_agents import build_graph, SchemaState
from schema_config import OXLO_API_KEY, MAX_JSON_SIZE

# ─── MANIFEST ──────────────────────────────────────────────────────────
MANIFEST = {
    "id": "json-to-schema-v2",
    "name": "JSON to DB Schema (Agentic V2)",
    "description": (
        "Multi-agent schema generation: programmatic JSON parsing, "
        "LLM-powered schema design with iterative review, and "
        "deterministic compilation to PostgreSQL/MySQL/Prisma/Mongoose/Drizzle"
    ),
    "author": "Oxlo Team",
    "version": "2.0.0",
    "requires": ["langgraph", "langchain-openai", "langchain-core"],
}


# ─── RUN (called by the unified runner) ──────────────────────────────
async def run(data: dict):
    """
    Execute the schema generation pipeline.
    Returns an async generator that streams per-node status + final output.
    """
    if not OXLO_API_KEY:
        return {"error": "OXLO_API_KEY not configured. Set it in .env"}

    raw_json = data.get("json", "")
    if not raw_json.strip():
        return {"error": "No JSON provided. Paste your JSON data."}

    # Validate JSON before entering the pipeline
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}. Fix syntax errors before converting."}

    if len(raw_json) > MAX_JSON_SIZE:
        return {"error": f"JSON too large ({len(raw_json)} bytes). Max: {MAX_JSON_SIZE} bytes."}

    output_format = data.get("outputFormat", "postgresql").lower()
    user_model = data.get("model", "")

    graph = build_graph()
    initial: SchemaState = {
        "raw_json": raw_json,
        "parsed_data": {},
        "output_format": output_format,
        "user_model": user_model,
        "structure_analysis": "",
        "draft_schema": {},
        "proposed_schema": {},
        "design_decisions": [],
        "review_approved": False,
        "review_issues": [],
        "review_refinements": [],
        "review_iteration": 0,
        "compiled_output": "",
        "documentation": "",
        "status": "starting",
    }

    async def stream():
        async for event in graph.astream(initial):
            for node_name, node_output in event.items():
                status = node_output.get("status", "processing")
                yield f"[{node_name}] {status}\n"

                # Stream parser stats
                if node_name == "parser" and "structure_analysis" in node_output:
                    lines = node_output["structure_analysis"].split("\n")
                    yield f"  → {lines[0]}\n"  # Stats line

                # Stream architect table count
                if node_name == "architect" and "proposed_schema" in node_output:
                    tables = node_output["proposed_schema"].get("tables", [])
                    yield f"  → Designed {len(tables)} tables\n"

                # Stream reviewer verdict
                if node_name == "reviewer":
                    approved = node_output.get("review_approved", False)
                    issues = len(node_output.get("review_issues", []))
                    iteration = node_output.get("review_iteration", 0)
                    verdict = "✓ Approved" if approved else "✗ Needs refinement"
                    yield f"  → {verdict} ({issues} issues, iteration {iteration})\n"

                # Stream compiled output
                if node_name == "compiler" and "compiled_output" in node_output:
                    yield "\n---SCHEMA_START---\n"
                    yield node_output["compiled_output"]
                    yield "\n---SCHEMA_END---\n"

                # Stream documentation
                if node_name == "documenter" and "documentation" in node_output:
                    yield "\n---DOCS_START---\n"
                    yield node_output["documentation"]

    return stream()
