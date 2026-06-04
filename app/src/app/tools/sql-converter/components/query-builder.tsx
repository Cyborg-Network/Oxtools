"use client";

import { useState } from "react";
import { Sparkles, TerminalSquare, Lock } from "lucide-react";
import { CodeEditor } from "@/components/code-editor";
import type { ExecutionMode } from "../types";

interface QueryBuilderProps {
  mode: ExecutionMode;
  setMode: (mode: ExecutionMode) => void;
  hasSuccessfulGeneration: boolean;
  selectedDialect: string;
  onExecuteA: (query: string, dialect: string) => void;
  onExecuteB: (sandboxQuery: string, dialect: string) => void;
  isLoading: boolean;
}

const DIALECTS = [
  { value: "postgresql", label: "PostgreSQL" },
  { value: "mysql", label: "MySQL" },
  { value: "sqlite", label: "SQLite" },
  { value: "mssql", label: "SQL Server" },
  { value: "bigquery", label: "BigQuery" },
];

export function QueryBuilder({
  mode,
  setMode,
  hasSuccessfulGeneration,
  selectedDialect,
  onExecuteA,
  onExecuteB,
  isLoading,
}: QueryBuilderProps) {
  const [nlQuery, setNlQuery] = useState("");
  const [dialect, setDialect] = useState(selectedDialect || "postgresql");
  const [sandboxQuery, setSandboxQuery] = useState("");

  return (
    <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-base font-bold tracking-tight text-foreground">
          Select execution mode
        </h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Generate SQL from natural language, or test a query directly in the sandbox.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ── MODE A ── */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setMode("A")}
          onKeyDown={(e) => e.key === "Enter" && setMode("A")}
          className={`rounded-2xl border-2 p-5 transition-all duration-200 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
            mode === "A"
              ? "border-primary bg-primary/5 shadow-sm"
              : "border-border bg-card hover:border-primary/40"
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <div
              className={`p-2 rounded-lg ${
                mode === "A"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-bold">Natural Language → SQL</p>
              <p className="text-xs text-muted-foreground">Mode A · Active by default</p>
            </div>
          </div>

          {mode === "A" && (
            <div
              className="space-y-3 mt-4 animate-in fade-in duration-200"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="space-y-1">
                <label className="text-xs font-semibold text-foreground/80">
                  Describe your query
                </label>
                <textarea
                  value={nlQuery}
                  onChange={(e) => setNlQuery(e.target.value)}
                  placeholder="List all active members who joined this year, ordered by join date..."
                  className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none h-20"
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-foreground/80">SQL Dialect</label>
                <select
                  value={dialect}
                  onChange={(e) => setDialect(e.target.value)}
                  disabled={isLoading}
                  className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
                >
                  {DIALECTS.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => onExecuteA(nlQuery, dialect)}
                disabled={!nlQuery.trim() || isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-semibold shadow hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                <Sparkles className="w-4 h-4" />
                {isLoading ? "Generating…" : "Generate SQL & Test"}
              </button>
            </div>
          )}
        </div>

        {/* ── MODE B ── */}
        <div
          role="button"
          tabIndex={hasSuccessfulGeneration ? 0 : -1}
          onClick={() => hasSuccessfulGeneration && setMode("B")}
          onKeyDown={(e) => e.key === "Enter" && hasSuccessfulGeneration && setMode("B")}
          className={`relative rounded-2xl border-2 p-5 transition-all duration-200 outline-none ${
            !hasSuccessfulGeneration
              ? "opacity-50 cursor-not-allowed border-border/40 bg-muted/10"
              : mode === "B"
              ? "border-amber-500 bg-amber-500/5 shadow-sm cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500/30"
              : "border-border bg-card hover:border-amber-400/50 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500/30"
          }`}
        >
          {!hasSuccessfulGeneration && (
            <div className="absolute top-4 right-4 p-1.5 bg-muted/80 rounded-full">
              <Lock className="w-3.5 h-3.5 text-muted-foreground" />
            </div>
          )}

          <div className="flex items-center gap-3 mb-3">
            <div
              className={`p-2 rounded-lg ${
                mode === "B" && hasSuccessfulGeneration
                  ? "bg-amber-500 text-white"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              <TerminalSquare className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-bold">Test SQL in Sandbox</p>
              <p className="text-xs text-muted-foreground">
                Mode B · {hasSuccessfulGeneration ? "Unlocked" : "Requires one successful generation"}
              </p>
            </div>
          </div>

          {!hasSuccessfulGeneration && (
            <p className="text-xs text-muted-foreground">
              Run Mode A successfully first to unlock direct sandbox testing.
            </p>
          )}

          {hasSuccessfulGeneration && mode === "B" && (
            <div
              className="space-y-3 mt-4 animate-in fade-in duration-200"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Safety notice */}
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-700 dark:text-amber-400 text-xs flex gap-2 items-start">
                <span className="shrink-0 text-base leading-none">⚠️</span>
                <p>
                  Runs against <strong>synthetic mock data</strong> generated from your schema.
                  Your real database is never accessed.
                </p>
              </div>

              <div className="rounded-xl border border-input overflow-hidden focus-within:ring-2 focus-within:ring-amber-500/20">
                <CodeEditor
                  value={sandboxQuery}
                  onChange={setSandboxQuery}
                  placeholder={"SELECT * FROM members WHERE membership_status = 'Active';"}
                  rows={7}
                />
              </div>

              {/* Dialect reminder */}
              <p className="text-[10px] text-muted-foreground">
                Dialect: <strong>{DIALECTS.find((d) => d.value === dialect)?.label ?? dialect.toUpperCase()}</strong>
                {" "}(same as Mode A)
              </p>

              <button
                onClick={() => onExecuteB(sandboxQuery, dialect)}
                disabled={!sandboxQuery.trim() || isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-amber-500 text-white rounded-xl text-sm font-semibold shadow hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                <TerminalSquare className="w-4 h-4" />
                {isLoading ? "Executing…" : "Execute in Sandbox"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}