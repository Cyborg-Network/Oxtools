"""
SQL Converter — Multi-Agent Tool Entry Point
=============================================
Pipeline:
  1. Schema Parser   — programmatic DDL parsing (sqlglot)
  2. Intent Classifier — LLM: deepseek-v3.2
  3. SQL Generator   — LLM: qwen-3-coder-30b (simple/moderate)
                            deepseek-r1-0528   (complex)
  4. SQL Validator   — programmatic: sqlglot + schema column check
  5. SQL Refiner     — LLM: qwen-3-coder-30b (max 2 retries if validation fails)
"""

from intent_classifier import classify_intent
from schema_parser import parse_schema
from sql_generator import GENERATOR_MODEL_COMPLEX, GENERATOR_MODEL_DEFAULT, generate_sql
from sql_refiner import refine_sql
from sql_sandbox import run_sandbox, sandbox_markdown
from sql_validator import validate_sql

MANIFEST = {
    "id": "sql-converter",
    "name": "Natural Language to SQL",
    "description": "Multi-agent pipeline: schema-aware, validated, dialect-correct SQL generation.",
    "author": "Franci-343",
    "version": "1.0.1",
}


async def run(data: dict):
    query = (data.get("query") or "").strip()
    dialect = (data.get("dialect") or "postgresql").strip()
    mode = (data.get("mode") or "generate").strip()
    sandbox_query = (data.get("sandboxQuery") or "").strip()

    schema_ddl = (data.get("schema") or "").strip()
    schema_file_raw = (data.get("schemaFile") or "").strip()

    if schema_file_raw:
        # The "files" input type in page.tsx prepends a header line:
        #   --- FILE: my_schema.sql ---
        #   <actual DDL content>
        # Strip that header before parsing.
        lines = schema_file_raw.split("\n")
        if lines and lines[0].startswith("--- FILE:"):
            schema_ddl = "\n".join(lines[1:]).strip()
        else:
            schema_ddl = schema_file_raw

    if mode == "sandbox":
        try:
            schema_info = parse_schema(schema_ddl)
        except Exception:
            schema_info = {"tables": {}, "table_names": [], "raw_ddl": ""}
        return {
            "result": run_sandbox(
                data.get("sql") or query,
                dialect,
                schema_info,
                int(data.get("rowsPerTable") or 8),
            )
        }

    if sandbox_query:
        async def sandbox_stream():
            yield "[1/2] Building mock sandbox database from schema...\n"
            try:
                schema_info = parse_schema(schema_ddl)
            except Exception as exc:
                yield f"[ERROR] Schema parser failed: {exc}\n"
                return

            yield "[2/2] Running read-only SQL against mock data...\n"
            payload = run_sandbox(sandbox_query, dialect, schema_info)

            yield "\n---RESULT---\n"
            yield "# SQL Sandbox Result\n"
            yield sandbox_markdown(payload)

        return sandbox_stream()

    async def stream():
        if not query:
            yield "[ERROR] Query cannot be empty.\n"
            return

        yield "[1/5] Parsing schema...\n"
        try:
            schema_info = parse_schema(schema_ddl)
        except Exception as exc:
            yield f"[WARN] Schema parser failed: {exc}. Continuing without schema.\n"
            schema_info = {"tables": {}, "table_names": [], "raw_ddl": ""}

        yield "[2/5] Classifying intent...\n"
        try:
            intent = await classify_intent(query, schema_info, dialect)
        except Exception as exc:
            yield f"[WARN] Intent classifier failed: {exc}. Using defaults.\n"
            intent = {
                "target_tables": [],
                "operation": "SELECT",
                "filters": [],
                "aggregations": [],
                "joins": [],
                "ordering": [],
                "grouping": [],
                "limit": None,
                "subquery_needed": False,
                "complexity": "simple",
                "ambiguities": [],
            }

        model_used = (
            GENERATOR_MODEL_COMPLEX
            if intent.get("complexity") == "complex"
            else GENERATOR_MODEL_DEFAULT
        )
        yield f"[3/5] Generating SQL with {model_used}...\n"
        try:
            raw_response = await generate_sql(query, intent, schema_info, dialect)
        except Exception as exc:
            yield f"[ERROR] SQL generator failed: {exc}\n"
            return

        yield "[4/5] Validating SQL...\n"
        try:
            validation = validate_sql(raw_response, dialect, schema_info)
        except Exception as exc:
            yield f"[WARN] Validator failed: {exc}. Returning unvalidated result.\n"
            validation = {
                "valid": True,
                "sql": "",
                "syntax_errors": [],
                "schema_errors": [],
                "warnings": [],
            }

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
            yield "[5/5] Refining (max 2 attempts)...\n"
            try:
                final_response, final_validation = await refine_sql(
                    query,
                    raw_response,
                    validation,
                    dialect,
                    schema_info,
                )
            except Exception as exc:
                yield f"[WARN] Refiner failed: {exc}. Returning best available result.\n"
        else:
            yield "[5/5] No refinement needed.\n"

        if final_validation.get("warnings"):
            for w in final_validation["warnings"]:
                yield f"  [WARN] {w}\n"

        sandbox_payload = run_sandbox(
            final_validation.get("sql") or "",
            dialect,
            schema_info,
        )

        yield "\n---RESULT---\n"
        yield final_response
        yield sandbox_markdown(sandbox_payload)

    return stream()
