"""
Synthetic Data Generator — produces realistic, schema-aware mock rows via LLM.

The LLM receives the full DDL and returns a JSON object shaped:
  {
    "table1": [ {"col1": val, "col2": val, ...}, ... ],
    "table2": [ ... ]
  }

Rows respect:
  - Data types (integers, floats, booleans, dates)
  - Foreign key relationships (FK column values exist in the referenced table)
  - NOT NULL constraints
  - Realistic domain values (emails, names, prices, statuses, etc.)

Falls back to a deterministic local generator if the LLM call fails.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from llm_client import call_oxlo_chat

_MODEL = "qwen-3-coder-30b"


def _enum_values(raw_type: str) -> list[str]:
    match = re.search(r"\b(?:ENUM|SET)\s*\((.*?)\)", raw_type or "", re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    parts = re.findall(r"'((?:\\'|[^'])*)'|\"((?:\\\"|[^\"])*)\"", match.group(1))
    values = [a or b for a, b in parts if (a or b)]
    return [v.replace("\\'", "'").replace('\\"', '"') for v in values]


def _varchar_limit(raw_type: str) -> int | None:
    match = re.search(r"\b(?:VARCHAR|CHAR|NVARCHAR|NCHAR)\s*\(\s*(\d+)\s*\)", raw_type or "", re.IGNORECASE)
    return int(match.group(1)) if match else None


def _normalize_type(raw_type: str) -> str:
    t = (raw_type or "").upper()
    if any(x in t for x in ("BOOL", "BOOLEAN", "TINYINT(1)", "BIT")):
        return "BOOL"
    if any(x in t for x in ("INT", "SERIAL", "BIGINT", "SMALLINT", "TINYINT")):
        return "INT"
    if any(x in t for x in ("FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC", "MONEY")):
        return "FLOAT"
    if any(x in t for x in ("DATE", "TIME", "TIMESTAMP", "DATETIME")):
        return "DATE"
    return "STRING"


def _clip_text(value: str, raw_type: str) -> str:
    limit = _varchar_limit(raw_type)
    if limit is not None:
        return value[:limit]
    return value

_SYSTEM = """\
You are a database expert generating realistic synthetic test data.
Given a SQL schema (DDL), generate coherent rows for each table.

Rules:
1. Respect all data types strictly (integers as numbers, not strings).
2. Honour foreign key relationships — FK values must appear in the parent table.
3. Generate diverse, realistic values (real-looking emails, names, prices, dates).
4. Do NOT use placeholder strings like "string1", "col_1". Use domain-appropriate values.
5. Respond ONLY with a valid JSON object — no markdown, no explanation.
   Shape: {"table_name": [{"col": value, ...}, ...], ...}
6. Generate exactly the number of rows requested per table.
7. Maintain referential integrity: if orders.user_id references users.id, the values must match.
"""


async def generate_synthetic_data(
    schema_info: dict,
    dialect: str,
    rows_per_table: int = 8,
) -> dict[str, list[dict[str, Any]]]:
    """
    Call the LLM to generate synthetic rows for every table in schema_info.

    Returns:
        {table_name: [row_dict, ...]}  — or deterministic fallback on error.
    """
    ddl = (schema_info.get("raw_ddl") or "").strip()
    tables = schema_info.get("tables") or {}

    if not tables:
        return {}

    # Build a compact schema summary for the prompt
    schema_summary = _build_schema_summary(schema_info)

    user_prompt = (
        f"Schema (DDL):\n```sql\n{ddl or schema_summary}\n```\n\n"
        f"Target dialect: {dialect}\n"
        f"Rows per table: {rows_per_table}\n\n"
        "Generate the synthetic data JSON now."
    )

    try:
        raw = await call_oxlo_chat(
            _MODEL,
            _SYSTEM,
            user_prompt,
            max_tokens=4096,
            temperature=0.7,
        )
        data = _parse_json(raw)
        if data and isinstance(data, dict):
            coerced = _coerce_types(data, schema_info)
            # Normalize table name keys to lowercase (matches schema_info)
            coerced = {k.lower(): v for k, v in coerced.items()}

            # Fill in any tables the LLM missed using the deterministic fallback
            expected_tables = {
                t.lower() for t in (schema_info.get("table_names") or [])
            }
            missing = expected_tables - set(coerced.keys())
            if missing:
                fallback = _deterministic_fallback(schema_info, rows_per_table)
                for tname in missing:
                    if tname in fallback:
                        coerced[tname] = fallback[tname]

            return coerced
    except Exception:
        pass

    # Deterministic fallback
    return _deterministic_fallback(schema_info, rows_per_table)


def _build_schema_summary(schema_info: dict) -> str:
    lines = []
    for tname, tinfo in (schema_info.get("tables") or {}).items():
        cols = ", ".join(
            f"{cname} {cinfo.get('type', 'TEXT')}"
            for cname, cinfo in (tinfo.get("columns") or {}).items()
        )
        fks = tinfo.get("foreign_keys") or []
        fk_desc = "; ".join(
            f"{','.join(fk['columns'])} -> {fk['references']['table']}({','.join(fk['references']['columns'])})"
            for fk in fks if fk.get("columns") and fk.get("references")
        )
        line = f"  {tname}({cols})"
        if fk_desc:
            line += f"  -- FK: {fk_desc}"
        lines.append(line)
    return "Tables:\n" + "\n".join(lines)


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```[a-zA-Z0-9]*\n?", "", text)
    text = re.sub(r"```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _coerce_types(
    data: dict[str, list[dict]],
    schema_info: dict,
) -> dict[str, list[dict[str, Any]]]:
    """Cast LLM-generated values to the correct Python types."""
    tables = schema_info.get("tables") or {}
    result: dict[str, list[dict[str, Any]]] = {}

    for tname, rows in data.items():
        if not isinstance(rows, list):
            continue
        col_types = {}
        tname_lower = tname.lower()
        matched_tname = next((k for k in tables if k.lower() == tname_lower), None)
        if matched_tname:
            col_types = {
                cname.lower(): cinfo.get("type", "TEXT")
                for cname, cinfo in tables[matched_tname].get("columns", {}).items()
            }
        result[tname] = [
            _coerce_row({k.lower(): v for k, v in row.items()}, col_types)
            for row in rows
            if isinstance(row, dict)
        ]

    return result


def _decimal_precision(raw_type: str) -> tuple[int, int] | None:
    """
    Parse DECIMAL(M, D) or NUMERIC(M, D) and return (M, D).
    Returns None if the type has no explicit precision.
    """
    m = re.search(
        r"\b(?:DECIMAL|NUMERIC|DEC|FIXED)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)",
        raw_type or "",
        re.IGNORECASE,
    )
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _clamp_decimal(val: float, raw_type: str) -> float:
    """
    Clamp a float to fit within DECIMAL(M, D).
    e.g. DECIMAL(3, 2) -> max 9.99, min -9.99.
    """
    precision = _decimal_precision(raw_type)
    if precision is None:
        return val
    m, d = precision
    integer_digits = m - d
    max_val = (10**integer_digits) - (10 ** -d)
    return max(min(val, max_val), -max_val)


def _coerce_row(row: dict, col_types: dict[str, str]) -> dict[str, Any]:
    out = {}
    for col, val in row.items():
        raw_type = col_types.get(col) or "TEXT"
        category = _normalize_type(raw_type)
        enum_vals = _enum_values(raw_type)
        if enum_vals:
            if val is None:
                out[col] = enum_vals[0]
            elif str(val) in enum_vals:
                out[col] = str(val)
            else:
                val_lower = str(val).lower()
                ci_match = next((ev for ev in enum_vals if ev.lower() == val_lower), None)
                out[col] = (
                    ci_match
                    if ci_match is not None
                    else enum_vals[(hash(f"{col}:{val}") % len(enum_vals))]
                )
            continue
        if category == "INT":
            try:
                out[col] = int(val) if val is not None else None
            except (TypeError, ValueError):
                out[col] = None
        elif category == "FLOAT":
            try:
                f = float(val) if val is not None else None
                out[col] = _clamp_decimal(f, raw_type) if f is not None else None
            except (TypeError, ValueError):
                out[col] = None
        elif category == "BOOL":
            if val is None:
                out[col] = None
            elif isinstance(val, bool):
                out[col] = 1 if val else 0
            elif isinstance(val, int):
                out[col] = 1 if val else 0
            elif isinstance(val, str):
                out[col] = 1 if val.lower() in ("true", "1", "yes", "on") else 0
            else:
                out[col] = 1 if val else 0
        elif category == "DATE":
            out[col] = str(val) if val is not None else None
        else:
            out[col] = _clip_text(str(val), raw_type) if val is not None else None
    return out


# ---------------------------------------------------------------------------
# Deterministic fallback (no LLM)
# ---------------------------------------------------------------------------

def _deterministic_fallback(
    schema_info: dict,
    rows_per_table: int,
) -> dict[str, list[dict[str, Any]]]:
    """
    Generate basic but valid synthetic rows without LLM.
    Used when the LLM call fails or returns unusable data.
    """
    tables = schema_info.get("tables") or {}
    result: dict[str, list[dict[str, Any]]] = {}

    # First pass: assign IDs so FK references work
    id_map: dict[str, list[int]] = {}
    for tname, tinfo in tables.items():
        pks = tinfo.get("primary_keys") or []
        if pks:
            id_map[tname] = list(range(1, rows_per_table + 1))

    for tname, tinfo in tables.items():
        cols = tinfo.get("columns") or {}
        fks = {
            fk_col: fk["references"]
            for fk in (tinfo.get("foreign_keys") or [])
            for fk_col in fk.get("columns", [])
            if fk.get("references")
        }

        rows = []
        for i in range(1, rows_per_table + 1):
            row: dict[str, Any] = {}
            for cname, cinfo in cols.items():
                raw_type = (cinfo.get("type") or "").upper()
                # FK resolution
                if cname in fks:
                    ref = fks[cname]
                    ref_table = ref.get("table")
                    if ref_table and ref_table in id_map:
                        row[cname] = id_map[ref_table][(i - 1) % len(id_map[ref_table])]
                        continue
                row[cname] = _mock_value(tname, cname, raw_type, i)
            rows.append(row)
        result[tname] = rows

    # Ensure all keys are lowercase for consistency
    return {k.lower(): v for k, v in result.items()}


def _mock_value(table: str, column: str, raw_type: str, idx: int) -> Any:
    name = column.lower()
    raw_upper = (raw_type or "").upper()
    category = _normalize_type(raw_type)
    enum_vals = _enum_values(raw_type)

    if enum_vals:
        if "status" in name:
            preferred = [
                v for v in enum_vals
                if any(k in v.lower() for k in ("active", "pending", "trial", "paid", "free"))
                ]
            if preferred:
                return preferred[(idx - 1) % len(preferred)]
        return enum_vals[(idx - 1) % len(enum_vals)]

    if category == "BOOL":
        return idx % 2

    if raw_upper.startswith("TIME") and "TIMESTAMP" not in raw_upper and "DATETIME" not in raw_upper:
        return f"{(idx * 3) % 24:02d}:{(idx * 7) % 60:02d}:00"

    # Identity / PK
    if name == "id" or name.endswith("_id") and "fk" not in name:
        return idx
    # Semantic heuristics
    if "email" in name:
        return f"user{idx}@example.test"
    if "username" in name or "login" in name:
        return f"user_{idx}"
    if "first_name" in name or name == "firstname":
        names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]
        return names[(idx - 1) % len(names)]
    if "last_name" in name or name == "lastname":
        surnames = ["Smith", "Jones", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore"]
        return surnames[(idx - 1) % len(surnames)]
    if "name" in name or "title" in name:
        return _clip_text(f"{table.title()} {idx}", raw_type)
    if "phone" in name:
        return f"+1-555-{idx:04d}"
    if "address" in name or "street" in name:
        return _clip_text(f"{idx * 10} Main Street", raw_type)
    if "city" in name:
        cities = ["New York", "London", "Paris", "Tokyo", "Berlin"]
        return cities[(idx - 1) % len(cities)]
    if "country" in name:
        return ["USA", "UK", "France", "Japan", "Germany"][(idx - 1) % 5]
    if "status" in name:
        return ["active", "pending", "archived"][(idx - 1) % 3]
    if "category" in name or "type" in name:
        return ["standard", "premium", "trial"][(idx - 1) % 3]
    if "price" in name or "amount" in name or "total" in name or "salary" in name:
        return round(19.99 + idx * 7.50, 2)
    if "count" in name or "qty" in name or "quantity" in name:
        return idx * 2
    if "created" in name or "updated" in name or "date" in name or "time" in name:
        if "TIMESTAMP" in raw_upper or "DATETIME" in raw_upper:
            return (datetime(2025, 1, 1) + timedelta(days=idx * 7)).strftime("%Y-%m-%d %H:%M:%S")
        return (datetime(2025, 1, 1) + timedelta(days=idx * 7)).strftime("%Y-%m-%d")
    if "description" in name or "notes" in name or "comment" in name:
        return _clip_text(f"Sample {table} record number {idx}.", raw_type)
    if "url" in name or "link" in name:
        return f"https://example.com/{table}/{idx}"
    if "image" in name or "avatar" in name or "photo" in name:
        return f"https://cdn.example.com/{table}/{idx}.jpg"
    if "color" in name or "colour" in name:
        return ["#FF5733", "#33FF57", "#3357FF", "#F1C40F", "#8E44AD"][(idx - 1) % 5]
    if "rating" in name or "score" in name:
        return round(1 + (idx % 5), 1)
    if "active" in name or "enabled" in name or "verified" in name:
        return idx % 2
    # Type-based fallbacks
    if category == "INT":
        return idx * 10
    if category == "FLOAT":
        return _clamp_decimal(round(idx * 3.14, 2), raw_type)
    if category == "DATE":
        if "TIMESTAMP" in raw_upper or "DATETIME" in raw_upper:
            return (datetime(2025, 1, 1) + timedelta(days=idx * 7)).strftime("%Y-%m-%d %H:%M:%S")
        return (datetime(2025, 1, 1) + timedelta(days=idx * 7)).strftime("%Y-%m-%d")
    return _clip_text(f"{column}_{idx}", raw_type)
