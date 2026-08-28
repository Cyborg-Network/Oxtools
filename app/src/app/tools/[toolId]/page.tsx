"use client";

import { Button, Label, Textarea } from "@ansospace/ui";
import { ArrowUpRight, Crown, Lock, Play, X } from "lucide-react";
import Image from "next/image";
import { notFound, useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
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
	const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
	// Defer localStorage-dependent rendering to prevent hydration mismatch.
	// Server always renders the "Run" button; limit state only applies after mount.
	const [mounted, setMounted] = useState(false);
	useEffect(() => setMounted(true), []);

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
										type="button"
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
									type="button"
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

			{/* ─── Upgrade Dialog Popup ──────────────────────────── */}
			{showUpgradeDialog && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
					<div className="relative mx-4 w-full max-w-md rounded-2xl border border-border/50 bg-card p-6 shadow-2xl animate-in zoom-in-95 duration-200">
						{/* Close button */}
						<button
							type="button"
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

function PdfDropField({
	config,
	value,
	onChange,
}: {
	config: InputFieldConfig;
	value: string;
	onChange: (value: string) => void;
}) {
	const dropRef = useRef<HTMLButtonElement>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const [dropState, setDropState] = useState<
		| "idle"
		| "hover"
		| "loading"
		| "loading-ocr"
		| "loading-excel"
		| "loading-word"
		| "loading-image-ocr"
		| "done"
		| "error"
	>("idle");
	const [fileName, setFileName] = useState<string>("");
	const [extractError, setExtractError] = useState<string>("");
	const [source, setSource] = useState<"file" | "manual">("manual");

	const maxMb = config.maxSizeMb ?? 20;
	const maxBytes = maxMb * 1024 * 1024;

	const extractText = useCallback(
		async (file: File): Promise<string> => {
			if (file.size > maxBytes) {
				throw new Error(`File exceeds ${maxMb} MB limit.`);
			}

			const name = file.name.toLowerCase();
			const win = window as unknown as Record<string, unknown>;

			// ── HELPER: lazy-load a CDN script (idempotent) ──────────────────
			async function loadScript(url: string, globalKey: string, label: string) {
				if (!win[globalKey]) {
					await new Promise<void>((resolve, reject) => {
						const s = document.createElement("script");
						s.src = url;
						s.onload = () => resolve();
						s.onerror = () =>
							reject(new Error(`Failed to load ${label}. Check your internet connection.`));
						document.head.appendChild(s);
					});
				}
			}

			// ── HELPER: OCR for an ImageBitmap or Blob with Tesseract.js ──────────────
			async function runOcrOnBlob(blob: Blob): Promise<string> {
				await loadScript(
					"https://cdnjs.cloudflare.com/ajax/libs/tesseract.js/5.0.4/tesseract.min.js",
					"Tesseract",
					"Tesseract.js"
				);
				type TWorker = {
					recognize: (img: Blob) => Promise<{ data: { text: string } }>;
					terminate: () => Promise<void>;
				};
				type TTesseract = { createWorker: (lang: string) => Promise<TWorker> };
				const Tesseract = win.Tesseract as TTesseract;
				const worker = await Tesseract.createWorker("eng");
				try {
					const { data } = await worker.recognize(blob);
					return data.text.trim();
				} finally {
					await worker.terminate();
				}
			}

			// ════════════════════════════════════════════════════════════════════════
			// PDF  (.pdf)
			// ════════════════════════════════════════════════════════════════════════
			if (name.endsWith(".pdf") || file.type === "application/pdf") {
				// 1. Load pdf.js if missing
				await loadScript(
					"https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js",
					"pdfjsLib",
					"pdf.js"
				);
				(
					win.pdfjsLib as { GlobalWorkerOptions: { workerSrc: string } }
				).GlobalWorkerOptions.workerSrc =
					"https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

				type PdfPage = {
					getTextContent: () => Promise<{ items: { str: string; hasEOL?: boolean }[] }>;
					getViewport: (o: { scale: number }) => { width: number; height: number };
					render: (p: {
						canvasContext: CanvasRenderingContext2D;
						viewport: { width: number; height: number };
					}) => { promise: Promise<void> };
				};
				const pdfjs = win.pdfjsLib as {
					getDocument: (src: { data: ArrayBuffer }) => {
						promise: Promise<{ numPages: number; getPage: (n: number) => Promise<PdfPage> }>;
					};
				};

				const arrayBuffer = await file.arrayBuffer();
				const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
				const pages: string[] = [];

				// 2. Native text extraction
				for (let i = 1; i <= pdf.numPages; i++) {
					const page = await pdf.getPage(i);
					const content = await page.getTextContent();
					const pageText = content.items
						.map((item) => item.str + (item.hasEOL ? "\n" : ""))
						.join("");
					pages.push(pageText.trim());
				}

				const nativeText = pages.join("\n\n").trim();
				if (nativeText.length > 30) return nativeText;

				// 3. OCR fallback — scanned PDF (images, handwritten text, forms)
				setDropState("loading-ocr");
				const ocrPages: string[] = [];
				const MAX_OCR_PAGES = 20;
				const pagesToProcess = Math.min(pdf.numPages, MAX_OCR_PAGES);

				for (let i = 1; i <= pagesToProcess; i++) {
					const page = await pdf.getPage(i);
					const viewport = page.getViewport({ scale: 2.5 });
					const canvas = document.createElement("canvas");
					canvas.width = Math.floor(viewport.width);
					canvas.height = Math.floor(viewport.height);
					const ctx = canvas.getContext("2d");
					if (!ctx) throw new Error("Could not render PDF page for OCR.");
					await page.render({ canvasContext: ctx, viewport }).promise;

					const blob = await new Promise<Blob>((res, rej) =>
						canvas.toBlob(
							(b) => (b ? res(b) : rej(new Error("Could not render PDF page to image."))),
							"image/png"
						)
					);
					ocrPages.push(await runOcrOnBlob(blob));

					// Release canvas memory after each page
					canvas.width = 0;
					canvas.height = 0;
				}

				if (pdf.numPages > MAX_OCR_PAGES) {
					ocrPages.push(
						`\n\n[Note: OCR was limited to the first ${MAX_OCR_PAGES} pages out of ${pdf.numPages} total.]`
					);
				}

				const ocrText = ocrPages.join("\n\n").trim();
				if (!ocrText)
					throw new Error(
						"OCR did not find readable text. The PDF may be blank or fully graphical."
					);
				return ocrText;
			}

			// ════════════════════════════════════════════════════════════════════════
			// DIRECT IMAGES (.jpg, .jpeg, .png, .webp, .gif)
			// Use case: photo of a document, whiteboard, scanned receipt
			// ════════════════════════════════════════════════════════════════════════
			if (
				name.endsWith(".jpg") ||
				name.endsWith(".jpeg") ||
				name.endsWith(".png") ||
				name.endsWith(".webp") ||
				name.endsWith(".gif") ||
				file.type.startsWith("image/")
			) {
				setDropState("loading-image-ocr");
				const text = await runOcrOnBlob(file);
				if (!text)
					throw new Error(
						"No readable text found in this image. Make sure the text is clear and not too small."
					);
				return text;
			}

			// ════════════════════════════════════════════════════════════════════════
			// EXCEL (.xlsx, .xls)
			// Convert to tabular text: headers + rows separated by tabs
			// ════════════════════════════════════════════════════════════════════════
			if (name.endsWith(".xlsx") || name.endsWith(".xls")) {
				setDropState("loading-excel");
				await loadScript(
					"https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js",
					"XLSX",
					"SheetJS"
				);
				type XLSXLib = {
					read: (
						data: ArrayBuffer,
						opts: { type: string }
					) => {
						SheetNames: string[];
						Sheets: Record<string, unknown>;
					};
					utils: {
						sheet_to_csv: (sheet: unknown) => string;
					};
				};
				const XLSX = win.XLSX as XLSXLib;
				const arrayBuffer = await file.arrayBuffer();
				const workbook = XLSX.read(arrayBuffer, { type: "array" });
				const sections: string[] = [];

				for (const sheetName of workbook.SheetNames) {
					const csv = XLSX.utils.sheet_to_csv(workbook.Sheets[sheetName]);
					const nonEmpty = csv
						.split("\n")
						.filter((l) => l.replace(/,/g, "").trim())
						.join("\n");
					if (nonEmpty.trim()) {
						sections.push(`### Sheet: ${sheetName}\n${nonEmpty}`);
					}
				}

				if (!sections.length) throw new Error("The Excel file appears to be empty.");
				return sections.join("\n\n");
			}

			// ════════════════════════════════════════════════════════════════════════
			// WORD (.docx)
			// Extract text while preserving paragraph structure
			// ════════════════════════════════════════════════════════════════════════
			if (name.endsWith(".docx")) {
				setDropState("loading-word");
				await loadScript(
					"https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js",
					"mammoth",
					"Mammoth.js"
				);
				type MammothLib = {
					extractRawText: (opts: { arrayBuffer: ArrayBuffer }) => Promise<{ value: string }>;
				};
				const mammoth = win.mammoth as MammothLib;
				const arrayBuffer = await file.arrayBuffer();
				const result = await mammoth.extractRawText({ arrayBuffer });
				const text = result.value.trim();
				if (!text)
					throw new Error("The Word document appears to be empty or contains only images.");
				return text;
			}

			// ════════════════════════════════════════════════════════════════════════
			// CSV (.csv) — browser-native, no library needed
			// ════════════════════════════════════════════════════════════════════════
			if (name.endsWith(".csv")) {
				const text = await file.text();
				if (!text.trim()) throw new Error("The CSV file is empty.");
				// Count columns from the first row to give the model context
				const lines = text.split("\n").filter((l) => l.trim());
				const headerCols = lines[0]?.split(",").length ?? 0;
				const preview = `CSV Document — ${lines.length - 1} rows × ${headerCols} columns\n\n${text}`;
				return preview;
			}

			// ════════════════════════════════════════════════════════════════════════
			// PLAIN TEXT (.txt, .md, and any other)
			// ════════════════════════════════════════════════════════════════════════
			const text = await file.text();
			if (!text.trim()) throw new Error("The file appears to be empty.");
			return text;
		},
		[maxMb, maxBytes]
	);

	const processFile = useCallback(
		async (file: File) => {
			setDropState("loading");
			setFileName(file.name);
			setExtractError("");
			try {
				const text = await extractText(file);
				if (!text.trim()) throw new Error("No readable text found in this file.");
				onChange(text);
				setSource("file"); // Track that this value came from a file
				setDropState("done");
			} catch (err) {
				setExtractError(err instanceof Error ? err.message : "Unknown error.");
				setDropState("error");
			}
		},
		[extractText, onChange]
	);

	const handleDragOver = useCallback((e: React.DragEvent) => {
		e.preventDefault();
		setDropState("hover");
	}, []);

	const handleDragLeave = useCallback(() => {
		setDropState(source === "file" ? "done" : "idle");
	}, [source]);

	const handleDrop = useCallback(
		(e: React.DragEvent) => {
			e.preventDefault();
			const file = e.dataTransfer.files?.[0];
			if (file) processFile(file);
		},
		[processFile]
	);

	const handleFileInput = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			const file = e.target.files?.[0];
			if (file) processFile(file);
			e.target.value = "";
		},
		[processFile]
	);

	const handleClear = useCallback(() => {
		onChange("");
		setFileName("");
		setDropState("idle");
		setExtractError("");
		setSource("manual"); // Reset to manual mode when cleared
	}, [onChange]);

	const isLoading =
		dropState === "loading" ||
		dropState === "loading-ocr" ||
		dropState === "loading-excel" ||
		dropState === "loading-word" ||
		dropState === "loading-image-ocr";

	const dropZoneBorder =
		dropState === "hover"
			? "border-primary bg-primary/5"
			: dropState === "error"
				? "border-destructive bg-destructive/5"
				: dropState === "done"
					? "border-primary/50 bg-primary/[0.03]"
					: isLoading
						? "border-primary/30 bg-muted/20"
						: "border-input hover:border-primary/40 hover:bg-muted/30";

	return (
		<div className="space-y-2">
			<Label>{config.label}</Label>

			<input
				ref={fileInputRef}
				type="file"
				accept={config.accept || ".pdf,.txt,.md,.csv,.xlsx,.xls,.docx,.jpg,.jpeg,.png,.webp,.gif"}
				className="hidden"
				onChange={handleFileInput}
			/>
			<button
				type="button"
				ref={dropRef}
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				onDrop={handleDrop}
				onClick={() => fileInputRef.current?.click()}
				className={`relative flex w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors ${dropZoneBorder}`}
			>
				{dropState === "loading" && (
					<>
						<div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
						<p className="text-sm text-muted-foreground">Extracting text from {fileName}...</p>
					</>
				)}

				{dropState === "loading-ocr" && (
					<>
						<div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
						<p className="text-sm text-muted-foreground">
							No text found - running OCR on {fileName}...
						</p>
						<p className="text-xs text-muted-foreground">This may take 10-30 seconds</p>
					</>
				)}

				{dropState === "loading-excel" && (
					<>
						<div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
						<p className="text-sm text-muted-foreground">Reading spreadsheet from {fileName}…</p>
						<p className="text-xs text-muted-foreground">Converting sheets to text</p>
					</>
				)}

				{dropState === "loading-word" && (
					<>
						<div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
						<p className="text-sm text-muted-foreground">Extracting text from {fileName}…</p>
						<p className="text-xs text-muted-foreground">Processing Word document</p>
					</>
				)}

				{dropState === "loading-image-ocr" && (
					<>
						<div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
						<p className="text-sm text-muted-foreground">Running OCR on {fileName}…</p>
						<p className="text-xs text-muted-foreground">This may take 15–40 seconds</p>
					</>
				)}

				{dropState === "done" && (
					<>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							aria-hidden="true"
							className="h-6 w-6 text-primary"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							strokeWidth={2}
						>
							<path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
						</svg>
						<p className="text-sm font-medium text-primary">{fileName}</p>
						<p className="text-xs text-muted-foreground">
							{value.length.toLocaleString()} chars extracted · Click to replace
						</p>
					</>
				)}

				{dropState === "error" && (
					<>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							aria-hidden="true"
							className="h-6 w-6 text-destructive"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							strokeWidth={2}
						>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
							/>
						</svg>
						<p className="text-sm text-destructive">{extractError}</p>
						<p className="text-xs text-muted-foreground">Click to try another file</p>
					</>
				)}

				{(dropState === "idle" || dropState === "hover") && (
					<>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							aria-hidden="true"
							className={`h-8 w-8 transition-colors ${
								dropState === "hover" ? "text-primary" : "text-muted-foreground"
							}`}
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							strokeWidth={1.5}
						>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
							/>
						</svg>
						<p className="text-sm font-medium">
							{dropState === "hover"
								? "Release to upload"
								: "Drag your document here or click to browse"}
						</p>
						<p className="text-xs text-muted-foreground">
							{config.helperText || "PDF · Word · Excel · CSV · Images · TXT — Max 25 MB"}
						</p>
					</>
				)}
			</button>

			{value && !isLoading && (
				<button
					type="button"
					onClick={(e) => {
						e.stopPropagation();
						handleClear();
					}}
					className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
				>
					Clear and start over
				</button>
			)}

			{/* Only show the paste textarea when the user is typing, not when a file was loaded */}
			{source === "manual" && (
				<div className="space-y-1">
					<p className="text-xs text-muted-foreground">Or paste / type text directly:</p>
					<Textarea
						value={value}
						onChange={(e) => {
							setSource("manual");
							onChange(e.target.value);
							if (e.target.value && dropState === "idle") setDropState("done");
							if (!e.target.value) setDropState("idle");
						}}
						placeholder={config.placeholder}
						rows={config.rows || 14}
						className="resize-none font-mono text-xs"
					/>
				</div>
			)}
		</div>
	);
}

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
								<Image src={value} alt="Preview" fill unoptimized className="object-cover" />
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
											const ext = `.${f.name.split(".").pop()?.toLowerCase()}`;
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

		case "pdf-drop":
			return <PdfDropField config={config} value={value} onChange={onChange} />;

		default:
			return null;
	}
}
