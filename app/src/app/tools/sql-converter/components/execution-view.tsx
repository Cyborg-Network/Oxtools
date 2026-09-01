"use client";

import {
	CheckCircle2,
	ChevronDown,
	ChevronRight,
	Database,
	Loader2,
	Sparkles,
	Table as TableIcon,
	Terminal,
	XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ResultViewer } from "@/components/result-viewer";
import { parseGenerationOutput, parseSandboxOutput } from "../lib/result-parser";
import type { ExecutionMode, ExecutionState } from "../types";

interface ExecutionViewProps {
	execution: ExecutionState;
	mode: ExecutionMode;
	isLoading: boolean;
	error: { message: string } | null;
}

const GENERATE_STEP_LABELS = [
	"Parsing Schema",
	"Classifying Intent",
	"Generating SQL",
	"Validating SQL",
	"Refining / Mock Data",
	"Running Sandbox",
];

const SANDBOX_STEP_LABELS = ["Parsing Schema", "Generating Synthetic Data", "Running Sandbox"];

export function ExecutionView({ execution, mode, isLoading, error }: ExecutionViewProps) {
	const [activeTab, setActiveTab] = useState<"results" | "mock">("results");
	const [logsOpen, setLogsOpen] = useState(true);
	const logsRef = useRef<HTMLDivElement>(null);

	const stepLabels = mode === "B" ? SANDBOX_STEP_LABELS : GENERATE_STEP_LABELS;
	const stepCount = stepLabels.length;

	useEffect(() => {
		if (logsRef.current) {
			logsRef.current.scrollTop = logsRef.current.scrollHeight;
		}
	}, []);

	useEffect(() => {
		if (execution.status === "running") setLogsOpen(true);
	}, [execution.status]);

	useEffect(() => {
		setActiveTab("results");
	}, []);

	if (execution.status === "idle") return null;

	const resultParts = execution.resultText.split("---RESULT---");
	const postResult = resultParts[1] || "";

	const generationMarkdown = parseGenerationOutput(postResult);
	const { sandboxMarkdown, mockPreviewMarkdown } = parseSandboxOutput(postResult);

	const hasGeneration = generationMarkdown.length > 0;
	const hasSandbox = sandboxMarkdown.length > 0;
	const hasMockPreview = mockPreviewMarkdown.length > 0;

	const progressPct =
		execution.status === "success" ? 100 : Math.max(5, (execution.currentStep / stepCount) * 100);

	const pipelineTitle = mode === "A" ? "SQL Generation" : "Sandbox Execution";

	return (
		<div className="space-y-1 animate-in fade-in slide-in-from-bottom-4 duration-500">
			<div className="rounded-2xl border border-border/50 bg-card overflow-hidden shadow-sm">
				{/* Progress header */}
				<div className="p-5 border-b border-border/40 bg-muted/20 space-y-3">
					<div className="flex items-center justify-between text-sm">
						<span className="font-semibold text-foreground flex items-center gap-2">
							{execution.status === "running" && (
								<Loader2 className="w-4 h-4 animate-spin text-primary" />
							)}
							{execution.status === "success" && (
								<CheckCircle2 className="w-4 h-4 text-emerald-500" />
							)}
							{execution.status === "error" && <XCircle className="w-4 h-4 text-destructive" />}
							{execution.stepLabel || pipelineTitle}
						</span>
						<span className="font-mono text-xs text-muted-foreground">
							{execution.currentStep}/{stepCount}
						</span>
					</div>

					<div className="h-1.5 bg-muted rounded-full overflow-hidden">
						<div
							className={`h-full rounded-full transition-all duration-700 ease-out ${
								execution.status === "error"
									? "bg-destructive"
									: execution.status === "success"
										? "bg-emerald-500"
										: "bg-primary animate-pulse"
							}`}
							style={{ width: `${progressPct}%` }}
						/>
					</div>

					<div className="flex items-center gap-1">
						{stepLabels.map((label, i) => {
							const stepNum = i + 1;
							const done = stepNum < execution.currentStep || execution.status === "success";
							const active = stepNum === execution.currentStep && execution.status === "running";
							return (
								<div
									key={label}
									title={label}
									className={`flex-1 h-1 rounded-full transition-colors duration-300 ${
										done ? "bg-emerald-500" : active ? "bg-primary" : "bg-muted"
									}`}
								/>
							);
						})}
					</div>
				</div>

				{/* Collapsible logs */}
				<div className="border-b border-border/40">
					<button
						type="button"
						onClick={() => setLogsOpen((o) => !o)}
						className="w-full flex items-center justify-between px-5 py-3 hover:bg-muted/30 transition-colors text-sm"
					>
						<span className="flex items-center gap-2 font-medium text-muted-foreground">
							<Terminal className="w-4 h-4" />
							Agent Logs
							{execution.logs.length > 0 && (
								<span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-mono">
									{execution.logs.length}
								</span>
							)}
						</span>
						{logsOpen ? (
							<ChevronDown className="w-4 h-4 text-muted-foreground" />
						) : (
							<ChevronRight className="w-4 h-4 text-muted-foreground" />
						)}
					</button>

					{logsOpen && (
						<div
							ref={logsRef}
							className="bg-zinc-950 text-zinc-300 px-5 py-3 text-xs font-mono max-h-44 overflow-y-auto"
						>
							{execution.logs.length === 0 ? (
								<span className="text-zinc-600">Waiting for logs…</span>
							) : (
								<ul className="space-y-0.5">
									{execution.logs.map((line, i) => {
										const lineKey = `log-${i}-${line.substring(0, 15).replace(/\s/g, "-")}`;
										let color = "text-zinc-400";
										if (line.startsWith("[") && /\[\d+\/\d+\]/.test(line))
											color = "text-primary font-semibold";
										else if (
											line.toLowerCase().includes("[error]") ||
											line.toLowerCase().includes("failed")
										)
											color = "text-red-400";
										else if (line.toLowerCase().includes("[warn]")) color = "text-amber-400";
										else if (line.startsWith("  ->") || line.startsWith("->"))
											color = "text-emerald-400 pl-3";
										return (
											<li key={lineKey} className={`py-0.5 ${color}`}>
												{line}
											</li>
										);
									})}
									{isLoading && (
										<li className="py-1 flex gap-1 text-primary/50">
											<span className="animate-bounce" style={{ animationDelay: "0ms" }}>
												·
											</span>
											<span className="animate-bounce" style={{ animationDelay: "150ms" }}>
												·
											</span>
											<span className="animate-bounce" style={{ animationDelay: "300ms" }}>
												·
											</span>
										</li>
									)}
								</ul>
							)}
						</div>
					)}
				</div>

				{/* ── Mode A: generation result only ── */}
				{mode === "A" && (hasGeneration || error) && (
					<div className="p-5">
						<div className="flex items-center gap-2 mb-4 text-sm font-semibold text-foreground">
							<Sparkles className="w-4 h-4 text-primary" />
							Generated SQL
						</div>
						<ResultViewer
							result={generationMarkdown}
							isLoading={isLoading && !hasGeneration}
							error={error}
							streaming={isLoading}
						/>
					</div>
				)}

				{/* ── Mode B: sandbox result + mock preview tabs ── */}
				{mode === "B" && (hasSandbox || hasMockPreview || error) && (
					<>
						<div className="flex border-b border-border/40 bg-muted/10">
							<TabBtn
								active={activeTab === "results"}
								onClick={() => setActiveTab("results")}
								icon={<TableIcon className="w-3.5 h-3.5" />}
								label="SQL Sandbox Result"
							/>
							<TabBtn
								active={activeTab === "mock"}
								onClick={() => setActiveTab("mock")}
								icon={<Database className="w-3.5 h-3.5" />}
								label="Mock Preview"
								disabled={!hasMockPreview}
							/>
						</div>

						<div className="p-5">
							{activeTab === "results" && (
								<ResultViewer
									result={hasSandbox ? sandboxMarkdown : ""}
									isLoading={isLoading && !hasSandbox}
									error={error}
									streaming={isLoading}
								/>
							)}

							{activeTab === "mock" && hasMockPreview && (
								<ResultViewer
									result={mockPreviewMarkdown}
									isLoading={false}
									error={null}
									streaming={false}
								/>
							)}

							{activeTab === "mock" && !hasMockPreview && (
								<div className="flex flex-col items-center justify-center h-40 text-center text-muted-foreground border-2 border-dashed border-border/40 rounded-xl">
									<Database className="w-8 h-8 mb-2 opacity-30" />
									<p className="text-sm font-medium">Mock data not yet available</p>
									<p className="text-xs mt-1">
										Synthetic table previews appear here after sandbox execution.
									</p>
								</div>
							)}
						</div>
					</>
				)}
			</div>
		</div>
	);
}

function TabBtn({
	active,
	onClick,
	icon,
	label,
	disabled,
}: {
	active: boolean;
	onClick: () => void;
	icon: React.ReactNode;
	label: string;
	disabled?: boolean;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			disabled={disabled}
			className={`flex-1 py-3 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors border-b-2 ${
				active
					? "border-primary text-primary bg-background"
					: disabled
						? "border-transparent text-muted-foreground/40 cursor-not-allowed"
						: "border-transparent text-muted-foreground hover:bg-muted/30"
			}`}
		>
			{icon}
			{label}
		</button>
	);
}
