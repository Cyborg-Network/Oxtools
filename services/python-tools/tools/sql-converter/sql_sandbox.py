"""
SQLite sandbox for generated SQL.

Creates an in-memory database from the parsed schema, inserts deterministic
mock rows, translates the generated query to SQLite when possible, and runs
read-only statements only.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Any

import sqlglot

_DIALECT_MAP = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "mssql": "tsql",
    "bigquery": "bigquery",
}


def _extract_sql(sql: str) -> str:
    text = (sql or "").strip()
    match = re.search(r"```(?:sql)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def _sqlite_type(raw_type: str) -> str:
    t = (raw_type or "").upper()
    if any(x in t for x in ("INT", "SERIAL", "BIGSERIAL")):
        return "INTEGER"
    if any(x in t for x in ("DECIMAL", "NUMERIC", "REAL", "DOUBLE", "FLOAT")):
        return "REAL"
    if any(x in t for x in ("BOOL",)):
        return "INTEGER"
    return "TEXT"


def _strip_identifier(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", name or "")


def _quote_identifier(name: str) -> str:
    safe = _strip_identifier(name)
    return f'"{safe}"'


def _is_read_only(sql: str, dialect: str) -> tuple[bool, str | None]:
    text = (sql or "").strip()
    if not text:
        return False, "No SQL query was provided."

    blocked = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE|GRANT|REVOKE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
        re.IGNORECASE,
    )
    if blocked.search(text):
        return False, "Sandbox only allows read-only SELECT/WITH queries."

    dialect_key = _DIALECT_MAP.get((dialect or "").lower(), "postgres")
    try:
        expressions = sqlglot.parse(text, read=dialect_key)
    except Exception as exc:
        return False, f"Could not parse SQL before sandbox execution: {exc}"

    for expr in expressions:
        root = expr.key.upper() if getattr(expr, "key", None) else ""
        if root == "SEMICOLON":
            continue
        if root not in {"SELECT", "WITH", "UNION"}:
            return False, "Sandbox only allows SELECT/WITH style queries."

    return True, None


def _translate_to_sqlite(sql: str, dialect: str) -> tuple[str, str | None]:
    if (dialect or "").lower() == "sqlite":
        return sql, None

    dialect_key = _DIALECT_MAP.get((dialect or "").lower(), "postgres")
    try:
        translated = sqlglot.transpile(sql, read=dialect_key, write="sqlite")
        if translated:
            return ";\n".join(translated), None
    except Exception as exc:
        return sql, f"Could not fully translate {dialect} SQL to SQLite: {exc}"

    return sql, None


def _mock_value(table: str, column: str, raw_type: str, row_index: int) -> Any:
    name = column.lower()
    typ = (raw_type or "").upper()

    if name == "id" or name.endswith("_id"):
        return row_index
    if "email" in name:
        return f"{table}{row_index}@example.test"
    if "name" in name or "title" in name:
        return f"{table.title()} {row_index}"
    if "status" in name:
        return ["active", "pending", "archived"][row_index % 3]
    if "category" in name or "type" in name:
        return ["standard", "premium", "trial"][row_index % 3]
    if "created" in name or "updated" in name or "date" in name or "time" in name:
        return (datetime(2026, 1, 1) + timedelta(days=row_index)).isoformat(sep=" ")
    if "price" in name or "amount" in name or "total" in name or "salary" in name:
        return round(19.5 + row_index * 7.25, 2)
    if "count" in name or "qty" in name or "quantity" in name:
        return row_index * 2
    if "BOOL" in typ:
        return row_index % 2
    if any(x in typ for x in ("INT", "SERIAL")):
        return row_index * 10
    if any(x in typ for x in ("DECIMAL", "NUMERIC", "REAL", "DOUBLE", "FLOAT")):
        return round(row_index * 3.14, 2)
    return f"{column}_{row_index}"


def _build_database(conn: sqlite3.Connection, schema_info: dict, rows_per_table: int) -> dict:
    tables = schema_info.get("tables") or {}
    preview: dict[str, list[dict[str, Any]]] = {}

    for table, info in tables.items():
        columns = info.get("columns") or {}
        if not columns:
            continue

        col_defs = []
        for col, cinfo in columns.items():
            col_defs.append(f"{_quote_identifier(col)} {_sqlite_type(cinfo.get('type', ''))}")

        conn.execute(f"CREATE TABLE {_quote_identifier(table)} ({', '.join(col_defs)})")

    for table, info in tables.items():
        columns = info.get("columns") or {}
        if not columns:
            continue

        column_names = list(columns.keys())
        placeholders = ", ".join(["?"] * len(column_names))
        insert_sql = (
            f"INSERT INTO {_quote_identifier(table)} "
            f"({', '.join(_quote_identifier(c) for c in column_names)}) "
            f"VALUES ({placeholders})"
        )

        rows = []
        for row_index in range(1, rows_per_table + 1):
            row = {
                col: _mock_value(table, col, columns[col].get("type", ""), row_index)
                for col in column_names
            }
            rows.append(row)
            conn.execute(insert_sql, [row[col] for col in column_names])
        preview[table] = rows[:3]

    conn.commit()
    return preview


def run_sandbox(sql: str, dialect: str, schema_info: dict, rows_per_table: int = 8) -> dict:
    sql = _extract_sql(sql)
    safe, reason = _is_read_only(sql, dialect)
    if not safe:
        return {
            "ok": False,
            "sql": sql,
            "sqliteSql": "",
            "columns": [],
            "rows": [],
            "mockPreview": {},
            "warnings": [],
            "error": reason,
        }

    if not (schema_info.get("tables") or {}):
        return {
            "ok": False,
            "sql": sql,
            "sqliteSql": "",
            "columns": [],
            "rows": [],
            "mockPreview": {},
            "warnings": [],
            "error": "A schema is required to build the mock sandbox database.",
        }

    sqlite_sql, translation_warning = _translate_to_sqlite(sql, dialect)
    warnings = [translation_warning] if translation_warning else []

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        preview = _build_database(conn, schema_info, rows_per_table)
        cursor = conn.execute(sqlite_sql)
        rows = [dict(row) for row in cursor.fetchmany(100)]
        columns = [desc[0] for desc in cursor.description or []]
        return {
            "ok": True,
            "sql": sql,
            "sqliteSql": sqlite_sql,
            "columns": columns,
            "rows": rows,
            "mockPreview": preview,
            "warnings": warnings,
            "error": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "sql": sql,
            "sqliteSql": sqlite_sql,
            "columns": [],
            "rows": [],
            "mockPreview": {},
            "warnings": warnings,
            "error": str(exc),
        }
    finally:
        conn.close()


def _markdown_table(columns: list[str], rows: list[dict[str, Any]]) -> str:
    if not columns:
        return "_The query executed successfully and returned no columns._"

    def cell(value: Any) -> str:
        return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:20]:
        lines.append("| " + " | ".join(cell(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def sandbox_markdown(payload: dict) -> str:
    status = "passed" if payload.get("ok") else "failed"
    lines = [
        "\n\n## Sandbox Test",
        f"Status: **{status}**",
    ]

    if payload.get("error"):
        lines.extend(["", f"Error: `{payload['error']}`"])

    for warning in payload.get("warnings") or []:
        lines.extend(["", f"Warning: {warning}"])

    if payload.get("ok"):
        rows = payload.get("rows") or []
        columns = payload.get("columns") or []
        lines.extend(
            [
                "",
                f"Rows returned from mock data: **{len(rows)}**",
                "",
                _markdown_table(columns, rows),
            ]
        )

    preview = payload.get("mockPreview") or {}
    if preview:
        lines.extend(["", "### Mock Data Preview"])
        for table_name, rows in preview.items():
            lines.extend(
                [
                    "",
                    f"**{table_name}**",
                    "",
                    "```json",
                    json.dumps(rows, ensure_ascii=False, indent=2),
                    "```",
                ]
            )

    if payload.get("sqliteSql") and payload.get("sqliteSql") != payload.get("sql"):
        lines.extend(
            [
                "",
                "### SQLite Query Used In Sandbox",
                "```sql",
                payload["sqliteSql"],
                "```",
            ]
        )

    return "\n".join(lines)
