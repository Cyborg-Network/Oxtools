"""
SQL Converter — Multi-Agent Tool Entry Point  (v2)
===================================================
Pipeline:
  1. Schema Parser      — programmatic DDL parsing (sqlglot)
  2. Intent Classifier  — LLM: deepseek-v3.2
  3. SQL Generator      — LLM: qwen-3-coder-30b (simple/moderate)
                               deepseek-r1-0528   (complex)
  4. SQL Validator      — programmatic: sqlglot + schema column check
  5. SQL Refiner        — LLM: qwen-3-coder-30b (max 2 retries)
  6. Synthetic Data Gen — LLM: qwen-3-coder-30b (realistic rows from schema)
  7. Sandbox Manager    — dialect-aware execution:
       sqlite     → in-memory SQLite (fast, no Docker)
       postgresql → postgres:16-alpine container (ephemeral)
       mysql      → mysql:8.4 container (ephemeral)
       mssql      → mssql/server:2022-latest (ephemeral, >=2 GB RAM required)
       bigquery   → bigquery-emulator container (ephemeral)

Modes controlled by the `mode` field in the POST body:
  generate  (default) — full NL->SQL pipeline + sandbox execution
  sandbox             — skip AI generation, run a user-supplied SQL directly
"""

from intent_classifier import classify_intent
from schema_parser import parse_schema
from sql_generator import GENERATOR_MODEL_COMPLEX, GENERATOR_MODEL_DEFAULT, generate_sql
from sql_refiner import refine_sql
from sql_validator import validate_sql
from sandbox_manager import run_sandbox, sandbox_markdown
from synthetic_data import generate_synthetic_data

MANIFEST = {
    "id": "sql-converter",
    "name": "Natural Language to SQL",
    "description": (
        "Multi-agent pipeline: schema-aware, validated, dialect-correct SQL generation "
        "with multi-dialect sandbox execution (SQLite / PostgreSQL / MySQL / SQL Server / BigQuery)."
    ),
    "author": "Franci-343",
    "version": "2.0.0",
}


async def run(data: dict):
    query        = (data.get("query")        or "").strip()
    dialect      = (data.get("dialect")      or "postgresql").strip().lower()
    mode         = (data.get("mode")         or "generate").strip()
    sandbox_sql  = (data.get("sandboxQuery") or "").strip()

    schema_ddl      = (data.get("schema")     or "").strip()
    schema_file_raw = (data.get("schemaFile") or "").strip()

    # The "files" input type prepends: --- FILE: name.sql ---
    if schema_file_raw:
        lines = schema_file_raw.split("\n")
        if lines and lines[0].startswith("--- FILE:"):
            schema_ddl = "\n".join(lines[1:]).strip()
        else:
            schema_ddl = schema_file_raw

    # Sandbox-only mode
    if mode == "sandbox" or sandbox_sql:
        return _sandbox_stream(sandbox_sql or query, dialect, schema_ddl)

    # Full generation pipeline
    return _generate_stream(query, dialect, schema_ddl)


# ---------------------------------------------------------------------------
# Sandbox-only stream
# ---------------------------------------------------------------------------

async def _sandbox_stream(sql: str, dialect: str, schema_ddl: str):
    yield f"[1/3] Parsing schema for {dialect.upper()} sandbox...\n"

    try:
        schema_info = parse_schema(schema_ddl)
    except Exception as exc:
        yield f"[ERROR] Schema parser failed: {exc}\n"
        return

    if not schema_info.get("table_names"):
        yield "[ERROR] No tables found in schema. Please provide a valid DDL.\n"
        return

    yield "[2/3] Generating synthetic data from schema...\n"
    try:
        mock_data = await generate_synthetic_data(schema_info, dialect)
    except Exception as exc:
        yield f"[WARN] Synthetic data generation failed ({exc}), using deterministic fallback.\n"
        from synthetic_data import _deterministic_fallback
        mock_data = _deterministic_fallback(schema_info, rows_per_table=8)

    if dialect != "sqlite":
        yield f"[3/3] Spinning up {dialect.upper()} sandbox container...\n"
    else:
        yield "[3/3] Running query in SQLite memory sandbox...\n"

    result = run_sandbox(sql, dialect, schema_info, mock_data)

    yield "\n---RESULT---\n"
    yield "# SQL Sandbox Result\n"
    yield sandbox_markdown(result)


# ---------------------------------------------------------------------------
# Full generation pipeline stream
# ---------------------------------------------------------------------------

async def _generate_stream(query: str, dialect: str, schema_ddl: str):
    if not query:
        yield "[ERROR] Query cannot be empty.\n"
        return

    yield "[1/6] Parsing schema...\n"
    try:
        schema_info = parse_schema(schema_ddl)
    except Exception as exc:
        yield f"[WARN] Schema parser failed: {exc}. Continuing without schema.\n"
        schema_info = {"tables": {}, "table_names": [], "raw_ddl": ""}

    yield "[2/6] Classifying intent...\n"
    try:
        intent = await classify_intent(query, schema_info, dialect)
    except Exception as exc:
        yield f"[WARN] Intent classifier failed: {exc}. Using defaults.\n"
        intent = {
            "target_tables": [], "operation": "SELECT",
            "filters": [], "aggregations": [], "joins": [],
            "ordering": [], "grouping": [], "limit": None,
            "subquery_needed": False, "complexity": "simple", "ambiguities": [],
        }

    model_used = (
        GENERATOR_MODEL_COMPLEX
        if intent.get("complexity") == "complex"
        else GENERATOR_MODEL_DEFAULT
    )
    yield f"[3/6] Generating {dialect.upper()} SQL with {model_used}...\n"
    try:
        raw_response = await generate_sql(query, intent, schema_info, dialect)
    except Exception as exc:
        yield f"[ERROR] SQL generator failed: {exc}\n"
        return

    yield "[4/6] Validating SQL...\n"
    try:
        validation = validate_sql(raw_response, dialect, schema_info)
    except Exception as exc:
        yield f"[WARN] Validator failed: {exc}. Returning unvalidated result.\n"
        validation = {"valid": True, "sql": "", "syntax_errors": [], "schema_errors": [], "warnings": []}

    if validation["syntax_errors"] or validation["schema_errors"]:
        total_errors = len(validation["syntax_errors"]) + len(validation["schema_errors"])
        yield f"  -> {total_errors} error(s) found. Entering refinement loop.\n"
    else:
        yield "  -> Validation passed.\n"

    for w in validation.get("warnings", []):
        yield f"  [WARN] {w}\n"

    final_response = raw_response
    final_validation = validation

    if not validation["valid"]:
        yield "[5/6] Refining SQL (max 2 attempts)...\n"
        try:
            final_response, final_validation = await refine_sql(
                query, raw_response, validation, dialect, schema_info,
            )
        except Exception as exc:
            yield f"[WARN] Refiner failed: {exc}. Returning best available result.\n"
    else:
        yield "[5/6] No refinement needed.\n"

    for w in (final_validation.get("warnings") or []):
        yield f"  [WARN] {w}\n"

    # ── Synthetic data + sandbox ──────────────────────────────────────────
    if schema_info.get("table_names"):
        if dialect != "sqlite":
            yield f"[6/6] Generating synthetic data & running {dialect.upper()} sandbox...\n"
        else:
            yield "[6/6] Generating synthetic data & running SQLite sandbox...\n"

        try:
            mock_data = await generate_synthetic_data(schema_info, dialect)
        except Exception as exc:
            yield f"  [WARN] Synthetic data generation failed: {exc}. Using deterministic fallback.\n"
            from synthetic_data import _deterministic_fallback
            mock_data = _deterministic_fallback(schema_info, rows_per_table=8)

        # Prefer the validated/cleaned SQL; fall back to the raw generator
        # response so sandbox_manager's _extract_sql can parse the fenced block
        sql_for_sandbox = (
            final_validation.get("sql")
            or final_response
            or ""
        )
        sandbox_result = run_sandbox(
            sql_for_sandbox,
            dialect,
            schema_info,
            mock_data,
        )
    else:
        yield "[6/6] No schema provided — skipping sandbox.\n"
        from sandbox_manager import SandboxResult
        sandbox_result = SandboxResult(
            ok=False, columns=[], rows=[],
            error="No schema available for sandbox.",
            dialect=dialect, warnings=[], duration_ms=0, mock_preview={},
        )

    yield "\n---RESULT---\n"
    yield final_response
    yield sandbox_markdown(sandbox_result)
