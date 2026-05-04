"use client";
import { Button, Label, Textarea } from "@ansospace/ui";
import { ArrowUpRight, Crown, Lock, Play, X } from "lucide-react";
import { notFound, useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CodeEditor } from "@/components/code-editor";
import { ResultViewer } from "@/components/result-viewer";
import { ToolLayout } from "@/components/tool-layout";
import { useToolExecution } from "@/hooks/use-tool-execution";
import { getPlanDisplayName } from "@/lib/auth";
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

	// Tier2 tools MUST bypass Next.js proxy buffering to prevent silent timeouts on long executions
	const runnerUrl = process.env.NEXT_PUBLIC_TOOL_RUNNER_URL || "http://localhost:9080";
	const apiBase = tool.tier === "tier2" ? `${runnerUrl}/api/tools` : "/api/tools";
	const { result, isLoading, error, execute, setResult } = useToolExecution({
		apiEndpoint: `${apiBase}/${tool.id}`,
		toolId: tool.id,
		...(tool.timeoutMs && { timeoutMs: tool.timeoutMs }),
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

	// ── HYDRATION FIX ──────────────────────────────────────────────────────────
	// getToolUsage reads from localStorage/cookies which don't exist on the server.
	// We defer the real value until after mount so SSR and client agree on the
	// initial render (both see the zero/default state), then the effect below
	// runs on the client and updates to the real value.
	const [mounted, setMounted] = useState(false);
	useEffect(() => setMounted(true), []);

	// Always call the hook (Rules of Hooks) — but only use its value post-mount.
	const rawToolUsage = getToolUsage(tool.id);
	const toolUsage = mounted
		? rawToolUsage
		: {
				// Issue 8: use optional chaining + safe defaults to prevent SSR TypeError
				// when getToolUsage returns undefined or an incomplete object before hydration.
				used: 0,
				limit: rawToolUsage?.limit ?? 0,
				remaining: rawToolUsage?.limit ?? 0,
				limitReached: false,
				plan: rawToolUsage?.plan ?? "free",
			};
	// ── END HYDRATION FIX ──────────────────────────────────────────────────────

	const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);

	// Show popup when limit is newly reached
	useEffect(() => {
		if (mounted && toolUsage.limitReached) {
			setShowUpgradeDialog(true);
		}
	}, [mounted, toolUsage.limitReached]);

	const handleExecute = () => {
		// Check per-tool usage limit
		if (!canExecute(tool.id)) {
			setShowUpgradeDialog(true);
			return;
		}
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

	const uploadedImageSrc = useMemo(() => {
		const imageKey = tool.inputs.find((i) => i.type === "image")?.key;
		return imageKey ? fields[imageKey] : undefined;
	}, [tool.inputs, fields]);

	return (
		<>
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
						{mounted && toolUsage.limitReached ? (
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
						{/* Deferred until after mount to prevent hydration mismatch from localStorage */}
						<div className="flex items-center gap-2">
							<div
								suppressHydrationWarning
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
									suppressHydrationWarning
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
							</div>
							<span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
								{mounted ? toolUsage.plan : "free"}
							</span>
						</div>
					</div>

					{/* Low usage warning */}
					{mounted &&
						!toolUsage.limitReached &&
						toolUsage.remaining <= 2 &&
						toolUsage.remaining > 0 && (
							<p className="text-xs text-amber-500">
								⚡ {toolUsage.remaining} use{toolUsage.remaining === 1 ? "" : "s"} remaining for
								this tool today.{" "}
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
						{/* Issue 19: derive the image src from whichever input has type==='image',
					    instead of hardcoding fields['image']. */}
						<ResultViewer
							result={result}
							isLoading={isLoading}
							error={error}
							streaming
							uploadedImageSrc={uploadedImageSrc}
						/>
					</div>
				</div>
			</ToolLayout>

			{/* ─── Upgrade Dialog Popup ──────────────────────────── */}
			{showUpgradeDialog && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
					<div className="relative mx-4 w-full max-w-md rounded-2xl border border-border/50 bg-card p-6 shadow-2xl animate-in zoom-in-95 duration-200">
						{/* Close button */}
						<button
							onClick={() => setShowUpgradeDialog(false)}
							className="absolute right-4 top-4 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
						>
							<X className="h-4 w-4" />
						</button>

						{/* Icon */}
						<div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20">
							<Crown className="h-7 w-7 text-amber-500" />
						</div>

						{/* Title */}
						<h3 className="text-center text-lg font-semibold">Daily Limit Reached</h3>
						<p className="mt-1 text-center text-sm text-muted-foreground">
							You&apos;ve used all <strong>{toolUsage.limit}</strong> executions for{" "}
							<strong>{tool.name}</strong> today on the{" "}
							<span className="font-medium text-foreground">
								{getPlanDisplayName(toolUsage.plan)}
							</span>{" "}
							plan.
						</p>

						{/* Tier comparison */}
						<div className="mt-5 space-y-2 rounded-xl bg-muted/50 p-4 text-sm">
							<div className="flex items-center justify-between">
								<span className="text-muted-foreground">Free</span>
								<span className={toolUsage.plan === "free" ? "font-bold text-foreground" : ""}>
									5 / tool / day {toolUsage.plan === "free" && "(current)"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-muted-foreground">Pro</span>
								<span
									className={
										toolUsage.plan === "pro" ? "font-bold text-foreground" : "text-primary"
									}
								>
									20 / tool / day {toolUsage.plan === "pro" && "(current)"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-muted-foreground">Premium</span>
								<span
									className={
										toolUsage.plan === "premium" ? "font-bold text-foreground" : "text-primary"
									}
								>
									100 / tool / day {toolUsage.plan === "premium" && "(current)"}
								</span>
							</div>
						</div>

						{/* CTA */}
						<div className="mt-5 flex gap-3">
							<Button
								variant="outline"
								className="flex-1"
								onClick={() => setShowUpgradeDialog(false)}
							>
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

		case "files":
			return (
				<div className="space-y-2">
					<Label>{config.label}</Label>
					<div className="space-y-3">
						<input
							type="file"
							accept={
								config.accept ||
								".py,.js,.ts,.go,.java,.c,.cpp,.rb,.php,.rs,.zip,.txt,.json,.yml,.yaml,.toml,.cfg,.ini,.env"
							}
							multiple
							onChange={async (e) => {
								const files = e.target.files;
								if (!files || files.length === 0) return;

								const maxFiles = config.maxFiles || 50;
								const maxSizeMb = config.maxSizeMb || 10;
								const maxSizeBytes = maxSizeMb * 1024 * 1024;

								// Check file count
								if (files.length > maxFiles) {
									alert(`Maximum ${maxFiles} files allowed. You selected ${files.length}.`);
									return;
								}

								// Check total size
								let totalSize = 0;
								for (const f of Array.from(files)) totalSize += f.size;
								if (totalSize > maxSizeBytes) {
									alert(`Total upload size exceeds ${maxSizeMb}MB limit.`);
									return;
								}

								// Handle ZIP files
								if (files.length === 1 && files[0].name.endsWith(".zip")) {
									const reader = new FileReader();
									reader.onloadend = () => {
										// Send as base64 with a zip: prefix so backend knows
										const base64 = (reader.result as string).split(",")[1];
										onChange(`__ZIP__:${base64}`);
									};
									reader.readAsDataURL(files[0]);
									return;
								}

								// Read all files as text and concatenate with markers
								const parts: string[] = [];
								for (const file of Array.from(files)) {
									try {
										const text = await file.text();
										const rawPath = file.webkitRelativePath || file.name;
										const cleanPath = rawPath.includes("/")
											? rawPath.split("/").slice(1).join("/") || rawPath
											: rawPath;
										parts.push(`--- FILE: ${cleanPath} ---\n${text}`);
									} catch {
										const rp = file.webkitRelativePath || file.name;
										const cp = rp.includes("/") ? rp.split("/").slice(1).join("/") || rp : rp;
										parts.push(`--- FILE: ${cp} ---\n[Binary file — skipped]`);
									}
								}
								onChange(parts.join("\n\n"));
							}}
							className="flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium hover:file:cursor-pointer hover:file:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						/>
						{/* Folder picker for directory uploads */}
						<div className="flex items-center gap-2">
							<span className="text-xs text-muted-foreground">or</span>
							<label className="cursor-pointer rounded-md border border-dashed border-input/60 bg-muted/20 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-colors">
								📁 Select Folder
								<input
									type="file"
									{...({
										webkitdirectory: "",
										directory: "",
									} as React.InputHTMLAttributes<HTMLInputElement>)}
									className="hidden"
									onChange={async (e) => {
										const files = e.target.files;
										if (!files || files.length === 0) return;
										const exts = new Set(
											".py,.js,.ts,.go,.java,.c,.cpp,.rb,.php,.rs,.txt,.json,.yml,.yaml,.toml,.cfg,.ini,.env,.lock".split(
												","
											)
										);
										const valid = Array.from(files).filter((f) => {
											const ext = "." + f.name.split(".").pop()?.toLowerCase();
											const p = f.webkitRelativePath || f.name;
											if (
												p.includes("__pycache__") ||
												p.includes("node_modules") ||
												p.includes(".git/")
											)
												return false;
											if (f.name.startsWith(".")) return false;
											return exts.has(ext);
										});
										if (valid.length === 0) {
											alert("No supported files found.");
											return;
										}
										if (valid.length > 50) {
											alert("Too many files (max 50).");
											return;
										}
										const parts: string[] = [];
										for (const file of valid) {
											try {
												const text = await file.text();
												const rp = file.webkitRelativePath || file.name;
												const cp = rp.includes("/") ? rp.split("/").slice(1).join("/") || rp : rp;
												parts.push(`--- FILE: ${cp} ---\n${text}`);
											} catch {
												/* skip binary */
											}
										}
										onChange(parts.join("\n\n"));
									}}
								/>
							</label>
						</div>
						{value && (
							<div className="rounded-md border border-input/50 bg-muted/30 p-3">
								<p className="text-xs text-muted-foreground">
									{value.startsWith("__ZIP__:")
										? "📦 ZIP archive loaded — will be extracted server-side"
										: `📄 ${(value.match(/--- FILE:/g) || []).length} file(s) loaded`}
								</p>
							</div>
						)}
						{config.helperText && (
							<p className="text-xs text-muted-foreground">{config.helperText}</p>
						)}
					</div>
				</div>
			);

		default:
			return null;
	}
}
