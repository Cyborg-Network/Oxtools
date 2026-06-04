"use client";

import { useState, useEffect, useCallback } from "react";
import { notFound } from "next/navigation";
import { Crown, ArrowUpRight, X } from "lucide-react";
import { Button } from "@ansospace/ui";

import { ToolLayout } from "@/components/tool-layout";
import { getToolIcon } from "@/lib/icons";
import { getToolById } from "@/lib/tools/registry";
import { useToolExecution } from "@/hooks/use-tool-execution";
import { useAuth } from "@/providers/auth-provider";
import { getPlanDisplayName } from "@/lib/auth";

import type { ParsedSchema, ExecutionMode, ExecutionState } from "./types";
import { SchemaUploader } from "./components/schema-uploader";
import { SchemaPreview } from "./components/schema-preview";
import { QueryBuilder } from "./components/query-builder";
import { ExecutionView } from "./components/execution-view";

const TOOL_ID = "sql-converter";

export default function SqlConverterPage() {
  const tool = getToolById(TOOL_ID);
  if (!tool || tool.status !== "active") notFound();

  // ── Auth / usage (PRESERVED — same logic as generic page) ────────────────
  const { canExecute, getToolUsage, trackExecution, redirectToUpgrade } = useAuth();
  const toolUsage = getToolUsage(TOOL_ID);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  useEffect(() => {
    if (mounted && toolUsage.limitReached) setShowUpgradeDialog(true);
  }, [mounted, toolUsage.limitReached]);

  // ── API endpoint (same pattern as generic page) ──────────────────────────
  const runnerUrl = process.env.NEXT_PUBLIC_TOOL_RUNNER_URL || "http://localhost:9080";
  const apiBase = tool.tier === "tier2" ? `${runnerUrl}/api/tools` : "/api/tools";

  const { result, isLoading, error, execute, reset } = useToolExecution({
    apiEndpoint: `${apiBase}/${TOOL_ID}`,
    toolId: TOOL_ID,
  });

  // ── Custom UI state ───────────────────────────────────────────────────────
  const [schema, setSchema] = useState<ParsedSchema | null>(null);
  const [mode, setMode] = useState<ExecutionMode>("A");
  const [hasSuccessfulGeneration, setHasSuccessfulGeneration] = useState(false);
  const [selectedDialect, setSelectedDialect] = useState("postgresql");

  const [execution, setExecution] = useState<ExecutionState>({
    status: "idle",
    currentStep: 0,
    stepLabel: "",
    resultText: "",
    logs: [],
  });

  // ── Parse streaming text into ExecutionState ──────────────────────────────
  useEffect(() => {
    if (!result && !isLoading) return;

    // Parse logs and step from streaming result text
    const lines = result.split("\n");
    const logs: string[] = [];
    let currentStep = 0;
    let stepLabel = "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed === ".") continue;

      // Detect [N/6] step lines
      const stepMatch = trimmed.match(/^\[(\d+)\/6\]\s*(.+)/);
      if (stepMatch) {
        currentStep = parseInt(stepMatch[1], 10);
        stepLabel = stepMatch[2].trim();
        logs.push(trimmed);
        continue;
      }

      // Skip the RESULT separator in logs
      if (trimmed === "---RESULT---") break;

      logs.push(trimmed);
    }

    const hasResultSeparator = result.includes("---RESULT---");
    const resultParts = result.split("---RESULT---");
    const resultText = resultParts[1] || "";

    if (isLoading) {
      setExecution({
        status: "running",
        currentStep: Math.max(currentStep, 1),
        stepLabel: stepLabel || "Processing…",
        resultText: result,
        logs,
      });
    } else if (error) {
      setExecution((prev) => ({
        ...prev,
        status: "error",
        stepLabel: "Failed",
        resultText: result,
        logs: [...prev.logs, `[ERROR] ${error.message}`],
      }));
    } else if (hasResultSeparator && resultText.trim()) {
      setExecution({
        status: "success",
        currentStep: 6,
        stepLabel: "Complete",
        resultText: result,
        logs,
      });
      if (mode === "A") setHasSuccessfulGeneration(true);
    }
  }, [result, isLoading, error, mode]);

  // ── Execute handlers ──────────────────────────────────────────────────────
  const handleExecuteA = useCallback(
    (query: string, dialect: string) => {
      if (!canExecute(TOOL_ID)) {
        setShowUpgradeDialog(true);
        return;
      }
      setSelectedDialect(dialect);
      setExecution({
        status: "running",
        currentStep: 1,
        stepLabel: "Parsing Schema…",
        resultText: "",
        logs: [`Started: NL→SQL (${dialect.toUpperCase()})`],
      });
      trackExecution(TOOL_ID);
      execute({
        model: tool.defaultModel,
        query,
        dialect,
        schema: schema?.raw ?? "",
      });
    },
    [canExecute, trackExecution, execute, tool.defaultModel, schema]
  );

  const handleExecuteB = useCallback(
    (sandboxQuery: string, dialect: string) => {
      if (!canExecute(TOOL_ID)) {
        setShowUpgradeDialog(true);
        return;
      }
      setExecution({
        status: "running",
        currentStep: 5,
        stepLabel: "Running Sandbox…",
        resultText: "",
        logs: [`Started: Sandbox mode (${dialect.toUpperCase()})`],
      });
      trackExecution(TOOL_ID);
      execute({
        model: tool.defaultModel,
        mode: "sandbox",
        sandboxQuery,
        dialect,
        schema: schema?.raw ?? "",
      });
    },
    [canExecute, trackExecution, execute, tool.defaultModel, schema]
  );

  const handleResetSchema = useCallback(() => {
    if (!window.confirm("Load a different schema? This will reset the current session.")) return;
    setSchema(null);
    setMode("A");
    setHasSuccessfulGeneration(false);
    setExecution({ status: "idle", currentStep: 0, stepLabel: "", resultText: "", logs: [] });
    reset();
  }, [reset]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      <ToolLayout
        title={tool.name}
        description={tool.description}
        icon={getToolIcon(tool.icon, "h-6 w-6")}
        onRestore={(body) => {
          // Restore schema from history if available
          const raw = (body.schema as string) || "";
          if (raw) {
            import("./lib/parser").then(({ parseDDL }) => {
              const parsed = parseDDL(raw);
              if (parsed.tableCount > 0) setSchema(parsed);
            });
          }
        }}
      >
        <div className="space-y-8 max-w-5xl mx-auto pb-20">
          {/* ── STEP 1: Schema ── */}
          <section>
            {!schema ? (
              <SchemaUploader onSchemaLoaded={setSchema} />
            ) : (
              <SchemaPreview schema={schema} onReset={handleResetSchema} />
            )}
          </section>

          {/* ── STEP 2: Mode + Query (only when schema loaded) ── */}
          {schema && (
            <section>
              {/* Usage pill — PRESERVED from generic page */}
              <div className="flex items-center justify-end mb-3">
                <div
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                    !mounted
                      ? "bg-primary/10 text-primary"
                      : toolUsage.limitReached
                      ? "bg-destructive/10 text-destructive"
                      : toolUsage.remaining <= 2
                      ? "bg-amber-500/10 text-amber-500"
                      : "bg-primary/10 text-primary"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      !mounted
                        ? "bg-primary"
                        : toolUsage.limitReached
                        ? "bg-destructive"
                        : toolUsage.remaining <= 2
                        ? "bg-amber-500"
                        : "bg-primary"
                    }`}
                  />
                  {mounted ? toolUsage.used : 0}/{toolUsage.limit} uses today
                  <span className="ml-1 rounded-md bg-muted px-1.5 py-0.5 text-[9px] font-semibold uppercase">
                    {mounted ? toolUsage.plan : "free"}
                  </span>
                </div>
              </div>

              {toolUsage.limitReached && mounted ? (
                <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
                  Daily limit reached.{" "}
                  <button
                    onClick={redirectToUpgrade}
                    className="underline underline-offset-2 font-medium"
                  >
                    Upgrade for more <ArrowUpRight className="inline w-3 h-3" />
                  </button>
                </div>
              ) : (
                <QueryBuilder
                  mode={mode}
                  setMode={setMode}
                  hasSuccessfulGeneration={hasSuccessfulGeneration}
                  selectedDialect={selectedDialect}
                  onExecuteA={handleExecuteA}
                  onExecuteB={handleExecuteB}
                  isLoading={isLoading}
                />
              )}
            </section>
          )}

          {/* ── STEP 3: Execution results ── */}
          {execution.status !== "idle" && (
            <section>
              <ExecutionView
                execution={execution}
                isLoading={isLoading}
                error={error}
              />
            </section>
          )}
        </div>
      </ToolLayout>

      {/* ── Upgrade dialog — PRESERVED from generic page ── */}
      {showUpgradeDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative mx-4 w-full max-w-md rounded-2xl border border-border/50 bg-card p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <button
              onClick={() => setShowUpgradeDialog(false)}
              className="absolute right-4 top-4 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20">
              <Crown className="h-7 w-7 text-amber-500" />
            </div>
            <h3 className="text-center text-lg font-semibold">Daily Limit Reached</h3>
            <p className="mt-1 text-center text-sm text-muted-foreground">
              You've used all <strong>{toolUsage.limit}</strong> executions for{" "}
              <strong>Natural Language to SQL</strong> today on the{" "}
              <span className="font-medium text-foreground">
                {getPlanDisplayName(toolUsage.plan)}
              </span>{" "}
              plan.
            </p>
            <div className="mt-5 space-y-2 rounded-xl bg-muted/50 p-4 text-sm">
              {[
                { plan: "free", label: "Free", count: "5 / tool / day" },
                { plan: "pro", label: "Pro", count: "20 / tool / day" },
                { plan: "premium", label: "Premium", count: "100 / tool / day" },
              ].map(({ plan, label, count }) => (
                <div key={plan} className="flex items-center justify-between">
                  <span className="text-muted-foreground">{label}</span>
                  <span className={toolUsage.plan === plan ? "font-bold text-foreground" : "text-primary"}>
                    {count} {toolUsage.plan === plan && "(current)"}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-5 flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setShowUpgradeDialog(false)}>
                Maybe Later
              </Button>
              <Button
                className="flex-1 gap-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600"
                onClick={redirectToUpgrade}
              >
                Upgrade Now
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}