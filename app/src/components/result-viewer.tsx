"use client";

import { Button, Card, CardContent, Spinner } from "@ansospace/ui";
import {
	AlertCircle,
	Check,
	Copy,
	Download,
	ExternalLink,
	Key,
	Lock,
	Maximize2,
	Minimize2,
	ShieldAlert,
	Sparkles,
	Timer,
	Upload,
} from "lucide-react";
import mermaid from "mermaid";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
			} catch (err: any) {
				if (isMounted) setError(err.message || "Error rendering Mermaid chart");
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
	uploadedImageSrc?: string;
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

function CopyButton({ text, className }: { text: string; className?: string }) {
	const [copied, setCopied] = useState(false);

	const handleCopy = useCallback(async () => {
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch {
			// clipboard access denied — silently fail
		}
	}, [text]);

	return (
		<button
			type="button"
			onClick={handleCopy}
			className={className || "absolute top-2 right-2 rounded-md bg-muted/80 p-1.5 text-muted-foreground opacity-0 backdrop-blur-sm transition-all hover:bg-muted hover:text-foreground group-hover/code:opacity-100"}
		>
			{copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
		</button>
	);
}

function PipelineStepsBar({ meta, isLoading }: { meta: Record<string, string>; isLoading?: boolean }) {
	return null; // replace with real steps bar later
}

function SideBySideComparison({
	uploadedSrc,
	generatedCode,
	isFullscreen,
}: {
	uploadedSrc: string;
	generatedCode: string;
	isFullscreen: boolean;
}) {
	const height = isFullscreen ? 'h-full' : 'h-[580px]';
	return (
		<div className={`grid grid-cols-2 gap-0 overflow-hidden rounded-lg border border-border ${height}`}>
			{/* Original screenshot panel */}
			<div className="relative flex flex-col overflow-hidden border-r border-border">
				<div className="flex shrink-0 items-center gap-2 border-b border-border bg-muted/40 px-3 py-1.5">
					<span className="h-2 w-2 rounded-full bg-blue-500" />
					<span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Original</span>
				</div>
				<div className="flex flex-1 items-center justify-center overflow-auto bg-[#0d0d0d]">
					<img src={uploadedSrc} alt="Original screenshot" className="max-h-full max-w-full object-contain" />
				</div>
			</div>
			{/* Generated code panel */}
			<div className="relative flex flex-col overflow-hidden">
				<div className="flex shrink-0 items-center gap-2 border-b border-border bg-muted/40 px-3 py-1.5">
					<span className="h-2 w-2 rounded-full bg-green-500" />
					<span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Generated</span>
				</div>
				<iframe
					srcDoc={generatedCode}
					className="flex-1 border-0"
					sandbox="allow-scripts allow-same-origin"
					title="Generated output"
				/>
			</div>
		</div>
	);
}

export function ResultViewer({
	result,
	isLoading,
	error,
	streaming,
	onOpenSettings,
	uploadedImageSrc,
}: ResultViewerProps) {
	const iframeRef = useRef<HTMLIFrameElement>(null);
	const editIframeRef = useRef<HTMLIFrameElement>(null);
	const editHtmlSetRef = useRef(false);
	const [copiedAll, setCopiedAll] = useState(false);
	const [activeTab, setActiveTab] = useState<"preview" | "edit" | "compare" | "code">("preview");
	const [isFullscreen, setIsFullscreen] = useState(false);
	const [selectedElement, setSelectedElement] = useState<{
		tag: string; classes: string; text: string;
		rect: { top: number; left: number; width: number; height: number };
	} | null>(null);
	const [editStyles, setEditStyles] = useState({
		fontSize: '', fontWeight: '400', fontFamily: 'Inter',
		color: '#000000', textAlign: 'left', lineHeight: '1.5',
		letterSpacing: '0', paddingTop: '', paddingRight: '',
		paddingBottom: '', paddingLeft: '', marginTop: '',
		marginRight: '', marginBottom: '', marginLeft: '',
		gap: '', width: '', height: '', minWidth: '', maxWidth: '',
		minHeight: '', maxHeight: '', backgroundColor: '#ffffff',
		opacity: '1', borderWidth: '', borderStyle: 'solid',
		borderColor: '#000000', borderRadius: '',
		boxShadow: '', textShadow: '', transform: '',
		overflow: 'visible', cursor: 'default',
	});
	const [aiSuggestion, setAiSuggestion] = useState('');
	const [aiLoading, setAiLoading] = useState(false);
	const [currentHtml, setCurrentHtml] = useState('');

	// Bug 3 fix — stable callbacks that read editIframeRef.current at call-time
	const sendToEditIframe = useCallback((msg: Record<string, unknown>) => {
		editIframeRef.current?.contentWindow?.postMessage(msg, '*');
	}, []);

	const applyStyle = useCallback((property: string, value: string) => {
		sendToEditIframe({ type: 'apply-style', property, value });
		// Force iframe to send back updated DOM so currentHtml is always current
		sendToEditIframe({ type: 'get-html' });
	}, [sendToEditIframe]);

	// Escape key exits fullscreen
	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") setIsFullscreen(false);
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, []);

	// Bug 1 fix — set srcdoc imperatively when entering Edit tab (only once per result)
	useEffect(() => {
		if (activeTab === 'edit' && editIframeRef.current && !editHtmlSetRef.current) {
			editIframeRef.current.srcdoc = currentHtml || htmlWithUpload;
			editHtmlSetRef.current = true;
		}
	}, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

	// Bug 1 fix — when AI suggestion returns new HTML, push it into the already-mounted iframe
	useEffect(() => {
		if (editIframeRef.current && editHtmlSetRef.current && currentHtml) {
			editIframeRef.current.srcdoc = currentHtml;
		}
	}, [currentHtml]);

	// Listen for postMessage from iframe (edit script)
	useEffect(() => {
		const handler = (e: MessageEvent) => {
			const msg = e.data;
			if (!msg?.type) return;
			if (msg.type === 'element-select') {
				setSelectedElement({ tag: msg.tag, classes: msg.classes, text: msg.text, rect: msg.rect });
				setEditStyles(prev => ({ ...prev,
					fontSize: '', fontWeight: '400', color: '#000000', textAlign: 'left',
				}));
			} else if (msg.type === 'html-snapshot') {
				setCurrentHtml(msg.html);
			}
		};
		window.addEventListener('message', handler);
		return () => window.removeEventListener('message', handler);
	}, []);

	// Sync currentHtml when result changes; also reset edit iframe guard so new result loads
	useEffect(() => {
		editHtmlSetRef.current = false;
		if (result) {
			try {
				const trimmed = result.trim();
				if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
					const p = JSON.parse(trimmed);
					if (typeof p.code === 'string') { setCurrentHtml(p.code); return; }
				}
			} catch { /* ignore */ }
			setCurrentHtml(result.trim());
		}
	}, [result]);

	const handleCopyAll = useCallback(async () => {
		await navigator.clipboard.writeText(result);
		setCopiedAll(true);
		setTimeout(() => setCopiedAll(false), 2000);
	}, [result]);

	const handleDownload = useCallback(() => {
		const blob = new Blob([result], { type: "text/markdown;charset=utf-8" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = `devkernel-ai-result-${Date.now()}.md`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	}, [result]);

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

	let parsedJson: { code?: string; [key: string]: any } | null = null;
	let displayMarkdown = result;

	if (result) {
		try {
			const trimmed = result.trim();
			if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
				const parsed = JSON.parse(trimmed);
				if (typeof parsed.code === "string") {
					parsedJson = parsed;
					displayMarkdown = `\`\`\`html\n${parsed.code}\n\`\`\``;
				}
			}
		} catch (_e) {
			// Ignore parsing errors
		}

		// Fallback: Check if the result embeds a standalone HTML block in markdown
		if (!parsedJson) {
			const htmlBlockRegex = /```(?:html)?\s*(<!DOCTYPE html>[\s\S]*?<html[\s\S]*?)```/i;
			const match = result.trim().match(htmlBlockRegex);
			if (match?.[1]) {
				parsedJson = { code: match[1] };
			} else if (result.trim().startsWith("<!DOCTYPE html>") || result.trim().startsWith("<html")) {
				parsedJson = { code: result.trim() };
			}
		}
	}

	const hasHtmlCode = !!(
		parsedJson?.code &&
		(parsedJson.code.includes("<!DOCTYPE html>") || parsedJson.code.includes("<html"))
	);

	// Extract uploaded image src for compare tab
	const hasCompare = hasHtmlCode && !!uploadedImageSrc;

	// The code field already has the upload+edit scripts injected server-side
	const htmlWithUpload = parsedJson?.code ?? "";

	// Pipeline metadata from result JSON (all fields except 'code')
	const meta: Record<string, string> = parsedJson
		? Object.fromEntries(
				Object.entries(parsedJson)
					.filter(([k]) => k !== "code")
					.map(([k, v]) => [k, String(v)])
		  )
		: {};

	// Tab definitions — Edit only for HTML; Code only for HTML; Compare only when image uploaded
	const tabs = [
		{ id: "preview" as const, label: hasHtmlCode ? "Preview" : "Result", icon: null },
		...(hasHtmlCode ? [{ id: "edit" as const, label: "Edit", icon: null }] : []),
		...(hasCompare ? [{ id: "compare" as const, label: "Compare", icon: null }] : []),
		...(hasHtmlCode ? [{ id: "code" as const, label: "Code", icon: null }] : []),
	];

	// ── Wrapper classes (prevents React from destroying the iframe on toggle) ──
	const wrapperClasses = isFullscreen
		? "fixed inset-0 z-[100] flex flex-col bg-background animate-in fade-in duration-150"
		: "rounded-xl border bg-card text-card-foreground shadow overflow-hidden relative";

	return (
		<div className={wrapperClasses}>
			{/* ── Pipeline Steps Bar ── */}
			<PipelineStepsBar meta={meta} isLoading={isLoading} />

			{/* ── Tab bar + action buttons ── */}
			<div className="flex items-center justify-between border-b border-border/50 bg-muted/10 px-4">
				{/* Tabs */}
				<div className="flex">
					{tabs.map((tab) => (
						<button
							key={tab.id}
							onClick={() => setActiveTab(tab.id)}
							className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
								activeTab === tab.id
									? "border-primary text-foreground"
									: "border-transparent text-muted-foreground hover:text-foreground"
							}`}
						>
							{tab.icon}
							{tab.label}
						</button>
					))}
				</div>

				{/* Action buttons */}
				<div className="flex items-center gap-2 py-2">
					{hasHtmlCode && (
						<button
							onClick={() => setIsFullscreen((f) => !f)}
							className="rounded-md border border-border/60 bg-background/80 p-1.5 text-muted-foreground backdrop-blur-sm transition-all hover:bg-muted hover:text-foreground"
							title={isFullscreen ? "Exit fullscreen (Esc)" : "Fullscreen"}
						>
							{isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
						</button>
					)}
					<Button variant="outline" size="sm" onClick={handleCopyAll} className="h-8 text-xs bg-background/80 backdrop-blur-sm">
						{copiedAll ? <Check className="h-3.5 w-3.5 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
						{copiedAll ? "Copied!" : "Copy"}
					</Button>
					<Button variant="outline" size="sm" onClick={handleDownload} className="h-8 text-xs bg-background/80 backdrop-blur-sm">
						<Download className="h-3.5 w-3.5 mr-1" />
						Download
					</Button>
				</div>
			</div>

			{/* ── Content ── */}
			<div className={isFullscreen ? "flex-1 overflow-hidden p-4" : "p-4"}>

				{/* PREVIEW TAB */}
				{activeTab === "preview" && hasHtmlCode && (
					<div className="flex flex-col h-full space-y-2">
						<div className="flex items-center gap-2 shrink-0">
							<p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
								Live Preview — images are click-to-replace
							</p>
							<div className="flex items-center gap-1 rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] text-blue-500 border border-blue-500/20">
								<Upload className="h-2.5 w-2.5" />
								Click any image to swap it
							</div>
						</div>
						<div
							className={`w-full flex-1 overflow-hidden rounded-lg border border-border bg-white ${
								!isFullscreen && "h-[580px]"
							}`}
						>
							<iframe
								ref={iframeRef}
								title="Preview"
								srcDoc={currentHtml || htmlWithUpload}
								className="h-full w-full border-0"
								// CRITICAL FIX: allow-same-origin and popups are required for the file picker to open
								sandbox="allow-scripts allow-same-origin allow-popups"
							/>
						</div>
					</div>
				)}


				{/* EDIT TAB */}
				{activeTab === "edit" && hasHtmlCode && (() => {
					const lbl = (t: string) => <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{t}</p>;
					const bi = (ph: string, val: string, set: (v: string) => void, done: (v: string) => void) => (
						<input className="h-7 w-full rounded border border-border bg-muted/30 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
							placeholder={ph} value={val} onChange={e => set(e.target.value)} onBlur={e => done(e.target.value)} />
					);
					const bs = (val: string, opts: string[], pick: (v: string) => void) => (
						<select className="h-7 w-full rounded border border-border bg-muted/30 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
							value={val} onChange={e => pick(e.target.value)}>
							{opts.map(o => <option key={o} value={o}>{o}</option>)}
						</select>
					);
					const sec = (title: string, children: React.ReactNode) => (
						<details open className="border-b border-border">
							<summary className="cursor-pointer select-none px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hover:bg-muted/40">{title}</summary>
							<div className="space-y-2 px-3 pb-3 pt-1">{children}</div>
						</details>
					);
					return (
						<div className={`flex overflow-hidden rounded-lg border border-border ${!isFullscreen ? 'h-[620px]' : 'h-full'}`}>
							<div className="flex-1 overflow-hidden bg-white">
								<iframe ref={editIframeRef} title="Edit Preview"
									className="h-full w-full border-0" sandbox="allow-scripts allow-same-origin allow-popups" />
							</div>
							<div className="w-80 shrink-0 overflow-y-auto border-l border-border bg-card">
								{sec("Selected Element",
									selectedElement
										? <div className="space-y-1.5 rounded bg-muted/30 p-2 text-xs">
											<div><span className="text-muted-foreground">Tag: </span><code className="text-primary">&lt;{selectedElement.tag}&gt;</code></div>
											<div><span className="text-muted-foreground">Classes: </span><span className="break-all font-mono text-[10px]">{selectedElement.classes || '—'}</span></div>
											<div>{lbl("Text")}<textarea className="h-12 w-full resize-none rounded border border-border bg-muted/30 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
												defaultValue={selectedElement.text} onBlur={e => { sendToEditIframe({ type: 'apply-text', value: e.target.value }); sendToEditIframe({ type: 'get-html' }); }} /></div>
										</div>
										: <p className="text-xs text-muted-foreground">Click any element in the preview to select it.</p>
								)}
								{sec("Typography", <div className="grid grid-cols-2 gap-2">
									<div>{lbl("Size (px)")}{bi("16", editStyles.fontSize, v => setEditStyles(p => ({ ...p, fontSize: v })), v => applyStyle('fontSize', v + 'px'))}</div>
									<div>{lbl("Weight")}{bs(editStyles.fontWeight, ['100','200','300','400','500','600','700','800','900'], v => { setEditStyles(p => ({ ...p, fontWeight: v })); applyStyle('fontWeight', v); })}</div>
									<div className="col-span-2">{lbl("Family")}{bs(editStyles.fontFamily, ['Inter','Roboto','DM Sans','Geist','monospace','serif'], v => { setEditStyles(p => ({ ...p, fontFamily: v })); applyStyle('fontFamily', v); })}</div>
									<div>{lbl("Color")}<input type="color" className="h-7 w-full cursor-pointer rounded border border-border" value={editStyles.color} onChange={e => { setEditStyles(p => ({ ...p, color: e.target.value })); applyStyle('color', e.target.value); }} /></div>
									<div>{lbl("Line-height")}{bi("1.5", editStyles.lineHeight, v => setEditStyles(p => ({ ...p, lineHeight: v })), v => applyStyle('lineHeight', v))}</div>
									<div>{lbl("Letter-sp.")}{bi("0px", editStyles.letterSpacing, v => setEditStyles(p => ({ ...p, letterSpacing: v })), v => applyStyle('letterSpacing', v))}</div>
									<div className="col-span-2">{lbl("Align")}<div className="flex gap-1">
										{['left','center','right','justify'].map(a => (
											<button key={a} onClick={() => { setEditStyles(p => ({ ...p, textAlign: a })); applyStyle('textAlign', a); }}
												className={`flex-1 rounded border py-0.5 text-[10px] transition-colors ${editStyles.textAlign === a ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-primary/50'}`}>{a[0].toUpperCase()}</button>
										))}
									</div></div>
								</div>)}
								{sec("Spacing", <div className="space-y-2">
									<div>{lbl("Padding T/R/B/L")}<div className="grid grid-cols-4 gap-1">{(['paddingTop','paddingRight','paddingBottom','paddingLeft'] as const).map(k => (
										<input key={k} placeholder="0px" className="h-7 w-full rounded border border-border bg-muted/30 px-1 text-center text-xs focus:outline-none focus:ring-1 focus:ring-primary"
											value={editStyles[k]} onChange={e => setEditStyles(p => ({ ...p, [k]: e.target.value }))} onBlur={e => applyStyle(k, e.target.value)} />
									))}</div></div>
									<div>{lbl("Margin T/R/B/L")}<div className="grid grid-cols-4 gap-1">{(['marginTop','marginRight','marginBottom','marginLeft'] as const).map(k => (
										<input key={k} placeholder="0px" className="h-7 w-full rounded border border-border bg-muted/30 px-1 text-center text-xs focus:outline-none focus:ring-1 focus:ring-primary"
											value={editStyles[k]} onChange={e => setEditStyles(p => ({ ...p, [k]: e.target.value }))} onBlur={e => applyStyle(k, e.target.value)} />
									))}</div></div>
									<div>{lbl("Gap")}{bi("0px", editStyles.gap, v => setEditStyles(p => ({ ...p, gap: v })), v => applyStyle('gap', v))}</div>
								</div>)}
								{sec("Size", <div className="grid grid-cols-2 gap-2">{(['width','height','minWidth','maxWidth','minHeight','maxHeight'] as const).map(k => (
									<div key={k}>{lbl(k.replace(/([A-Z])/g, ' $1').trim())}
										<input placeholder="auto" className="h-7 w-full rounded border border-border bg-muted/30 px-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
											value={editStyles[k]} onChange={e => setEditStyles(p => ({ ...p, [k]: e.target.value }))} onBlur={e => applyStyle(k, e.target.value)} />
									</div>
								))}</div>)}
								{sec("Background", <div className="space-y-2">
									<div>{lbl("Color")}<input type="color" className="h-7 w-full cursor-pointer rounded border border-border" value={editStyles.backgroundColor} onChange={e => { setEditStyles(p => ({ ...p, backgroundColor: e.target.value })); applyStyle('backgroundColor', e.target.value); }} /></div>
									<div>{lbl("Image")}<input type="file" accept="image/*" className="w-full text-xs" onChange={e => { const f = e.target.files?.[0]; if (!f) return; const r = new FileReader(); r.onload = ev => applyStyle('backgroundImage', `url(${ev.target!.result})`); r.readAsDataURL(f); }} /></div>
									<div>{lbl("Opacity")}<input type="range" min="0" max="1" step="0.01" className="w-full accent-primary" value={editStyles.opacity} onChange={e => { setEditStyles(p => ({ ...p, opacity: e.target.value })); applyStyle('opacity', e.target.value); }} /></div>
								</div>)}
								{sec("Border", <div className="grid grid-cols-2 gap-2">
									<div>{lbl("Width (px)")}{bi("0", editStyles.borderWidth, v => setEditStyles(p => ({ ...p, borderWidth: v })), v => applyStyle('borderWidth', v + 'px'))}</div>
									<div>{lbl("Style")}{bs(editStyles.borderStyle, ['none','solid','dashed','dotted','double'], v => { setEditStyles(p => ({ ...p, borderStyle: v })); applyStyle('borderStyle', v); })}</div>
									<div>{lbl("Color")}<input type="color" className="h-7 w-full cursor-pointer rounded border border-border" value={editStyles.borderColor} onChange={e => { setEditStyles(p => ({ ...p, borderColor: e.target.value })); applyStyle('borderColor', e.target.value); }} /></div>
									<div>{lbl("Radius (px)")}{bi("0", editStyles.borderRadius, v => setEditStyles(p => ({ ...p, borderRadius: v })), v => applyStyle('borderRadius', v + 'px'))}</div>
								</div>)}
								{sec("Effects", <div className="space-y-2">
									<div>{lbl("Box shadow")}{bi("0 4px 6px rgba(0,0,0,.1)", editStyles.boxShadow, v => setEditStyles(p => ({ ...p, boxShadow: v })), v => applyStyle('boxShadow', v))}</div>
									<div>{lbl("Text shadow")}{bi("none", editStyles.textShadow, v => setEditStyles(p => ({ ...p, textShadow: v })), v => applyStyle('textShadow', v))}</div>
									<div>{lbl("Transform")}{bi("rotate(0deg)", editStyles.transform, v => setEditStyles(p => ({ ...p, transform: v })), v => applyStyle('transform', v))}</div>
									<div>{lbl("Overflow")}{bs(editStyles.overflow, ['visible','hidden','scroll','auto'], v => { setEditStyles(p => ({ ...p, overflow: v })); applyStyle('overflow', v); })}</div>
									<div>{lbl("Cursor")}{bs(editStyles.cursor, ['default','pointer','not-allowed','grab','crosshair','text'], v => { setEditStyles(p => ({ ...p, cursor: v })); applyStyle('cursor', v); })}</div>
								</div>)}
								{sec("AI Suggestions", <div className="space-y-2">
									<textarea className="h-20 w-full resize-none rounded border border-border bg-muted/30 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
										placeholder="e.g. make the header darker…" value={aiSuggestion} onChange={e => setAiSuggestion(e.target.value)} />
									<button disabled={aiLoading || !aiSuggestion.trim()}
										className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50 hover:bg-primary/90 transition-colors"
										onClick={async () => {
											setAiLoading(true);
											try {
												const rawHtml = currentHtml || htmlWithUpload;
												// 1. Extract all Base64 data URIs and replace with lightweight placeholders
												const imageMap: Record<string, string> = {};
												let counter = 0;
												const cleanedHtml = rawHtml.replace(/(data:image\/[^;]+;base64,[A-Za-z0-9+\/=]+)/g, (match) => {
													const placeholder = `__USER_UPLOADED_IMG_${counter++}__`;
													imageMap[placeholder] = match;
													return placeholder;
												});
												// 2. Send lightweight HTML to LLM
												const res = await fetch('/api/tools/screenshot-to-code', {
													method: 'POST',
													headers: { 'Content-Type': 'application/json' },
													body: JSON.stringify({ update_prompt: aiSuggestion, previous_code: cleanedHtml }),
												});
												const d = await res.json();
												// 3. Restore all Base64 images back into exact positions
												if (d.code) {
													let finalHtml = d.code;
													Object.entries(imageMap).forEach(([placeholder, dataUrl]) => {
														finalHtml = finalHtml.replace(new RegExp(placeholder, 'g'), dataUrl);
													});
													setCurrentHtml(finalHtml);
												}
											} catch (err) {
												console.error('AI Edit Failed', err);
											} finally {
												setAiLoading(false);
											}
										}}>
										{aiLoading ? <Spinner className="h-3 w-3" /> : null}{aiLoading ? 'Applying…' : 'Apply'}
									</button>
								</div>)}
								{sec("Export", <div className="flex flex-col gap-1.5">
									<button className="rounded border border-border px-3 py-1.5 text-xs hover:bg-muted transition-colors" onClick={() => navigator.clipboard.writeText(currentHtml || htmlWithUpload)}>Copy HTML</button>
									<button className="rounded border border-border px-3 py-1.5 text-xs hover:bg-muted transition-colors" onClick={() => { const b = new Blob([currentHtml || htmlWithUpload], { type: 'text/html' }); const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'design.html'; a.click(); }}>Download .html</button>
									<button className="rounded border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 transition-colors" onClick={() => setCurrentHtml(htmlWithUpload)}>Reset to Original</button>
								</div>)}
							</div>
						</div>
					);
				})()}

				{/* COMPARE TAB */}
				{activeTab === "compare" && hasCompare && (
					<div className="space-y-2">
						<p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
							Side-by-side fidelity comparison
						</p>
						<SideBySideComparison
							uploadedSrc={uploadedImageSrc!}
							generatedCode={htmlWithUpload}
							isFullscreen={isFullscreen}
						/>
					</div>
				)}

				{/* CODE TAB */}
				{activeTab === "code" && (
					<div className="space-y-4">
						{/* HTML code block */}
						<div className="group/code relative">
							<div className="flex items-center justify-between px-4 py-2 border border-border rounded-t-lg bg-zinc-900 border-b-0">
								<span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
									HTML · Tailwind CSS
								</span>
								<CopyButton
									text={parsedJson?.code ?? result}
									className="relative opacity-100 rounded-md bg-zinc-800 p-1.5 text-zinc-400 transition-all hover:bg-zinc-700 hover:text-white"
								/>
							</div>
							<pre className="overflow-x-auto rounded-b-lg border border-border bg-zinc-950 px-4 py-4 text-sm leading-relaxed text-zinc-100 max-h-[520px]">
								<code>{parsedJson?.code ?? result}</code>
							</pre>
						</div>

						{/* Pipeline metadata */}
						{meta && Object.keys(meta).length > 0 && (
							<div className="rounded-lg border border-border bg-muted/20">
								<div className="px-4 py-2 border-b border-border">
									<h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
										Pipeline Metadata
									</h4>
								</div>
								<div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-3 lg:grid-cols-4">
									{Object.entries(meta).map(([k, v]) => (
										<div key={k} className="bg-background px-4 py-3">
											<p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{k.replace(/_/g, " ")}</p>
											<p className="mt-0.5 font-mono text-sm text-foreground">{String(v)}</p>
										</div>
									))}
								</div>
							</div>
						)}
					</div>
				)}

				{/* PREVIEW TAB — Markdown fallback (non-HTML results) */}
				{activeTab === "preview" && !hasHtmlCode && (
					<article
						className={[
							"prose prose-sm dark:prose-invert max-w-none",
							"prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-foreground",
							"prose-h1:text-xl prose-h1:mt-6 prose-h1:mb-4",
							"prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3 prose-h2:border-b prose-h2:border-border prose-h2:pb-2",
							"prose-h3:text-base prose-h3:mt-5 prose-h3:mb-2",
							"prose-p:text-foreground/90 prose-p:leading-7 prose-p:my-3",
							"prose-strong:text-foreground prose-strong:font-semibold",
							"prose-a:text-primary prose-a:underline prose-a:underline-offset-4",
							"prose-li:text-foreground/90 prose-li:my-1 prose-li:leading-7",
							"prose-ul:my-3 prose-ul:pl-6 prose-ol:my-3 prose-ol:pl-6",
							"prose-code:rounded-md prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[13px] prose-code:font-mono prose-code:before:content-none prose-code:after:content-none",
							"prose-pre:rounded-lg prose-pre:border prose-pre:border-border prose-pre:bg-zinc-950 prose-pre:px-4 prose-pre:py-4 prose-pre:my-4",
						].join(" ")}
					>
						<ReactMarkdown
							remarkPlugins={[remarkGfm]}
							components={{
								pre({ children, ...props }) {
									let codeText = "";
									try {
										const child = children as any;
										codeText = child?.props?.children ? String(child.props.children) : String(children || "");
									} catch { codeText = String(children || ""); }
									return (
										<div className="group/code relative my-4">
											<CopyButton text={codeText} />
											<pre className="overflow-x-auto rounded-lg border border-border bg-zinc-950 px-4 py-4 text-sm leading-relaxed text-zinc-100 dark:bg-zinc-900" {...props}>
												{children}
											</pre>
										</div>
									);
								},
								code({ className, children, ...props }) {
									if (!className) return <code className="rounded-md bg-muted px-1.5 py-0.5 text-[13px] font-mono font-medium text-foreground" {...props}>{children}</code>;
									if (className.includes("language-mermaid")) return <MermaidViewer chart={String(children)} />;
									return <code className={`${className} text-sm leading-relaxed text-zinc-100`} {...props}>{children}</code>;
								},
								table({ children, ...props }) { return <div className="my-4 overflow-x-auto rounded-lg border border-border"><table className="w-full text-sm" {...props}>{children}</table></div>; },
								thead({ children, ...props }) { return <thead className="border-b border-border bg-muted/50" {...props}>{children}</thead>; },
								th({ children, ...props }) { return <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-foreground" {...props}>{children}</th>; },
								td({ children, ...props }) { return <td className="border-t border-border px-4 py-2.5 text-foreground/90" {...props}>{children}</td>; },
								blockquote({ children, ...props }) { return <blockquote className="my-4 rounded-r-lg border-l-4 border-l-primary/50 bg-muted/30 py-2 px-4 text-foreground/80 [&>p]:my-1" {...props}>{children}</blockquote>; },
								a({ children, href, ...props }) { return <a href={href} className="text-primary underline underline-offset-4" target="_blank" rel="noopener noreferrer" {...props}>{children}</a>; },
							}}
						>
							{displayMarkdown}
						</ReactMarkdown>
						{streaming && isLoading && <span className="mt-1 inline-block h-5 w-1.5 animate-pulse rounded-sm bg-primary" />}
					</article>
				)}
			</div>
		</div>
	);
}