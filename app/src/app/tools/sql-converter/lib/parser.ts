import type { ParsedSchema, TableDef, ColumnDef } from "../types";

/**
 * Lightweight client-side DDL parser for schema preview.
 * Does NOT need to be perfect — just enough to show tables/columns.
 * The backend (schema_parser.py with sqlglot) is the authoritative parser.
 */
export function parseDDL(ddl: string): ParsedSchema {
  const tables: TableDef[] = [];

  // Strip comments before parsing
  const cleaned = ddl
    .replace(/--[^\n]*/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "");

  // Match CREATE TABLE blocks
  const tableRegex =
    /CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"']?(\w+)[`"']?\s*\(([\s\S]*?)\)\s*(?:ENGINE|DEFAULT|AUTO|;|$)/gi;

  let match: RegExpExecArray | null;
  while ((match = tableRegex.exec(cleaned)) !== null) {
    const tableName = match[1];
    const body = match[2];

    const columns: ColumnDef[] = [];

    // Split on commas that are NOT inside parentheses
    const lines = splitColumnDefs(body);

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const upper = trimmed.toUpperCase();

      // Skip table-level constraints
      if (
        upper.startsWith("PRIMARY KEY") ||
        upper.startsWith("FOREIGN KEY") ||
        upper.startsWith("CONSTRAINT") ||
        upper.startsWith("UNIQUE") ||
        upper.startsWith("INDEX") ||
        upper.startsWith("KEY ") ||
        upper.startsWith("CHECK")
      ) {
        continue;
      }

      // Extract column name (first token, strip quotes/backticks)
      const nameMatch = trimmed.match(/^[`"']?(\w+)[`"']?\s+(.+)/);
      if (!nameMatch) continue;

      const colName = nameMatch[1];
      const rest = nameMatch[2];

      // Extract type — take up to first space or first keyword
      const typeMatch = rest.match(
        /^(\w+(?:\s*\([^)]+\))?(?:\s+UNSIGNED)?(?:\s+ZEROFILL)?)/i
      );
      const colType = typeMatch ? typeMatch[1].trim() : rest.split(/\s+/)[0];

      columns.push({
        name: colName,
        type: colType,
        isPrimary: /PRIMARY\s+KEY/i.test(rest),
        isForeign: /REFERENCES/i.test(rest),
        isNotNull: /NOT\s+NULL/i.test(rest),
      });
    }

    if (columns.length > 0 || tableName) {
      tables.push({ name: tableName, columns });
    }
  }

  return { raw: ddl, tables, tableCount: tables.length };
}

function splitColumnDefs(body: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = "";

  for (const char of body) {
    if (char === "(") depth++;
    else if (char === ")") depth--;
    else if (char === "," && depth === 0) {
      parts.push(current);
      current = "";
      continue;
    }
    current += char;
  }
  if (current.trim()) parts.push(current);
  return parts;
}