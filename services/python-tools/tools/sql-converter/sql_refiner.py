"""
SQL Refiner — feeds validation errors back to the generator and retries.
Max 2 refinement attempts. Model: qwen-3-coder-30b.
"""
from llm_client import call_oxlo_chat
from sql_validator import validate_sql

REFINER_MODEL = "qwen-3-coder-30b"

_SYSTEM = """\
You are an expert SQL developer fixing a broken SQL query.
You will receive the original request, the broken SQL, and the specific errors.
Output ONLY a corrected fenced SQL code block, followed by the same ## Explanation,
## Performance Notes, and ## Dialect Notes sections as before.
Do NOT repeat the errors. Just output the corrected SQL and sections.
"""


async def refine_sql(
    original_query: str,
    previous_response: str,
    validation: dict,
    dialect: str,
    schema_info: dict,
    max_retries: int = 2,
) -> tuple[str, dict]:
    """
    Args:
        original_query:    User's natural language request.
        previous_response: Last generator output (SQL + explanation).
        validation:        Output of validate_sql() for the previous response.
        dialect:           Target dialect.
        schema_info:       Parsed schema.
        max_retries:       Maximum number of refinement attempts (default 2).
    Returns:
        (final_response, final_validation) — best available result after retries.
    """
    response = previous_response
    val = validation

    for _ in range(max_retries):
        if val["valid"]:
            break

        errors = val["syntax_errors"] + val["schema_errors"]
        error_summary = "\n".join(f"  - {e}" for e in errors)

        schema_section = ""
        if schema_info.get("raw_ddl", "").strip():
            schema_section = f"\nSchema:\n```sql\n{schema_info['raw_ddl']}\n```"

        user_prompt = (
            f"Original request: {original_query}\n\n"
            f"Previous SQL output:\n{response}\n\n"
            f"Errors:\n{error_summary}\n"
            f"Target dialect: {dialect}\n"
            f"{schema_section}\n\n"
            "Output the corrected SQL query."
        )

        try:
            response = await call_oxlo_chat(
                REFINER_MODEL,
                _SYSTEM,
                user_prompt,
                max_tokens=2048,
                temperature=0.2,
            )
            val = validate_sql(response, dialect, schema_info)
        except Exception:
            break

    return response, val
