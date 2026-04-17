"use client";

import { Button, Label, Textarea } from "@ansospace/ui";
import { ArrowUpRight, Lock, Play } from "lucide-react";
import { notFound, useParams } from "next/navigation";
import { useCallback, useState } from "react";

import { CodeEditor } from "@/components/code-editor";
import { ResultViewer } from "@/components/result-viewer";
import { ToolLayout } from "@/components/tool-layout";
import { useToolExecution } from "@/hooks/use-tool-execution";
import { getToolIcon } from "@/lib/icons";
import { getToolById } from "@/lib/tools/registry";
import { useAuth } from "@/providers/auth-provider";
import type { InputFieldConfig } from "@/types";

/**
 * Dynamic tool page - renders any tool from the registry.
 *
 * Contributors only need to create a ToolDefinition file in
 * src/lib/tools/<tool-id>.ts - this page handles the rest.
 */
export default function DynamicToolPage() {
	const params = useParams<{ toolId: string }>();
	const tool = getToolById(params.toolId);

	if (!tool || tool.status !== "active") {
		notFound();
	}

	return <ToolPageContent toolId={tool.id} />;
}

function ToolPageContent({ toolId }: { toolId: string }) {
	const tool = getToolById(toolId)!;
	// Model is hardcoded per tool - no user selection
	const model = tool.defaultModel || "llama-3.3-70b";
	const [fields, setFields] = useState<Record<string, string>>(() => {
		const initial: Record<string, string> = {};
		for (const input of tool.inputs) {
			initial[input.key] =
				input.type === "select" && input.options?.length ? input.options[0].value : "";
		}
		return initial;
	});

	const { result, isLoading, error, execute, setResult } = useToolExecution({
		apiEndpoint: `/api/tools/${tool.id}`,
		toolId: tool.id,
	});

	const setField = useCallback((key: string, value: string) => {
		setFields((prev) => ({ ...prev, [key]: value }));
	}, []);

	const handleRestore = useCallback(
		(body: Record<string, unknown>, restoredResult: string) => {
			const restored: Record<string, string> = {};
			for (const input of tool.inputs) {
				restored[input.key] = (body[input.key] as string) || "";
			}
			setFields(restored);
			setResult(restoredResult);
		},
		[tool, setResult]
	);

	const { canExecute, getToolUsage, trackExecution, redirectToUpgrade } = useAuth();
	const toolUsage = getToolUsage(tool.id);

	const handleExecute = () => {
		// Check per-tool usage limit
		if (!canExecute(tool.id)) return;
		// Check required fields
		for (const field of tool.requiredFields) {
			if (!fields[field]?.trim()) return;
		}
		execute({ ...fields, model });
		// Track usage for THIS tool
		trackExecution(tool.id);
	};

	// Check if all required fields are filled
	const isReady = tool.requiredFields.every((field) => fields[field]?.trim());

	return (
		<ToolLayout
			title={tool.name}
			description={tool.description}
			icon={getToolIcon(tool.icon, "h-6 w-6")}
			onRestore={handleRestore}
		>
			<div className="space-y-6">
				{/* Render input fields from tool definition */}
				{tool.inputs.map((input) => (
					<InputField
						key={input.key}
						config={input}
						value={fields[input.key] || ""}
						onChange={(value) => setField(input.key, value)}
					/>
				))}

				{/* Execute button + Usage counter */}
				<div className="flex items-center gap-4 flex-wrap">
					{toolUsage.limitReached ? (
						<div className="space-y-2">
							<Button
								onClick={redirectToUpgrade}
								variant="outline"
								className="gap-2 border-destructive/30 text-destructive hover:bg-destructive/10"
							>
								<Lock className="h-4 w-4" />
								Limit reached for this tool ({toolUsage.used}/{toolUsage.limit})
							</Button>
							<p className="text-xs text-muted-foreground">
								Upgrade your plan for more daily executions.{" "}
								<button
									onClick={redirectToUpgrade}
									className="text-primary hover:underline underline-offset-2"
								>
									View plans <ArrowUpRight className="inline h-3 w-3" />
								</button>
							</p>
						</div>
					) : (
						<Button onClick={handleExecute} disabled={!isReady || isLoading} className="gap-2">
							<Play className="h-4 w-4" />
							{isLoading ? "Processing..." : `Run ${tool.name}`}
						</Button>
					)}

					{/* Usage indicator pill - per tool */}
					<div className="flex items-center gap-2">
						<div
							className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
								toolUsage.limitReached
									? "bg-destructive/10 text-destructive"
									: toolUsage.remaining <= 2
										? "bg-amber-500/10 text-amber-500"
										: "bg-primary/10 text-primary"
							}`}
						>
							<span
								className={`h-1.5 w-1.5 rounded-full ${
									toolUsage.limitReached
										? "bg-destructive"
										: toolUsage.remaining <= 2
											? "bg-amber-500"
											: "bg-primary"
								}`}
							/>
							{toolUsage.used}/{toolUsage.limit} uses today
						</div>
						<span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
							{toolUsage.plan}
						</span>
					</div>
				</div>

				{/* Low usage warning */}
				{!toolUsage.limitReached && toolUsage.remaining <= 2 && toolUsage.remaining > 0 && (
					<p className="text-xs text-amber-500">
						⚡ {toolUsage.remaining} use{toolUsage.remaining === 1 ? "" : "s"} remaining for this
						tool today.{" "}
						<button
							onClick={redirectToUpgrade}
							className="underline underline-offset-2 hover:text-amber-400"
						>
							Upgrade for more
						</button>
					</p>
				)}

				{/* Results */}
				<div className="space-y-2">
					<Label>Result</Label>
					<ResultViewer result={result} isLoading={isLoading} error={error} streaming />
				</div>
			</div>
		</ToolLayout>
	);
}

// ---------------------------------------------------------------------------
// Generic input renderer - renders any InputFieldConfig
// ---------------------------------------------------------------------------

function InputField({
	config,
	value,
	onChange,
}: {
	config: InputFieldConfig;
	value: string;
	onChange: (value: string) => void;
}) {
	switch (config.type) {
		case "code":
			return (
				<div className="space-y-2">
					<Label>{config.label}</Label>
					<CodeEditor
						value={value}
						onChange={onChange}
						placeholder={config.placeholder}
						rows={config.rows || 8}
					/>
				</div>
			);

		case "textarea":
			return (
				<div className="space-y-2">
					<Label>{config.label}</Label>
					<Textarea
						value={value}
						onChange={(e) => onChange(e.target.value)}
						placeholder={config.placeholder}
						rows={config.rows || 4}
						className="resize-none"
					/>
				</div>
			);

		case "select":
			return (
				<div className="space-y-2">
					<Label>{config.label}</Label>
					<div className="max-w-xs">
						<select
							value={value}
							onChange={(e) => onChange(e.target.value)}
							className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							{config.options?.map((opt) => (
								<option key={opt.value} value={opt.value}>
									{opt.label}
								</option>
							))}
						</select>
					</div>
				</div>
			);

		case "text":
			return (
				<div className="space-y-2">
					<Label>{config.label}</Label>
					<input
						type="text"
						value={value}
						onChange={(e) => onChange(e.target.value)}
						placeholder={config.placeholder}
						className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					/>
				</div>
			);

		case "image":
			return (
				<div className="space-y-2">
					<Label>{config.label}</Label>
					<div className="flex items-center gap-4 p-1">
						<input
							type="file"
							accept="image/*"
							onChange={(e) => {
								const file = e.target.files?.[0];
								if (!file) return;
								const reader = new FileReader();
								reader.onloadend = () => {
									onChange(reader.result as string); // base64 string
								};
								reader.readAsDataURL(file);
							}}
							className="flex h-10 w-full max-w-sm rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium hover:file:cursor-pointer hover:file:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						/>
						{value && (
							<div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-md border">
								<img src={value} alt="Preview" className="h-full w-full object-cover" />
							</div>
						)}
					</div>
				</div>
			);

		default:
			return null;
	}
}
