"use client";

import { Button, Card, CardContent, Spinner } from "@ansospace/ui";
import {
	AlertCircle,
	Check,
	Copy,
	ExternalLink,
	Key,
	Lock,
	ShieldAlert,
	Sparkles,
	Timer,
} from "lucide-react";
import mermaid from "mermaid";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ColorPaletteViewer } from "./color-palette-viewer";

mermaid.initialize({
	startOnLoad: false,
	theme: "dark",
});

function MermaidViewer({ chart }: { chart: string }) {
	const containerRef = useRef<HTMLDivElement>(null);
	const [svg, setSvg] = useState<string>("");
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		let isMounted = true;
		(async () => {
			try {
				const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
				const { svg: generatedSvg } = await mermaid.render(id, chart);
				if (isMounted) setSvg(generatedSvg);
				setError(null);
			} catch (err: unknown) {
				if (isMounted)
					setError(err instanceof Error ? err.message : "Error rendering Mermaid chart");
			}
		})();
		return () => {
			isMounted = false;
		};
	}, [chart]);

	if (error) {
		return (
			<div className="my-4 rounded-md border border-destructive/20 bg-destructive/10 p-4 text-xs font-mono text-destructive overflow-auto">
				<strong>Mermaid Syntax Error:</strong>
				<br />
				{error}
			</div>
		);
	}

	// biome-ignore lint/security/noDangerouslySetInnerHtml: Mermaid returns trusted SVG markup for display
	return (
		<div
			ref={containerRef}
			className="mermaid-wrapper my-6 flex items-center justify-center overflow-auto rounded-lg border border-border bg-zinc-950 dark:bg-zinc-900 p-6"
			dangerouslySetInnerHTML={{ __html: svg }}
		/>
	);
}

import type { ToolError } from "@/hooks/use-tool-execution";

interface ResultViewerProps {
	result: string;
	isLoading?: boolean;
	error?: ToolError | string | null;
	streaming?: boolean;
	onOpenSettings?: () => void;
}

const ERROR_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
	model_access_denied: {
		icon: <Lock className="h-5 w-5" />,
		label: "Model Access Denied",
		color: "text-amber-600 dark:text-amber-400",
	},
	rate_limit_exceeded: {
		icon: <Timer className="h-5 w-5" />,
		label: "Rate Limit Exceeded",
		color: "text-amber-600 dark:text-amber-400",
	},
	unauthorized: {
		icon: <ShieldAlert className="h-5 w-5" />,
		label: "Unauthorized",
		color: "text-red-600 dark:text-red-400",
	},
	insufficient_quota: {
		icon: <AlertCircle className="h-5 w-5" />,
		label: "Quota Exhausted",
		color: "text-red-600 dark:text-red-400",
	},
	service_unavailable: {
		icon: <AlertCircle className="h-5 w-5" />,
		label: "Service Unavailable",
		color: "text-orange-600 dark:text-orange-400",
	},
};

function ErrorDisplay({
	error,
	onOpenSettings,
}: {
	error: ToolError;
	onOpenSettings?: () => void;
}) {
	const config = ERROR_CONFIG[error.code || ""] || {
		icon: <AlertCircle className="h-5 w-5" />,
		label: "Error",
		color: "text-destructive",
	};

	const isKeyRelated =
		error.code === "model_access_denied" ||
		error.code === "rate_limit_exceeded" ||
		error.code === "unauthorized" ||
		error.code === "insufficient_quota";

	return (
		<Card className="border-destructive/30 bg-destructive/5">
			<CardContent className="py-5">
				<div className="flex items-start gap-3">
					<div className={`mt-0.5 shrink-0 ${config.color}`}>{config.icon}</div>
					<div className="min-w-0 flex-1 space-y-3">
						{/* Error header */}
						<div>
							<div className="flex items-center gap-2">
								<span className={`text-sm font-semibold ${config.color}`}>{config.label}</span>
								{error.code && (
									<span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
										{error.code}
									</span>
								)}
							</div>
							<p className="mt-1 text-sm text-foreground/90">{error.message}</p>
						</div>

						{/* Action hint */}
						{error.action && (
							<div className="rounded-md border border-border/60 bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground">
								<span className="font-medium text-foreground">💡 What to do: </span>
								{error.action}
							</div>
						)}

						{/* Action buttons */}
						{isKeyRelated && (
							<div className="flex flex-wrap gap-2">
								<Button
									variant="outline"
									size="sm"
									onClick={() => {
										if (onOpenSettings) {
											onOpenSettings();
										} else {
											window.dispatchEvent(new CustomEvent("open-settings"));
										}
									}}
									className="h-8 gap-1.5 text-xs"
								>
									<Key className="h-3.5 w-3.5" />
									Add API Key
								</Button>
								<a href="https://portal.oxlo.ai/signup" target="_blank" rel="noopener noreferrer">
									<Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
										Get Free Key
										<ExternalLink className="h-3 w-3" />
									</Button>
								</a>
							</div>
						)}
					</div>
				</div>
			</CardContent>
		</Card>
	);
}

function CopyButton({ text }: { text: string }) {
	const handleCopy = useCallback(async () => {
		await navigator.clipboard.writeText(text);
		const btn = document.activeElement as HTMLButtonElement;
		if (btn) {
			btn.dataset.copied = "true";
			setTimeout(() => {
				btn.dataset.copied = "false";
			}, 2000);
		}
	}, [text]);

	return (
		<button
			type="button"
			onClick={handleCopy}
			className="absolute top-2 right-2 rounded-md bg-muted/80 p-1.5 text-muted-foreground opacity-0 backdrop-blur-sm transition-all hover:bg-muted hover:text-foreground group-hover/code:opacity-100 data-[copied=true]:text-green-500"
			data-copied="false"
		>
			<Copy className="h-3.5 w-3.5 data-[copied=true]:hidden" />
			<Check className="hidden h-3.5 w-3.5 data-[copied=true]:block" />
		</button>
	);
}

export function ResultViewer({
	result,
	isLoading,
	error,
	streaming,
	onOpenSettings,
}: ResultViewerProps) {
	const [copiedAll, setCopiedAll] = useState(false);
	const [copiedExtracted, setCopiedExtracted] = useState(false);
	const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");

	type StructuredResult = {
		code?: string;
		palette?: Record<string, string>;
		roles?: Record<string, string>;
		image?: string;
		extractedColors?: string[];
		[key: string]: unknown;
	};

	const handleCopyAll = useCallback(async () => {
		await navigator.clipboard.writeText(result);
		setCopiedAll(true);
		setTimeout(() => setCopiedAll(false), 2000);
	}, [result]);

	const handleCopyExtractedAll = useCallback(async (colors: string[]) => {
		await navigator.clipboard.writeText(colors.join("\n"));
		setCopiedExtracted(true);
		setTimeout(() => setCopiedExtracted(false), 2000);
	}, []);

	if (error) {
		// Normalize string errors to ToolError shape
		const toolError: ToolError = typeof error === "string" ? { message: error } : error;
		return <ErrorDisplay error={toolError} onOpenSettings={onOpenSettings} />;
	}

	if (isLoading && !result) {
		return (
			<Card className="border-primary/20 bg-primary/[0.02]">
				<CardContent className="flex items-center justify-center py-12">
					<div className="flex flex-col items-center gap-3">
						<div className="relative">
							<Spinner className="h-6 w-6 text-primary" />
							<Sparkles className="absolute -top-1 -right-1 h-3 w-3 animate-pulse text-primary" />
						</div>
						<span className="text-sm font-medium text-muted-foreground">AI is thinking...</span>
					</div>
				</CardContent>
			</Card>
		);
	}

	if (!result) {
		return (
			<Card className="border-dashed">
				<CardContent className="py-12 text-center">
					<div className="flex flex-col items-center gap-2">
						<div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
							<Sparkles className="h-5 w-5 text-muted-foreground" />
						</div>
						<p className="text-sm text-muted-foreground">Results will appear here</p>
					</div>
				</CardContent>
			</Card>
		);
	}

	let parsedJson: StructuredResult | null = null;
	let displayMarkdown = "";
	let pipelineLogs = "";
	let isReportStarted = false;
	let extractedColorsPreview: string[] = [];

	let outputContent = result;

	const extractStructuredBlock = (text: string, startMarker: string, endMarker?: string) => {
		const startIndex = text.indexOf(startMarker);
		if (startIndex === -1) return null;

		const startContentIndex = startIndex + startMarker.length;
		if (endMarker) {
			const endIndex = text.indexOf(endMarker, startContentIndex);
			return text.slice(startContentIndex, endIndex === -1 ? undefined : endIndex).trim();
		}

		return text.slice(startContentIndex).trim();
	};

	const extractBalancedJson = (text: string) => {
		const startIndex = text.indexOf("{");
		if (startIndex === -1) return null;

		let depth = 0;
		let inString = false;
		let escaped = false;

		for (let index = startIndex; index < text.length; index += 1) {
			const character = text[index];

			if (escaped) {
				escaped = false;
				continue;
			}

			if (character === "\\") {
				escaped = true;
				continue;
			}

			if (character === '"') {
				inString = !inString;
				continue;
			}

			if (inString) continue;

			if (character === "{") depth += 1;
			if (character === "}") {
				depth -= 1;
				if (depth === 0) {
					return text.slice(startIndex, index + 1);
				}
			}
		}

		return null;
	};

	if (result) {
		// Check for output markers (both old and new format)
		if (result.includes("---OUTPUT_START---")) {
			const structuredBlock = extractStructuredBlock(
				result,
				"---OUTPUT_START---",
				"---OUTPUT_END---"
			);
			if (structuredBlock) {
				outputContent = structuredBlock;
			} else {
				const parts = result.split("---OUTPUT_START---");
				pipelineLogs = parts[0].trim();
				outputContent = parts[1] || "";
			}
			isReportStarted = true;
		} else if (result.includes("---REPORT_START---")) {
			const parts = result.split("---REPORT_START---");
			pipelineLogs = parts[0].trim();
			outputContent = parts[1] || "";
			isReportStarted = true;
		} else if (streaming && isLoading) {
			// If we haven't hit the output marker yet, everything is logs.
			pipelineLogs = result.trim();
			outputContent = "";
		}
	}

	// Extract early KMeans colors from logs (arrives before OUTPUT_START)
	const extractedSource = pipelineLogs || result || "";
	if (extractedSource.includes("---EXTRACTED_COLORS_START---")) {
		try {
			// Prefer regex so we survive streaming chunk boundaries / extra whitespace.
			const match = extractedSource.match(
				/---EXTRACTED_COLORS_START---\s*([\s\S]*?)\s*---EXTRACTED_COLORS_END---/m
			);
			if (match?.[1]) {
				const parsed = JSON.parse(match[1].trim());
				if (Array.isArray(parsed?.extractedColors)) extractedColorsPreview = parsed.extractedColors;
			}
		} catch {
			// ignore - preview is optional
		}
	}

	// Hide the extracted-colors JSON block from the logs viewer (UI already shows swatches)
	const pipelineLogsDisplay = pipelineLogs
		? pipelineLogs.replace(
				/---EXTRACTED_COLORS_START---[\s\S]*?---EXTRACTED_COLORS_END---\s*/gm,
				""
			)
		: pipelineLogs;

	if (outputContent) {
		try {
			const trimmed = outputContent.trim();
			const jsonCandidate =
				trimmed.startsWith("{") && trimmed.endsWith("}") ? trimmed : extractBalancedJson(trimmed);
			if (jsonCandidate) {
				const parsed = JSON.parse(jsonCandidate) as StructuredResult;
				// Check for color palette JSON
				if (
					parsed.palette &&
					typeof parsed.palette === "object" &&
					parsed.roles &&
					typeof parsed.roles === "object"
				) {
					parsedJson = parsed;
					displayMarkdown = ""; // Don't show markdown for palettes
				} else if (typeof parsed.code === "string") {
					parsedJson = parsed;
					displayMarkdown = `\`\`\`html\n${parsed.code}\n\`\`\``;
				}
			}
		} catch (_e) {
			// Ignore parsing errors - fall back to markdown rendering
			displayMarkdown = outputContent;
		}

		// Fallback: Check if the result embeds a standalone HTML block in markdown
		if (!parsedJson) {
			const htmlBlockRegex = /```(?:html)?\s*(<!DOCTYPE html>[\s\S]*?<html[\s\S]*?)```/i;
			const match = outputContent.trim().match(htmlBlockRegex);
			if (match?.[1]) {
				parsedJson = { code: match[1] };
			} else if (
				outputContent.trim().startsWith("<!DOCTYPE html>") ||
				outputContent.trim().startsWith("<html")
			) {
				parsedJson = { code: outputContent.trim() };
			} else {
				// Not HTML or JSON, treat as markdown
				displayMarkdown = outputContent;
			}
		}
	}

	const hasHtmlCode = !!(
		parsedJson?.code &&
		(parsedJson.code.includes("<!DOCTYPE html>") || parsedJson.code.includes("<html"))
	);

	return (
		<div className="space-y-6">
			{/* Early extracted-colors preview (shows before final palette) */}
			{extractedColorsPreview.length > 0 && (
				<Card className="border-border/50 overflow-hidden">
					<CardContent className="p-0">
						<div className="flex items-center justify-between gap-3 border-b border-border/40 bg-muted/20 px-5 py-4">
							<div className="min-w-0">
								<div className="flex items-center gap-2">
									<h4 className="text-base font-semibold">Extracted Colors</h4>
									<span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
										{extractedColorsPreview.length}
									</span>
								</div>
								<p className="mt-0.5 text-xs text-muted-foreground">
									{isLoading ? "Showing fast extraction while refining palette…" : "Ready"}
								</p>
							</div>

							<div className="flex shrink-0 items-center gap-2">
								<Button
									variant="outline"
									size="sm"
									onClick={() => handleCopyExtractedAll(extractedColorsPreview)}
									className="h-8 text-xs"
								>
									{copiedExtracted ? (
										<Check className="h-3.5 w-3.5 mr-1" />
									) : (
										<Copy className="h-3.5 w-3.5 mr-1" />
									)}
									Copy all
								</Button>
							</div>
						</div>

						<div className="px-5 py-5">
							<div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
								{extractedColorsPreview.map((color) => (
									<button
										key={color}
										type="button"
										className="group text-left"
										onClick={() => navigator.clipboard.writeText(color)}
										title="Click to copy"
									>
										<div
											className="w-full aspect-square rounded-xl border-2 border-border/50 shadow-sm transition-all group-hover:shadow-md group-hover:border-primary"
											style={{ backgroundColor: color }}
										/>
										<div className="mt-2">
											<code className="block truncate rounded bg-muted px-2 py-1 text-[11px] font-mono text-muted-foreground group-hover:text-foreground">
												{color}
											</code>
										</div>
									</button>
								))}
							</div>
						</div>
					</CardContent>
				</Card>
			)}

			{/* Pipeline Logs Viewer */}
			{pipelineLogsDisplay && (
				<Card className="border-primary/20 bg-primary/[0.02] overflow-hidden">
					<CardContent className="p-0">
						<div className="flex items-center gap-3 border-b border-border/40 bg-muted/30 px-4 py-3">
							<div className="relative">
								{isLoading && !isReportStarted ? (
									<Spinner className="h-4 w-4 text-primary" />
								) : (
									<Check className="h-4 w-4 text-green-500" />
								)}
								{isLoading && !isReportStarted && (
									<Sparkles className="absolute -top-1 -right-1 h-2 w-2 animate-pulse text-primary" />
								)}
							</div>
							<span className="text-sm font-medium text-muted-foreground">
								{isLoading && !isReportStarted ? "Agent Pipeline Running..." : "Pipeline Complete"}
							</span>
						</div>
						<div className="max-h-[300px] overflow-y-auto bg-zinc-950 p-4 font-mono text-[13px] leading-relaxed text-zinc-300 dark:bg-zinc-950/50">
							{pipelineLogsDisplay.split("\n").map((line, i) => {
								if (!line.trim() || line === ".") return null;
								let textColor = "text-zinc-400";
								if (line.startsWith("[")) {
									textColor = "text-primary font-semibold";
								} else if (line.startsWith(">")) {
									textColor = "text-zinc-300 ml-4 border-l-2 border-primary/30 pl-2";
								} else if (
									line.toLowerCase().includes("error") ||
									line.toLowerCase().includes("failed")
								) {
									textColor = "text-red-400";
								}
								return (
									<div key={`${line}-${textColor}`} className={`py-0.5 ${textColor}`}>
										{line}
									</div>
								);
							})}
							{isLoading && !isReportStarted && (
								<div className="mt-2 flex items-center gap-1.5 text-primary/70">
									<span
										className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70"
										style={{ animationDelay: "0ms" }}
									/>
									<span
										className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70"
										style={{ animationDelay: "150ms" }}
									/>
									<span
										className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70"
										style={{ animationDelay: "300ms" }}
									/>
								</div>
							)}
						</div>
					</CardContent>
				</Card>
			)}

			{/* If result contains an image or extracted colors but no full palette,
			    render an interactive preview so the uploaded image can be inspected locally. */}
			{(() => {
				let previewData: StructuredResult | null = null;
				try {
					const candidate = (
						outputContent ? JSON.parse(outputContent.trim()) : null
					) as StructuredResult | null;
					if (candidate && (candidate.image || Array.isArray(candidate.extractedColors))) {
						previewData = candidate;
					}
				} catch {
					// ignore parse errors
				}

				if (previewData) {
					return (
						<Card className="overflow-hidden relative">
							<CardContent className="pt-6 pb-6 relative">
								<ColorPaletteViewer data={previewData} enableHover={true} />
							</CardContent>
						</Card>
					);
				}

				// Fallback to the regular palette viewer when full palette + roles exist
				if (parsedJson?.palette && parsedJson?.roles) {
					return (
						<Card className="overflow-hidden relative">
							<div
								className="absolute top-3 right-3 flex items-center gap-2 z-10"
								style={{ opacity: 1 }}
							>
								<Button
									variant="outline"
									size="sm"
									onClick={handleCopyAll}
									className="h-8 text-xs bg-background/80 backdrop-blur-sm"
								>
									{copiedAll ? (
										<Check className="h-3.5 w-3.5 mr-1" />
									) : (
										<Copy className="h-3.5 w-3.5 mr-1" />
									)}
									Copy
								</Button>
							</div>
							<CardContent className="pt-10 pb-6 relative">
								<ColorPaletteViewer data={parsedJson} enableHover={true} />
							</CardContent>
						</Card>
					);
				}
				return null;
			})()}

			{/* Final Report Viewer - Shows when palette/roles DON'T exist */}
			{(isReportStarted || displayMarkdown) && !(parsedJson?.palette && parsedJson?.roles) && (
				<Card className="overflow-hidden relative">
					<div
						className="absolute top-3 right-3 flex items-center gap-2 z-10"
						style={{ opacity: 1 }}
					>
						<Button
							variant="outline"
							size="sm"
							onClick={handleCopyAll}
							className="h-8 text-xs bg-background/80 backdrop-blur-sm"
						>
							{copiedAll ? (
								<Check className="h-3.5 w-3.5 mr-1" />
							) : (
								<Copy className="h-3.5 w-3.5 mr-1" />
							)}
							Copy
						</Button>
					</div>

					{hasHtmlCode && (
						<div className="flex border-b border-border/50 px-4 pt-3 bg-muted/20">
							<button
								type="button"
								onClick={() => setActiveTab("preview")}
								className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
									activeTab === "preview"
										? "border-primary text-foreground"
										: "border-transparent text-muted-foreground hover:text-foreground"
								}`}
							>
								Preview
							</button>
							<button
								type="button"
								onClick={() => setActiveTab("code")}
								className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
									activeTab === "code"
										? "border-primary text-foreground"
										: "border-transparent text-muted-foreground hover:text-foreground"
								}`}
							>
								Code
							</button>
						</div>
					)}

					<CardContent className="pt-10 pb-6 relative">
						{/* HTML Preview / Markdown */}
						<article
							className={[
								"prose prose-sm dark:prose-invert max-w-none",
								"prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-foreground",
								"prose-h1:text-xl prose-h1:mt-6 prose-h1:mb-4",
								"prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3 prose-h2:border-b prose-h2:border-border prose-h2:pb-2",
								"prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2",
								"prose-p:text-foreground/90 prose-p:leading-7 prose-p:my-3",
								"prose-strong:text-foreground prose-strong:font-semibold",
								"prose-em:text-foreground/80",
								"prose-a:text-primary prose-a:underline prose-a:underline-offset-4 prose-a:decoration-primary/40 hover:prose-a:decoration-primary",
								"prose-li:text-foreground/90 prose-li:my-1 prose-li:leading-7",
								"prose-ul:my-3 prose-ul:pl-6 prose-ol:my-3 prose-ol:pl-6",
								"prose-code:rounded-md prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[13px] prose-code:font-mono prose-code:font-medium",
								"prose-code:before:content-none prose-code:after:content-none",
								"prose-pre:rounded-lg prose-pre:border prose-pre:border-border prose-pre:bg-zinc-950 dark:prose-pre:bg-zinc-900",
								"prose-pre:px-4 prose-pre:py-4 prose-pre:my-4",
								"prose-blockquote:border-l-primary/50 prose-blockquote:bg-muted/30 prose-blockquote:rounded-r-lg prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:my-4",
								"prose-blockquote:text-foreground/80 prose-blockquote:not-italic",
								"prose-th:text-foreground prose-th:font-semibold prose-th:text-left prose-th:px-3 prose-th:py-2",
								"prose-td:text-foreground/90 prose-td:px-3 prose-td:py-2",
								"prose-table:my-4",
								"prose-hr:border-border prose-hr:my-6",
								"prose-img:rounded-lg prose-img:my-4",
							].join(" ")}
						>
							{activeTab === "preview" && hasHtmlCode ? (
								<div className="w-full h-[600px] rounded-lg border border-border bg-white overflow-hidden -mt-4 relative z-0">
									<iframe
										title="Preview"
										srcDoc={parsedJson?.code}
										className="w-full h-full border-0 absolute inset-0 bg-white"
										sandbox="allow-scripts"
									/>
								</div>
							) : (
								<>
									<ReactMarkdown
										remarkPlugins={[remarkGfm]}
										components={{
											pre({ children, ...props }) {
												let codeText = "";
												try {
													const child = children as unknown as { props?: { children?: unknown } };
													codeText = child?.props?.children
														? String(child.props.children)
														: String(children || "");
												} catch {
													codeText = String(children || "");
												}
												return (
													<div className="group/code relative my-4">
														<CopyButton text={codeText} />
														<pre
															className="overflow-x-auto rounded-lg border border-border bg-zinc-950 px-4 py-4 text-sm leading-relaxed text-zinc-100 dark:bg-zinc-900"
															{...props}
														>
															{children}
														</pre>
													</div>
												);
											},
											code({ className, children, ...props }) {
												const isInline = !className;
												if (isInline) {
													return (
														<code
															className="rounded-md bg-muted px-1.5 py-0.5 text-[13px] font-mono font-medium text-foreground"
															{...props}
														>
															{children}
														</code>
													);
												}
												const isMermaid = className?.includes("language-mermaid");
												if (isMermaid) {
													return <MermaidViewer chart={String(children)} />;
												}
												return (
													<code
														className={`${className || ""} text-sm leading-relaxed text-zinc-100`}
														{...props}
													>
														{children}
													</code>
												);
											},
											table({ children, ...props }) {
												return (
													<div className="my-4 overflow-x-auto rounded-lg border border-border">
														<table className="w-full text-sm" {...props}>
															{children}
														</table>
													</div>
												);
											},
											thead({ children, ...props }) {
												return (
													<thead className="border-b border-border bg-muted/50" {...props}>
														{children}
													</thead>
												);
											},
											th({ children, ...props }) {
												return (
													<th
														className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-foreground"
														{...props}
													>
														{children}
													</th>
												);
											},
											td({ children, ...props }) {
												return (
													<td
														className="border-t border-border px-4 py-2.5 text-foreground/90"
														{...props}
													>
														{children}
													</td>
												);
											},
											blockquote({ children, ...props }) {
												return (
													<blockquote
														className="my-4 rounded-r-lg border-l-4 border-l-primary/50 bg-muted/30 py-2 px-4 text-foreground/80 [&>p]:my-1"
														{...props}
													>
														{children}
													</blockquote>
												);
											},
											ul({ children, ...props }) {
												return (
													<ul className="my-3 list-disc space-y-1.5 pl-6" {...props}>
														{children}
													</ul>
												);
											},
											ol({ children, ...props }) {
												return (
													<ol className="my-3 list-decimal space-y-1.5 pl-6" {...props}>
														{children}
													</ol>
												);
											},
											li({ children, ...props }) {
												return (
													<li className="leading-7 text-foreground/90" {...props}>
														{children}
													</li>
												);
											},
											h1({ children, ...props }) {
												return (
													<h1
														className="mt-6 mb-4 text-xl font-semibold tracking-tight text-foreground"
														{...props}
													>
														{children}
													</h1>
												);
											},
											h2({ children, ...props }) {
												return (
													<h2
														className="mt-6 mb-3 border-b border-border pb-2 text-lg font-semibold tracking-tight text-foreground"
														{...props}
													>
														{children}
													</h2>
												);
											},
											h3({ children, ...props }) {
												return (
													<h3
														className="mt-5 mb-2 text-base font-semibold tracking-tight text-foreground"
														{...props}
													>
														{children}
													</h3>
												);
											},
											p({ children, ...props }) {
												return (
													<p className="my-3 leading-7 text-foreground/90" {...props}>
														{children}
													</p>
												);
											},
											hr() {
												return <hr className="my-6 border-border" />;
											},
											a({ children, href, ...props }) {
												return (
													<a
														href={href}
														className="text-primary underline underline-offset-4 decoration-primary/40 hover:decoration-primary"
														target="_blank"
														rel="noopener noreferrer"
														{...props}
													>
														{children}
													</a>
												);
											},
										}}
									>
										{displayMarkdown}
									</ReactMarkdown>
									{streaming && isLoading && (
										<span className="mt-1 inline-block h-5 w-1.5 animate-pulse rounded-sm bg-primary" />
									)}
									{parsedJson &&
										Object.keys(parsedJson).filter((k) => k !== "code").length > 0 &&
										activeTab === "code" && (
											<div className="mt-8 pt-4 border-t border-border">
												<h4
													className="text-sm font-semibold mb-3 text-foreground"
													style={{ fontFamily: "var(--font-unbounded), sans-serif" }}
												>
													Additional Context
												</h4>
												<pre className="mt-3 bg-muted p-3 rounded-md overflow-x-auto text-xs text-muted-foreground whitespace-pre-wrap">
													{JSON.stringify(
														Object.fromEntries(
															Object.entries(parsedJson).filter(([k]) => k !== "code")
														),
														null,
														2
													)}
												</pre>
											</div>
										)}
								</>
							)}
						</article>
					</CardContent>
				</Card>
			)}
		</div>
	);
}
