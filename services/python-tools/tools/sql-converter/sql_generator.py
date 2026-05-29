"""
SQL Generator — produces dialect-specific SQL from the structured query plan.

Model routing:
  - simple / moderate  → qwen-3-coder-30b   (fast, accurate for standard SQL)
  - complex            → deepseek-r1-0528    (reasoning model for analytical queries)
"""
from llm_client import call_oxlo_chat

GENERATOR_MODEL_DEFAULT = "qwen-3-coder-30b"
GENERATOR_MODEL_COMPLEX = "deepseek-r1-0528"

_SYSTEM_TEMPLATE = """\
You are an expert {dialect} developer.
Generate a single, correct SQL query for the following request.

Rules:
1. Output ONLY a fenced SQL code block — nothing else before the opening fence.
2. Use {dialect}-specific syntax strictly (e.g. ILIKE for PostgreSQL, IFNULL for MySQL).
3. If a schema is provided, use ONLY the table and column names that appear in it.
4. Add inline comments for non-obvious logic.
5. After the code block, output:
   ## Explanation
   (step-by-step description)
   ## Performance Notes
   (indexing suggestions, join order, etc.)
   ## Dialect Notes
   (any {dialect}-specific caveats)
"""


async def generate_sql(
    query: str,
    intent: dict,
    schema_info: dict,
    dialect: str,
) -> str:
    """
    Args:
        query:       Original natural language request.
        intent:      Output of intent_classifier.classify_intent().
        schema_info: Output of schema_parser.parse_schema().
        dialect:     Target dialect string.
    Returns:
        Raw model response (SQL block + explanation text).
    """
    complexity = intent.get("complexity", "simple")
    model = GENERATOR_MODEL_COMPLEX if complexity == "complex" else GENERATOR_MODEL_DEFAULT

    schema_section = ""
    if schema_info.get("raw_ddl", "").strip():
        schema_section = f"\nAvailable schema:\n```sql\n{schema_info['raw_ddl']}\n```\n"

    intent_section = (
        f"Query plan:\n"
        f"  Operation: {intent.get('operation', 'SELECT')}\n"
        f"  Tables: {', '.join(intent.get('target_tables', []))}\n"
        f"  Filters: {'; '.join(intent.get('filters', []))}\n"
        f"  Aggregations: {'; '.join(intent.get('aggregations', []))}\n"
        f"  Joins: {'; '.join(intent.get('joins', []))}\n"
        f"  Ordering: {'; '.join(intent.get('ordering', []))}\n"
        f"  Grouping: {'; '.join(intent.get('grouping', []))}\n"
        f"  Limit: {intent.get('limit')}\n"
    )

    user_prompt = (
        f"Natural language request:\n{query}\n\n"
        f"{schema_section}\n"
        f"{intent_section}\n"
        "Generate the SQL query."
    )

    system = _SYSTEM_TEMPLATE.format(dialect=dialect or "PostgreSQL")
    return await call_oxlo_chat(
        model,
        system,
        user_prompt,
        max_tokens=2048,
        temperature=0.2,
    )
