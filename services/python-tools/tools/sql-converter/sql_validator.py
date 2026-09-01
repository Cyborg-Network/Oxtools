"""
SQL Validator — two-phase validation:
  Phase 1: sqlglot syntax parse for the target dialect.
  Phase 2: Column reference check against the parsed schema (if schema provided).
"""
import re

import sqlglot
from sqlglot import exp

# Map our dialect strings to sqlglot dialect names
_DIALECT_MAP = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "mssql": "tsql",
    "bigquery": "bigquery",
}


def _extract_sql(response: str) -> str:
    """Pull the first SQL code block out of a markdown response."""
    m = re.search(r"```(?:sql)?\s*\n(.*?)```", response, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    lines = response.split("\n")
    sql_lines = []
    for line in lines:
        if line.startswith("##"):
            break
        sql_lines.append(line)
    return "\n".join(sql_lines).strip()


def validate_sql(response: str, dialect: str, schema_info: dict) -> dict:
    """
    Args:
        response:    Raw generator output (may include markdown fences + explanation).
        dialect:     Target dialect string (e.g. "postgresql").
        schema_info: Output of schema_parser.parse_schema().
    Returns:
        {
          "valid": bool,
          "sql": "...",
          "syntax_errors": ["..."],
          "schema_errors": ["..."],
          "warnings": [],
        }
    """
    sql = _extract_sql(response)
    result = {
        "valid": False,
        "sql": sql,
        "syntax_errors": [],
        "schema_errors": [],
        "warnings": [],
    }

    if not sql:
        result["syntax_errors"].append("No SQL found in generator output.")
        return result

    dialect_key = _DIALECT_MAP.get(dialect.lower() if dialect else "", "postgres")
    try:
        parsed = sqlglot.parse(sql, dialect=dialect_key, error_level=sqlglot.ErrorLevel.RAISE)
        if not parsed:
            result["syntax_errors"].append("sqlglot returned no AST (empty parse result).")
            return result
    except sqlglot.errors.ParseError as exc:
        result["syntax_errors"] = [str(e) for e in exc.errors]
        return result

    if schema_info and schema_info.get("table_names"):
        known_tables = schema_info["tables"]
        all_columns: set[str] = set()
        for tinfo in known_tables.values():
            all_columns.update(tinfo["columns"].keys())

        for statement in parsed:
            for col in statement.find_all(exp.Column):
                col_name = col.name.lower() if col.name else ""
                table_name = col.table
                if table_name:
                    table_key = table_name.lower()
                    if table_key in known_tables:
                        if col_name and col_name not in known_tables[table_key]["columns"]:
                            result["schema_errors"].append(
                                f"Unknown column '{table_key}.{col_name}'"
                            )
                    else:
                        result["warnings"].append(
                            f"Unrecognized table or alias '{table_name}' for column '{col.name}'"
                        )
                else:
                    if col_name and col_name not in all_columns:
                        result["warnings"].append(
                            f"Unqualified column '{col.name}' not found in schema"
                        )

    result["valid"] = not result["syntax_errors"] and not result["schema_errors"]
    return result
