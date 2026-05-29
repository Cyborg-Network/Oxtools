"""
Intent Classifier — analyses natural language and returns a structured query plan.
Model: deepseek-v3.2  (fast, good at structured JSON extraction)
"""
import json
import re

from llm_client import call_oxlo_chat

INTENT_MODEL = "deepseek-v3.2"

_SYSTEM = """\
You are an expert at analysing natural language database queries.
Respond ONLY with a valid JSON object — no markdown fences, no explanation.
The JSON must have these keys:
  - "target_tables": list of table names the query touches
  - "operation": one of "SELECT" | "INSERT" | "UPDATE" | "DELETE" | "DDL"
  - "filters": list of filter condition descriptions (plain English)
  - "aggregations": list of aggregation descriptions (e.g. "COUNT of orders", "SUM of amount")
  - "joins": list of join descriptions (e.g. "users JOIN orders ON users.id = orders.user_id")
  - "ordering": list of ordering descriptions
  - "grouping": list of columns to group by
  - "limit": integer or null
  - "subquery_needed": boolean
  - "complexity": one of "simple" | "moderate" | "complex"
  - "ambiguities": list of strings describing unclear aspects (empty list if none)
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
    text = re.sub(r"```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


async def classify_intent(query: str, schema_info: dict, dialect: str) -> dict:
    """
    Args:
        query:       Natural language query from the user.
        schema_info: Output of schema_parser.parse_schema().
        dialect:     Target SQL dialect (e.g. "postgresql").
    Returns:
        Structured query plan dict. Falls back to minimal defaults on error.
    """
    table_summary = ""
    if schema_info.get("table_names"):
        lines = []
        for tname, tinfo in schema_info["tables"].items():
            col_names = list(tinfo["columns"].keys())
            lines.append(f"  - {tname}: {', '.join(col_names)}")
        table_summary = "Available tables:\n" + "\n".join(lines)

    user_prompt = (
        f"Natural language query: {query}\n\n"
        f"Target dialect: {dialect or 'postgresql'}\n"
        f"{table_summary}\n\n"
        "Return the JSON query plan."
    )

    try:
        raw = await call_oxlo_chat(
            INTENT_MODEL,
            _SYSTEM,
            user_prompt,
            max_tokens=700,
            temperature=0.1,
        )
        plan = _extract_json(raw)
    except Exception:
        plan = {}

    defaults = {
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
    defaults.update({k: v for k, v in plan.items() if v is not None})
    return defaults
