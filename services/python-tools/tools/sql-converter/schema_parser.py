"""
Programmatic schema parser — no LLM call.
Parses CREATE TABLE statements using sqlglot to extract:
  - table names
  - column names and data types
  - primary keys, foreign keys, NOT NULL constraints
"""
import sqlglot
from sqlglot import exp


def _extract_fk(fk: exp.ForeignKey, columns: list[str]) -> dict:
    ref_table = None
    ref_columns: list[str] = []
    ref = fk.args.get("reference")
    if isinstance(ref, exp.Reference):
        ref_table_expr = ref.this if isinstance(ref.this, exp.Table) else ref.find(exp.Table)
        if ref_table_expr is not None:
            ref_table = ref_table_expr.name.lower()
        ref_columns = [c.name.lower() for c in ref.find_all(exp.Column)]

    return {
        "columns": columns,
        "references": {"table": ref_table, "columns": ref_columns},
    }


def parse_schema(ddl: str) -> dict:
    """
    Args:
        ddl: Raw DDL string (one or more CREATE TABLE statements).
    Returns:
        {
          "tables": {
            "table_name": {
              "columns": {
                "column_name": {
                  "type": "VARCHAR(255)",
                  "not_null": True,
                },
              },
              "primary_keys": ["id"],
              "foreign_keys": [
                {"columns": ["user_id"], "references": {"table": "users", "columns": ["id"]}},
              ],
            },
          },
          "table_names": ["table_name"],
          "raw_ddl": "..."
        }
    Returns {"tables": {}, "table_names": [], "raw_ddl": ddl} on parse failure.
    """
    result = {"tables": {}, "table_names": [], "raw_ddl": ddl or ""}
    if not ddl or not ddl.strip():
        return result

    try:
        statements = sqlglot.parse(ddl)
    except Exception:
        return result

    for stmt in statements:
        if not isinstance(stmt, exp.Create):
            continue
        table_expr = stmt.find(exp.Table)
        if table_expr is None:
            continue
        table_name = table_expr.name.lower()
        columns: dict = {}
        pks: list[str] = []
        fks: list[dict] = []

        for col_def in stmt.find_all(exp.ColumnDef):
            col_name = col_def.name.lower()
            data_type_expr = col_def.args.get("kind")
            data_type = data_type_expr.sql() if data_type_expr is not None else ""
            not_null = False

            for constraint in col_def.find_all(exp.ColumnConstraint):
                c = constraint.this
                if isinstance(c, exp.NotNullColumnConstraint):
                    not_null = True
                elif isinstance(c, exp.PrimaryKeyColumnConstraint):
                    if col_name not in pks:
                        pks.append(col_name)
                elif isinstance(c, exp.ForeignKey):
                    fks.append(_extract_fk(c, [col_name]))

            columns[col_name] = {
                "type": data_type,
                "not_null": not_null,
            }

        # Table-level PRIMARY KEY / FOREIGN KEY constraints
        for constraint in stmt.find_all(exp.PrimaryKey):
            for col_expr in constraint.find_all(exp.Column):
                col_name = col_expr.name.lower()
                if col_name not in pks:
                    pks.append(col_name)

        for fk in stmt.find_all(exp.ForeignKey):
            fk_cols = [c.name.lower() for c in fk.find_all(exp.Column)]
            if fk_cols:
                fks.append(_extract_fk(fk, fk_cols))

        result["tables"][table_name] = {
            "columns": columns,
            "primary_keys": pks,
            "foreign_keys": fks,
        }

    result["table_names"] = list(result["tables"].keys())
    return result
