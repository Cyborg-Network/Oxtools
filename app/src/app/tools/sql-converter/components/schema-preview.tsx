"use client";

import { Check, Database, Key, RefreshCw } from "lucide-react";
import type { ParsedSchema } from "../types";

interface SchemaPreviewProps {
  schema: ParsedSchema;
  onReset: () => void;
}

export function SchemaPreview({ schema, onReset }: SchemaPreviewProps) {
  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-400">
      {/* Header row */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 rounded-full text-emerald-500 shrink-0">
            <Check className="w-4 h-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Schema loaded</p>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Database className="w-3 h-3" />
              {schema.tableCount} {schema.tableCount === 1 ? "table" : "tables"} detected
            </p>
          </div>
        </div>
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors underline underline-offset-4"
        >
          <RefreshCw className="w-3 h-3" />
          Load different schema
        </button>
      </div>

      {/* Table grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[38vh] overflow-y-auto pr-1">
        {schema.tables.map((table) => (
          <div
            key={table.name}
            className="rounded-xl border border-border/50 bg-card overflow-hidden shadow-sm hover:shadow-md transition-shadow"
          >
            {/* Table header */}
            <div className="bg-muted/50 px-3 py-2.5 border-b border-border/40 flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-primary shrink-0" />
              <span className="text-sm font-semibold truncate" title={table.name}>
                {table.name}
              </span>
              <span className="ml-auto text-[10px] text-muted-foreground font-mono shrink-0">
                {table.columns.length} col{table.columns.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Columns list */}
            <ul className="divide-y divide-border/20">
              {table.columns.slice(0, 8).map((col, j) => (
                <li
                  key={col.name + j}
                  className="px-3 py-1.5 flex items-center justify-between gap-2 text-xs hover:bg-muted/20 transition-colors"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    {col.isPrimary ? (
                      <Key className="w-3 h-3 shrink-0 text-amber-500" aria-label="Primary Key" />
                    ) : col.isForeign ? (
                      <Key className="w-3 h-3 shrink-0 text-blue-400" aria-label="Foreign Key" />
                    ) : (
                      <span className="w-3 h-3 shrink-0" />
                    )}
                    <span className="font-medium text-foreground truncate">{col.name}</span>
                    {col.isNotNull && (
                      <span className="text-[9px] text-destructive/70 font-mono shrink-0">NN</span>
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono uppercase shrink-0 max-w-[80px] truncate">
                    {col.type}
                  </span>
                </li>
              ))}
              {table.columns.length > 8 && (
                <li className="px-3 py-1.5 text-xs text-muted-foreground italic">
                  +{table.columns.length - 8} more columns…
                </li>
              )}
              {table.columns.length === 0 && (
                <li className="px-3 py-2 text-xs text-muted-foreground italic text-center">
                  No columns parsed
                </li>
              )}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}