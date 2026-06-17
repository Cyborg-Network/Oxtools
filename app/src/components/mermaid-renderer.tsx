"use client";

import { Button } from "@ansospace/ui";
import { Download, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface MermaidRendererProps {
	chart: string;
}

export function MermaidRenderer({ chart }: MermaidRendererProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const [error, setError] = useState<string | null>(null);
	const [svg, setSvg] = useState<string>("");

	const renderChart = useCallback(async () => {
		if (!chart.trim()) return;
		try {
			setError(null);
			const mermaid = (await import("mermaid")).default;
			mermaid.initialize({
				startOnLoad: false,
				theme: "dark",
				securityLevel: "loose",
				flowchart: { useMaxWidth: true, htmlLabels: true, curve: "basis" },
			});
			const id = `mermaid-${Date.now()}`;
			const { svg: rendered } = await mermaid.render(id, chart.trim());
			setSvg(rendered);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to render diagram");
			setSvg("");
		}
	}, [chart]);

	useEffect(() => {
		renderChart();
	}, [renderChart]);

	const handleDownloadSvg = useCallback(() => {
		if (!svg) return;
		const blob = new Blob([svg], { type: "image/svg+xml" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `architecture-diagram-${Date.now()}.svg`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}, [svg]);

	if (error) {
		return (
			<div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
				<p className="mb-2 text-sm font-medium text-destructive">Diagram render error</p>
				<pre className="text-xs text-destructive/80 whitespace-pre-wrap">{error}</pre>
				<Button variant="outline" size="sm" onClick={renderChart} className="mt-3 gap-2">
					<RefreshCw className="h-3.5 w-3.5" /> Retry
				</Button>
			</div>
		);
	}

	if (!svg) {
		return (
			<div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
				Rendering diagram…
			</div>
		);
	}

	return (
		<div className="space-y-3">
			<div className="flex justify-end">
				<Button
					variant="outline"
					size="sm"
					onClick={handleDownloadSvg}
					className="gap-2 h-8 text-xs"
				>
					<Download className="h-3.5 w-3.5" /> Download SVG
				</Button>
			</div>
			<div
				ref={containerRef}
				className="overflow-auto rounded-lg border bg-zinc-950 p-6 dark:bg-zinc-900 [&_svg]:mx-auto [&_svg]:max-w-full"
				// biome-ignore lint/security/noDangerouslySetInnerHtml: Trusted SVG output from mermaid diagram generation
				dangerouslySetInnerHTML={{ __html: svg }}
			/>
		</div>
	);
}
