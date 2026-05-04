"""
JSON to Schema V2 — Deterministic Compilers
=============================================
Pure Python code generators for each output format.
These take a structured schema definition (from the LLM architect)
and produce syntactically perfect, production-ready code.

ZERO LLM involvement — this is deterministic compilation.

KEY FIX (v2.1): All FK field accessors use _get_fk_field() which
handles multiple key name variants from LLM output:
  referencesTable / references_table / refTable / ref_table / table
"""

import logging

logger = logging.getLogger("json-to-schema")


# ─── Type Mapping ─────────────────────────────────────────────────────

PG_TYPE_MAP = {
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "float": "DOUBLE PRECISION",
    "decimal": "DECIMAL(10, 2)",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP WITH TIME ZONE",
    "timestamp": "TIMESTAMP WITH TIME ZONE",
    "uuid": "UUID",
    "json": "JSONB",
    "jsonb": "JSONB",
    "array": "JSONB",
    "serial": "SERIAL",
    "bigserial": "BIGSERIAL",
}

MYSQL_TYPE_MAP = {
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "integer": "INT",
    "bigint": "BIGINT",
    "float": "DOUBLE",
    "decimal": "DECIMAL(10, 2)",
    "boolean": "TINYINT(1)",
    "date": "DATE",
    "datetime": "DATETIME",
    "timestamp": "TIMESTAMP",
    "uuid": "CHAR(36)",
    "json": "JSON",
    "jsonb": "JSON",
    "array": "JSON",
    "serial": "INT AUTO_INCREMENT",
    "bigserial": "BIGINT AUTO_INCREMENT",
}

PRISMA_TYPE_MAP = {
    "string": "String",
    "text": "String",
    "integer": "Int",
    "bigint": "BigInt",
    "float": "Float",
    "decimal": "Decimal",
    "boolean": "Boolean",
    "date": "DateTime",
    "datetime": "DateTime",
    "timestamp": "DateTime",
    "uuid": "String     @default(uuid())",
    "json": "Json",
    "jsonb": "Json",
    "array": "Json",
    "serial": "Int       @default(autoincrement())",
}

MONGOOSE_TYPE_MAP = {
    "string": "String",
    "text": "String",
    "integer": "Number",
    "bigint": "Number",
    "float": "Number",
    "decimal": "Number",
    "boolean": "Boolean",
    "date": "Date",
    "datetime": "Date",
    "timestamp": "Date",
    "uuid": "String",
    "json": "Schema.Types.Mixed",
    "jsonb": "Schema.Types.Mixed",
    "array": "[Schema.Types.Mixed]",
}

DRIZZLE_TYPE_MAP = {
    "string": "varchar('name', { length: 255 })",
    "text": "text('name')",
    "integer": "integer('name')",
    "bigint": "bigint('name', { mode: 'number' })",
    "float": "doublePrecision('name')",
    "decimal": "decimal('name', { precision: 10, scale: 2 })",
    "boolean": "boolean('name')",
    "date": "date('name')",
    "datetime": "timestamp('name')",
    "timestamp": "timestamp('name')",
    "uuid": "uuid('name').defaultRandom()",
    "json": "jsonb('name')",
    "jsonb": "jsonb('name')",
    "serial": "serial('name')",
}


# ─── Helpers ──────────────────────────────────────────────────────────

def _resolve_type(col_type: str, type_map: dict) -> str:
    """Resolve a column type through the type map, with fallback."""
    normalized = col_type.lower().strip()
    return type_map.get(normalized, col_type.upper())


def _get_fk_ref_table(fk: dict) -> str:
    """
    Extract the referenced table name from a foreign key dict.
    Handles multiple key name variants that LLMs might generate:
      referencesTable, references_table, refTable, ref_table, table, target_table
    """
    for key in ("referencesTable", "references_table", "refTable", "ref_table",
                "table", "target_table", "targetTable", "referenced_table"):
        if key in fk:
            return fk[key]
    return fk.get("references", {}).get("table", "unknown_table")


def _get_fk_ref_column(fk: dict) -> str:
    """
    Extract the referenced column name from a foreign key dict.
    Handles multiple key name variants.
    """
    for key in ("referencesColumn", "references_column", "refColumn", "ref_column",
                "column_ref", "targetColumn", "target_column", "referenced_column"):
        if key in fk:
            return fk[key]
    ref = fk.get("references", {})
    if isinstance(ref, dict):
        return ref.get("column", "id")
    return "id"


def _get_fk_column(fk: dict) -> str:
    """Extract the source column name from a foreign key dict."""
    for key in ("column", "source_column", "sourceColumn", "from_column", "fromColumn"):
        if key in fk:
            return fk[key]
    return "unknown_id"


def _safe_col(col: dict, field: str, default=None):
    """Safely get a column field, handling camelCase and snake_case."""
    camel_map = {
        "isPrimary": ["isPrimary", "is_primary", "primary"],
        "isNullable": ["isNullable", "is_nullable", "nullable"],
        "isUnique": ["isUnique", "is_unique", "unique"],
        "defaultValue": ["defaultValue", "default_value", "default"],
    }
    keys = camel_map.get(field, [field])
    for k in keys:
        if k in col:
            return col[k]
    return default


# ─── Compiler: PostgreSQL ─────────────────────────────────────────────

def compile_postgresql(schema: dict) -> str:
    """Generate PostgreSQL DDL from structured schema."""
    output = "-- Generated by Oxtools JSON-to-Schema V2 (Agentic Pipeline)\n"
    output += "-- Format: PostgreSQL\n\n"

    tables = schema.get("tables", [])
    if not tables:
        return output + "-- No tables in schema. The architect may have returned an unexpected format.\n"

    for table in tables:
        name = table.get("name", "unnamed_table")
        output += f"CREATE TABLE {name} (\n"

        col_lines = []
        for col in table.get("columns", []):
            col_name = col.get("name", "unnamed_col")
            pg_type = _resolve_type(col.get("type", "text"), PG_TYPE_MAP)
            line = f"  {col_name} {pg_type}"
            if _safe_col(col, "isPrimary"):
                line += " PRIMARY KEY"
            if not _safe_col(col, "isNullable", True) and not _safe_col(col, "isPrimary"):
                line += " NOT NULL"
            if _safe_col(col, "isUnique"):
                line += " UNIQUE"
            default_val = _safe_col(col, "defaultValue")
            if default_val:
                line += f" DEFAULT {default_val}"
            col_lines.append(line)

        for fk in table.get("foreignKeys", []):
            fk_col = _get_fk_column(fk)
            ref_table = _get_fk_ref_table(fk)
            ref_col = _get_fk_ref_column(fk)
            col_lines.append(
                f"  CONSTRAINT fk_{name}_{fk_col} "
                f"FOREIGN KEY ({fk_col}) "
                f"REFERENCES {ref_table}({ref_col}) "
                f"ON DELETE CASCADE"
            )

        output += ",\n".join(col_lines) + "\n);\n\n"

        # Indexes
        for idx in table.get("indexes", []):
            cols_list = idx.get("columns", [])
            if not cols_list:
                continue
            cols = ", ".join(cols_list)
            unique = "UNIQUE " if idx.get("unique") else ""
            idx_name = f"idx_{name}_{'_'.join(cols_list)}"
            output += f"CREATE {unique}INDEX {idx_name} ON {name} ({cols});\n"

        output += "\n"

    return output


# ─── Compiler: MySQL ──────────────────────────────────────────────────

def compile_mysql(schema: dict) -> str:
    """Generate MySQL DDL from structured schema."""
    output = "-- Generated by Oxtools JSON-to-Schema V2 (Agentic Pipeline)\n"
    output += "-- Format: MySQL\n\n"

    for table in schema.get("tables", []):
        name = table.get("name", "unnamed_table")
        output += f"CREATE TABLE `{name}` (\n"

        col_lines = []
        for col in table.get("columns", []):
            col_name = col.get("name", "unnamed_col")
            mysql_type = _resolve_type(col.get("type", "text"), MYSQL_TYPE_MAP)
            line = f"  `{col_name}` {mysql_type}"
            if _safe_col(col, "isPrimary"):
                line += " PRIMARY KEY"
            if not _safe_col(col, "isNullable", True) and not _safe_col(col, "isPrimary"):
                line += " NOT NULL"
            col_lines.append(line)

        for fk in table.get("foreignKeys", []):
            fk_col = _get_fk_column(fk)
            ref_table = _get_fk_ref_table(fk)
            ref_col = _get_fk_ref_column(fk)
            col_lines.append(
                f"  FOREIGN KEY (`{fk_col}`) "
                f"REFERENCES `{ref_table}`(`{ref_col}`)"
            )

        output += ",\n".join(col_lines) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n"

    return output


# ─── Compiler: Prisma ─────────────────────────────────────────────────

def compile_prisma(schema: dict) -> str:
    """Generate Prisma schema from structured schema."""
    output = "// Generated by Oxtools JSON-to-Schema V2 (Agentic Pipeline)\n"
    output += "// Format: Prisma ORM\n\n"
    output += 'generator client {\n  provider = "prisma-client-js"\n}\n\n'
    output += 'datasource db {\n  provider = "postgresql"\n  url      = env("DATABASE_URL")\n}\n\n'

    for table in schema.get("tables", []):
        raw_name = table.get("name", "unnamed_table")
        model_name = raw_name[0].upper() + raw_name[1:] if raw_name else "Unknown"
        output += f"model {model_name} {{\n"

        for col in table.get("columns", []):
            col_name = col.get("name", "unnamed_col")
            prisma_type = _resolve_type(col.get("type", "text"), PRISMA_TYPE_MAP)
            nullable = "?" if _safe_col(col, "isNullable") and not _safe_col(col, "isPrimary") else ""
            id_attr = "  @id" if _safe_col(col, "isPrimary") else ""
            unique_attr = "  @unique" if _safe_col(col, "isUnique") else ""
            output += f"  {col_name}  {prisma_type}{nullable}{id_attr}{unique_attr}\n"

        # Relations from foreign keys
        for fk in table.get("foreignKeys", []):
            fk_col = _get_fk_column(fk)
            ref_table = _get_fk_ref_table(fk)
            ref_col = _get_fk_ref_column(fk)
            ref_model = ref_table[0].upper() + ref_table[1:] if ref_table else "Unknown"
            rel_name = fk_col.replace("_id", "").replace("Id", "")
            output += f"  {rel_name}  {ref_model}  @relation(fields: [{fk_col}], references: [{ref_col}])\n"

        output += "}\n\n"

    return output


# ─── Compiler: Mongoose ───────────────────────────────────────────────

def compile_mongoose(schema: dict) -> str:
    """Generate Mongoose schema definitions from structured schema."""
    output = "// Generated by Oxtools JSON-to-Schema V2 (Agentic Pipeline)\n"
    output += "// Format: Mongoose (MongoDB)\n\n"
    output += 'const mongoose = require("mongoose");\n'
    output += "const { Schema } = mongoose;\n\n"

    for table in schema.get("tables", []):
        name = table.get("name", "unnamed_table")
        var_name = name[0].lower() + name[1:] if name else "unknown"
        output += f"const {var_name}Schema = new Schema({{\n"

        for col in table.get("columns", []):
            col_name = col.get("name", "unnamed_col")
            if _safe_col(col, "isPrimary") and col_name == "_id":
                continue  # MongoDB handles _id automatically

            mg_type = _resolve_type(col.get("type", "text"), MONGOOSE_TYPE_MAP)
            required = "true" if not _safe_col(col, "isNullable", True) else "false"
            unique = ", unique: true" if _safe_col(col, "isUnique") else ""

            # Check for foreign key reference
            fk_ref = None
            for fk in table.get("foreignKeys", []):
                if _get_fk_column(fk) == col_name:
                    fk_ref = _get_fk_ref_table(fk)
                    break

            if fk_ref:
                ref_model = fk_ref[0].upper() + fk_ref[1:] if fk_ref else "Unknown"
                output += f'  {col_name}: {{ type: Schema.Types.ObjectId, ref: "{ref_model}", required: {required} }},\n'
            else:
                output += f'  {col_name}: {{ type: {mg_type}, required: {required}{unique} }},\n'

        output += "}, { timestamps: true });\n\n"

        model_name = name[0].upper() + name[1:] if name else "Unknown"
        output += f'const {model_name} = mongoose.model("{model_name}", {var_name}Schema);\n'
        output += f"module.exports = {model_name};\n\n"

    return output


# ─── Compiler: Drizzle ORM ────────────────────────────────────────────

def compile_drizzle(schema: dict) -> str:
    """Generate Drizzle ORM schema from structured schema."""
    output = "// Generated by Oxtools JSON-to-Schema V2 (Agentic Pipeline)\n"
    output += "// Format: Drizzle ORM (PostgreSQL)\n\n"
    output += 'import { pgTable, serial, varchar, text, integer, boolean, timestamp, uuid, jsonb, bigint, doublePrecision, decimal, date } from "drizzle-orm/pg-core";\n\n'

    for table in schema.get("tables", []):
        name = table.get("name", "unnamed_table")
        output += f"export const {name} = pgTable('{name}', {{\n"

        for col in table.get("columns", []):
            col_name = col.get("name", "unnamed_col")
            col_type = col.get("type", "text").lower().strip()

            # Map to drizzle column builder
            if _safe_col(col, "isPrimary") and col_type in ("serial", "integer"):
                output += f"  {col_name}: serial('{col_name}').primaryKey(),\n"
            elif col_type == "uuid" and _safe_col(col, "isPrimary"):
                output += f"  {col_name}: uuid('{col_name}').defaultRandom().primaryKey(),\n"
            elif col_type in ("string", "varchar"):
                not_null = ".notNull()" if not _safe_col(col, "isNullable", True) else ""
                output += f"  {col_name}: varchar('{col_name}', {{ length: 255 }}){not_null},\n"
            elif col_type == "text":
                not_null = ".notNull()" if not _safe_col(col, "isNullable", True) else ""
                output += f"  {col_name}: text('{col_name}'){not_null},\n"
            elif col_type in ("integer", "int"):
                not_null = ".notNull()" if not _safe_col(col, "isNullable", True) else ""
                output += f"  {col_name}: integer('{col_name}'){not_null},\n"
            elif col_type == "boolean":
                not_null = ".notNull()" if not _safe_col(col, "isNullable", True) else ""
                output += f"  {col_name}: boolean('{col_name}'){not_null},\n"
            elif col_type in ("datetime", "timestamp"):
                output += f"  {col_name}: timestamp('{col_name}').defaultNow(),\n"
            elif col_type in ("json", "jsonb"):
                output += f"  {col_name}: jsonb('{col_name}'),\n"
            else:
                output += f"  {col_name}: text('{col_name}'),  // unmapped type: {col_type}\n"

        output += "});\n\n"

    return output


# ─── Compiler Dispatcher ─────────────────────────────────────────────

COMPILERS = {
    "postgresql": compile_postgresql,
    "mysql": compile_mysql,
    "prisma": compile_prisma,
    "mongoose": compile_mongoose,
    "drizzle": compile_drizzle,
}

def compile_schema(schema: dict, output_format: str) -> str:
    """
    Dispatch to the appropriate compiler.
    Returns syntactically valid, production-ready output.
    """
    compiler = COMPILERS.get(output_format.lower())
    if not compiler:
        return f"-- Unsupported format: {output_format}. Supported: {', '.join(COMPILERS.keys())}"

    try:
        result = compiler(schema)
        logger.info(f"[Compiler] Generated {output_format} output ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"[Compiler] Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"-- Compilation error: {str(e)}\n-- Please report this bug."
