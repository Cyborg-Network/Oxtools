"""
JSON to Schema V2 — Agent Nodes & Graph
=========================================
LangGraph StateGraph with typed state and 5 specialist nodes.

KEY ARCHITECTURAL FIX (v2.2):
  Old approach: Parser does analysis → Architect designs schema from scratch
  Problem: LLM creates generic EAV meta-schemas instead of specific tables

  New approach: Parser BUILDS a draft schema deterministically → Architect REFINES it
  This gives the LLM a much simpler task (adjust types, handle edge cases)
  while the deterministic builder ensures every JSON key gets its own table/column.

  Pipeline:
    Parser (builds draft schema) → Architect (refines) → Reviewer → Compiler → Documenter
"""

import json
import logging
import re
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from schema_config import (
    OXLO_API_KEY, OXLO_BASE_URL,
    ARCHITECT_MODEL, REVIEWER_MODEL, DOCUMENTER_MODEL,
    MAX_REVIEW_ITERATIONS,
)
from schema_prompts import ARCHITECT_PROMPT, REVIEWER_PROMPT, DOCUMENTER_PROMPT
from schema_compilers import compile_schema

logger = logging.getLogger("json-to-schema")


# ─── State Schema ─────────────────────────────────────────────────────

class SchemaState(TypedDict):
    """Shared state flowing through the schema generation pipeline."""
    # Input
    raw_json: str
    parsed_data: dict
    output_format: str
    user_model: str

    # Parser output (deterministic)
    structure_analysis: str
    draft_schema: dict          # NEW: deterministic draft schema

    # Architect output
    proposed_schema: dict
    design_decisions: list[str]

    # Reviewer output
    review_approved: bool
    review_issues: list[dict]
    review_refinements: list[dict]
    review_iteration: int

    # Compiler output (deterministic)
    compiled_output: str

    # Documenter output
    documentation: str

    # Metadata
    status: str


# ─── Helpers ──────────────────────────────────────────────────────────

def get_llm(model: str, temperature: float = 0.1) -> ChatOpenAI:
    """Create an LLM instance pointing to Oxlo API."""
    return ChatOpenAI(
        model=model,
        api_key=OXLO_API_KEY,
        base_url=OXLO_BASE_URL,
        temperature=temperature,
        max_tokens=16384,
    )


def _parse_json_from_llm(content: str) -> dict:
    """Robustly extract a JSON object from LLM output."""
    content = content.strip()

    if "```" in content:
        blocks = content.split("```")
        for block in blocks:
            cleaned = block.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("{"):
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass

    return {}


def _get_depth(obj, depth=0) -> int:
    """Calculate the maximum nesting depth of a JSON structure."""
    if isinstance(obj, dict):
        if not obj:
            return depth
        return max(_get_depth(v, depth + 1) for v in obj.values())
    elif isinstance(obj, list):
        if not obj:
            return depth
        return max(_get_depth(item, depth + 1) for item in obj[:5])
    return depth


def _sanitize_name(name: str) -> str:
    """Convert a JSON key to a safe SQL table/column name."""
    # Remove dangerous characters, path traversal, special prefixes
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    # Don't start with a number
    if cleaned and cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned.lower() or "unnamed"


# ─── Dangerous Key Detection ─────────────────────────────────────────

DANGEROUS_KEYS = {
    # Prototype pollution
    "__proto__", "constructor", "prototype", "__class__",
    "__subclasses__", "__globals__", "__builtins__",
    # NoSQL operators
    "$gt", "$ne", "$lt", "$gte", "$lte", "$regex", "$where", "$exists",
    "$in", "$nin", "$or", "$and", "$not", "$set", "$unset",
}

SHELL_METACHARACTERS = set(';|&$`><')


def _is_dangerous_key(key: str) -> tuple[bool, str]:
    """Check if a JSON key is an attack payload. Returns (is_dangerous, threat_type)."""
    lower = key.lower()
    if lower in DANGEROUS_KEYS:
        if lower.startswith("$"):
            return True, "nosql_operator"
        return True, "prototype_pollution"
    # Path traversal
    if ".." in key or key.startswith("/") or "%2f" in lower or "%2e" in lower:
        return True, "path_traversal"
    # Shell metacharacters in keys
    if any(c in key for c in SHELL_METACHARACTERS):
        return True, "shell_injection"
    return False, ""


def _is_type_confused(value) -> bool:
    """Check if a string value LOOKS like a typed primitive but contains injection."""
    if not isinstance(value, str):
        return False
    v = value.strip().lower()
    # String "true"/"false" → type confusion
    if v in ("true", "false"):
        return True
    # String number with injection payload
    if re.match(r'^-?\d+', v) and not v.replace('-', '').replace('.', '').isdigit():
        return True
    return False


def _infer_safe_type(value) -> str:
    """Infer a safe SQL type from a JSON value. Defaults to TEXT for safety."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        if abs(value) > 2_147_483_647:
            return "bigint"
        return "integer"
    if isinstance(value, float):
        return "decimal"
    if isinstance(value, dict):
        # Check for NoSQL operators as values
        if any(k.startswith("$") for k in value.keys()):
            return "text"  # Don't create child table for operator dicts
        return "jsonb"
    if isinstance(value, list):
        return "jsonb"
    # For strings: always TEXT (safe default)
    if isinstance(value, str):
        return "text"
    return "text"


# ─── Deterministic Schema Builder ────────────────────────────────────

def _build_draft_schema(data: dict) -> dict:
    """
    Build a complete schema deterministically from JSON structure.
    
    Rules:
    - Each top-level key → its own table
    - Each sub-key → a column in that table
    - Nested objects → separate child table with FK
    - Dangerous keys → stored in a safe key_value table
    - Deeply nested (>5 levels) → flattened with nesting_level column
    - All string values → TEXT (safe default)
    - _comment keys → ignored
    """
    tables = []
    design_decisions = []
    has_dangerous_keys = False

    if not isinstance(data, dict):
        # If top-level is an array, create one table
        tables.append({
            "name": "items",
            "columns": [
                {"name": "id", "type": "serial", "isPrimary": True, "isNullable": False, "isUnique": False},
                {"name": "data", "type": "jsonb", "isPrimary": False, "isNullable": True, "isUnique": False},
                {"name": "created_at", "type": "timestamp", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "CURRENT_TIMESTAMP"},
            ],
            "foreignKeys": [],
            "indexes": [],
        })
        return {"tables": tables, "designDecisions": ["Top-level is an array, stored as JSONB rows"]}

    # Process each top-level key
    for top_key, top_value in data.items():
        # Skip comment/meta keys
        if top_key.startswith("_"):
            design_decisions.append(f"Skipped meta key '{top_key}'")
            continue

        if not isinstance(top_value, dict):
            # Scalar top-level value — add to a general table later
            continue

        table_name = _sanitize_name(top_key)

        # Check if this object contains dangerous keys (RECURSIVE)
        dangerous_entries = []
        safe_entries = {}

        def _scan_keys_recursive(obj, prefix=""):
            """Recursively scan ALL nesting levels for dangerous keys."""
            nonlocal has_dangerous_keys
            if isinstance(obj, dict):
                for k, v in obj.items():
                    full_path = f"{prefix}.{k}" if prefix else k
                    is_bad, threat = _is_dangerous_key(k)
                    if is_bad:
                        dangerous_entries.append((full_path, v, threat))
                        has_dangerous_keys = True
                    else:
                        _scan_keys_recursive(v, full_path)
            elif isinstance(obj, list):
                for item in obj[:5]:
                    _scan_keys_recursive(item, prefix)

        _scan_keys_recursive(top_value)

        for key, value in top_value.items():
            is_bad, _ = _is_dangerous_key(key)
            if not is_bad:
                safe_entries[key] = value

        # Build columns for safe entries
        columns = [
            {"name": "id", "type": "serial", "isPrimary": True, "isNullable": False, "isUnique": False},
        ]

        child_tables = []

        for key, value in safe_entries.items():
            col_name = _sanitize_name(key)
            # Type confusion: string "true"/"18; DROP TABLE" stays as _raw TEXT
            if _is_type_confused(value):
                col_name = f"{col_name}_raw"

            if isinstance(value, dict):
                # Check nesting depth
                depth = _get_depth(value)
                if depth > 5:
                    # Deeply nested → flatten
                    columns.append({"name": f"{col_name}_deepest_value", "type": "text", "isPrimary": False, "isNullable": True, "isUnique": False})
                    columns.append({"name": f"{col_name}_nesting_level", "type": "integer", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "0"})
                    design_decisions.append(f"Flattened deeply nested '{key}' (depth={depth}) with nesting_level + deepest_value")
                else:
                    # Nested object → child table
                    child_table_name = f"{table_name}_{col_name}"
                    child_cols = [
                        {"name": "id", "type": "serial", "isPrimary": True, "isNullable": False, "isUnique": False},
                        {"name": f"{table_name}_id", "type": "integer", "isPrimary": False, "isNullable": False, "isUnique": False},
                    ]
                    for sub_key, sub_value in value.items():
                        is_bad, threat = _is_dangerous_key(sub_key)
                        if is_bad:
                            dangerous_entries.append((f"{key}.{sub_key}", sub_value, threat))
                        else:
                            sub_col_name = _sanitize_name(sub_key)
                            if _is_type_confused(sub_value):
                                sub_col_name = f"{sub_col_name}_raw"
                            sub_type = _infer_safe_type(sub_value)
                            child_cols.append({"name": sub_col_name, "type": sub_type, "isPrimary": False, "isNullable": True, "isUnique": False})
                    child_cols.append({"name": "created_at", "type": "timestamp", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "CURRENT_TIMESTAMP"})
                    child_tables.append({
                        "name": child_table_name,
                        "columns": child_cols,
                        "foreignKeys": [{"column": f"{table_name}_id", "referencesTable": table_name, "referencesColumn": "id"}],
                        "indexes": [{"columns": [f"{table_name}_id"], "unique": False}],
                    })
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Array of objects → child table
                    child_table_name = f"{table_name}_{col_name}"
                    child_cols = [
                        {"name": "id", "type": "serial", "isPrimary": True, "isNullable": False, "isUnique": False},
                        {"name": f"{table_name}_id", "type": "integer", "isPrimary": False, "isNullable": False, "isUnique": False},
                    ]
                    for sub_key, sub_value in value[0].items():
                        sub_col_name = _sanitize_name(sub_key)
                        sub_type = _infer_safe_type(sub_value)
                        child_cols.append({"name": sub_col_name, "type": sub_type, "isPrimary": False, "isNullable": True, "isUnique": False})
                    child_cols.append({"name": "created_at", "type": "timestamp", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "CURRENT_TIMESTAMP"})
                    child_tables.append({
                        "name": child_table_name,
                        "columns": child_cols,
                        "foreignKeys": [{"column": f"{table_name}_id", "referencesTable": table_name, "referencesColumn": "id"}],
                        "indexes": [{"columns": [f"{table_name}_id"], "unique": False}],
                    })
                else:
                    # Array of primitives → JSONB
                    columns.append({"name": col_name, "type": "jsonb", "isPrimary": False, "isNullable": True, "isUnique": False})
            else:
                # Scalar value → column
                col_type = _infer_safe_type(value)
                columns.append({"name": col_name, "type": col_type, "isPrimary": False, "isNullable": True, "isUnique": False})

        # Add created_at to main table
        columns.append({"name": "created_at", "type": "timestamp", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "CURRENT_TIMESTAMP"})

        tables.append({
            "name": table_name,
            "columns": columns,
            "foreignKeys": [],
            "indexes": [],
        })
        tables.extend(child_tables)

        # If there were dangerous entries, log them
        if dangerous_entries:
            design_decisions.append(
                f"Table '{table_name}': quarantined {len(dangerous_entries)} dangerous keys "
                f"({', '.join(k for k, *_ in dangerous_entries)}) in dangerous_key_values table"
            )

    # Create a dangerous_key_values table if any dangerous keys were found
    if has_dangerous_keys:
        tables.append({
            "name": "dangerous_key_values",
            "columns": [
                {"name": "id", "type": "serial", "isPrimary": True, "isNullable": False, "isUnique": False},
                {"name": "source_table", "type": "text", "isPrimary": False, "isNullable": False, "isUnique": False},
                {"name": "key_path", "type": "text", "isPrimary": False, "isNullable": False, "isUnique": False},
                {"name": "raw_value", "type": "text", "isPrimary": False, "isNullable": True, "isUnique": False},
                {"name": "threat_type", "type": "text", "isPrimary": False, "isNullable": False, "isUnique": False},
                {"name": "is_confirmed_attack", "type": "boolean", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "TRUE"},
                {"name": "detected_at", "type": "timestamp", "isPrimary": False, "isNullable": False, "isUnique": False, "defaultValue": "CURRENT_TIMESTAMP"},
            ],
            "foreignKeys": [],
            "indexes": [
                {"columns": ["source_table"], "unique": False},
                {"columns": ["threat_type"], "unique": False},
            ],
        })
        design_decisions.append("Created dangerous_key_values table with threat_type classification (prototype_pollution, path_traversal, nosql_operator, shell_injection)")

    return {"tables": tables, "designDecisions": design_decisions}


# ─── Node 1: Parser (Deterministic Schema Builder) ───────────────────

def parser_node(state: SchemaState) -> dict:
    """
    Pure Python JSON parsing + DETERMINISTIC SCHEMA BUILDING.
    
    This is the key fix: instead of just analyzing the JSON structure,
    we BUILD a complete draft schema that the Architect refines.
    This ensures every JSON key gets its own table/column.
    """
    raw_json = state["raw_json"]

    logger.info("[Parser] Analyzing JSON structure and building draft schema...")

    data = json.loads(raw_json)

    # Build draft schema deterministically
    draft_schema = _build_draft_schema(data)

    # Generate human-readable analysis
    json_str = json.dumps(data, indent=2)
    stats = (
        f"JSON Stats: {len(json_str)} bytes, "
        f"Max depth: {_get_depth(data)}, "
        f"Top-level type: {type(data).__name__}, "
        f"Top-level keys: {len(data) if isinstance(data, dict) else 'N/A'}"
    )

    draft_tables = draft_schema.get("tables", [])
    draft_summary = f"Draft schema: {len(draft_tables)} tables built deterministically"
    for t in draft_tables:
        cols = len(t.get("columns", []))
        fks = len(t.get("foreignKeys", []))
        draft_summary += f"\n  - {t['name']}: {cols} columns, {fks} FKs"

    structure_analysis = stats + "\n\n" + draft_summary

    logger.info(f"[Parser] Built draft schema with {len(draft_tables)} tables")

    return {
        "parsed_data": data,
        "structure_analysis": structure_analysis,
        "draft_schema": draft_schema,
        "status": "parsing_complete",
    }


# ─── Node 2: Architect (LLM Refines Draft Schema) ────────────────────

def architect_node(state: SchemaState) -> dict:
    """
    LLM REFINES the draft schema built by the Parser.
    
    KEY FIX: The Architect no longer designs from scratch.
    It receives a complete draft schema and makes intelligent adjustments:
    - Type refinements
    - Safety overrides
    - Naming improvements
    - Index suggestions
    - Structural changes for better normalization
    """
    logger.info("[Architect] Refining draft schema...")
    model = state.get("user_model") or ARCHITECT_MODEL
    llm = get_llm(model, 0.2)

    draft = state.get("draft_schema", {})
    raw_json_full = state["raw_json"]

    user_content = (
        f"## Draft Schema (built deterministically from JSON structure):\n"
        f"```json\n{json.dumps(draft, indent=2)}\n```\n\n"
        f"## Raw JSON Data:\n```json\n{raw_json_full}\n```\n\n"
        f"## Target Format: {state['output_format']}\n\n"
    )

    # Include reviewer feedback if this is a refinement pass
    if state.get("review_issues"):
        user_content += (
            f"## Reviewer Feedback (address these issues):\n"
            f"```json\n{json.dumps(state['review_issues'], indent=2)}\n```\n\n"
            f"## Suggested Refinements:\n"
            f"```json\n{json.dumps(state.get('review_refinements', []), indent=2)}\n```\n\n"
        )

    response = llm.invoke([
        SystemMessage(content=ARCHITECT_PROMPT),
        HumanMessage(content=user_content),
    ])

    result = _parse_json_from_llm(response.content)

    # If the LLM returned fewer tables than draft, fall back to draft
    # This prevents the LLM from collapsing specific tables into EAV
    tables = result.get("tables", [])
    draft_tables = draft.get("tables", [])
    if len(tables) < len(draft_tables):
        logger.warning(f"[Architect] LLM returned {len(tables)} tables vs draft's {len(draft_tables)} — using draft")
        result = draft
        tables = draft_tables

    decisions = result.get("designDecisions", [])
    # Merge draft decisions
    draft_decisions = draft.get("designDecisions", [])
    all_decisions = draft_decisions + decisions

    logger.info(f"[Architect] Final schema: {len(tables)} tables, {len(all_decisions)} design decisions")

    return {
        "proposed_schema": result,
        "design_decisions": all_decisions,
        "status": "architecture_complete",
    }


# ─── Node 3: Reviewer (LLM Quality Check) ────────────────────────────

def reviewer_node(state: SchemaState) -> dict:
    """Reviews schema for normalization issues, safety, and anti-patterns."""
    iteration = state.get("review_iteration", 0)
    schema = state.get("proposed_schema", {})

    logger.info(f"[Reviewer] Reviewing schema (iteration {iteration + 1})...")
    model = state.get("user_model") or REVIEWER_MODEL
    llm = get_llm(model, 0.1)

    response = llm.invoke([
        SystemMessage(content=REVIEWER_PROMPT),
        HumanMessage(content=(
            f"## Original JSON Structure:\n{state['structure_analysis']}\n\n"
            f"## Proposed Schema:\n```json\n{json.dumps(schema, indent=2)}\n```\n\n"
            f"Review this schema for correctness and quality."
        )),
    ])

    review = _parse_json_from_llm(response.content)

    approved = review.get("approved", True)
    issues = review.get("issues", [])
    refinements = review.get("refinements", [])

    if refinements and approved:
        schema = _apply_refinements(schema, refinements)

    logger.info(
        f"[Reviewer] {'Approved' if approved else 'Rejected'} — "
        f"{len(issues)} issues, {len(refinements)} refinements"
    )

    return {
        "proposed_schema": schema,
        "review_approved": approved,
        "review_issues": issues,
        "review_refinements": refinements,
        "review_iteration": iteration + 1,
        "status": "review_complete",
    }


def _apply_refinements(schema: dict, refinements: list) -> dict:
    """Apply minor reviewer refinements directly to the schema."""
    for ref in refinements:
        table_name = ref.get("table", "")
        action = ref.get("action", "")

        for table in schema.get("tables", []):
            if table["name"] == table_name:
                if action == "add_column" and ref.get("column"):
                    table.setdefault("columns", []).append(ref["column"])
                elif action == "add_index" and ref.get("index"):
                    table.setdefault("indexes", []).append(ref["index"])

    return schema


# ─── Node 4: Compiler (Pure Deterministic) ───────────────────────────

def compiler_node(state: SchemaState) -> dict:
    """Deterministic compilation to target format. NO LLM."""
    schema = state.get("proposed_schema", {})
    output_format = state.get("output_format", "postgresql")

    logger.info(f"[Compiler] Generating {output_format} output...")

    compiled = compile_schema(schema, output_format)

    logger.info(f"[Compiler] Generated {len(compiled)} chars of {output_format}")
    return {
        "compiled_output": compiled,
        "status": "compilation_complete",
    }


# ─── Node 5: Documenter (LLM Documentation) ──────────────────────────

def documenter_node(state: SchemaState) -> dict:
    """Generates documentation, example queries, and design notes."""
    logger.info("[Documenter] Writing documentation...")
    llm = get_llm(DOCUMENTER_MODEL, 0.4)

    response = llm.invoke([
        SystemMessage(content=DOCUMENTER_PROMPT),
        HumanMessage(content=(
            f"## Schema (compiled {state.get('output_format', 'SQL')}):\n"
            f"```\n{state.get('compiled_output', '')[:6000]}\n```\n\n"
            f"## Design Decisions:\n"
            + "\n".join(f"- {d}" for d in state.get("design_decisions", []))
        )),
    ])

    logger.info("[Documenter] Documentation generated")
    return {
        "documentation": response.content,
        "status": "complete",
    }


# ─── Routing Logic ────────────────────────────────────────────────────

def should_refine(state: SchemaState) -> str:
    """After review, decide: refine or compile."""
    approved = state.get("review_approved", True)
    iteration = state.get("review_iteration", 0)

    if not approved and iteration < MAX_REVIEW_ITERATIONS:
        logger.info("[Router] Reviewer rejected — sending back to Architect")
        return "refine"

    if not approved:
        logger.info("[Router] Max iterations — proceeding despite issues")

    return "compile"


# ─── Graph Builder ────────────────────────────────────────────────────

def build_graph():
    """
    Build the LangGraph schema generation workflow.

    parser (builds draft) → architect (refines) → reviewer ─┬→ compiler → documenter → END
                                    ↑                        │
                                    └── refine ──────────────┘
    """
    wf = StateGraph(SchemaState)

    wf.add_node("parser", parser_node)
    wf.add_node("architect", architect_node)
    wf.add_node("reviewer", reviewer_node)
    wf.add_node("compiler", compiler_node)
    wf.add_node("documenter", documenter_node)

    wf.set_entry_point("parser")
    wf.add_edge("parser", "architect")
    wf.add_edge("architect", "reviewer")

    wf.add_conditional_edges(
        "reviewer",
        should_refine,
        {"refine": "architect", "compile": "compiler"},
    )

    wf.add_edge("compiler", "documenter")
    wf.add_edge("documenter", END)

    return wf.compile()
