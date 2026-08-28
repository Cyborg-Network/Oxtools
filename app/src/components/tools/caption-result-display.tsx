"use client";

import { Check, Copy } from "lucide-react";
import { useCallback, useState } from "react";

function VariationCopyButton({ text }: { text: string }) {
	const [copied, setCopied] = useState(false);
	const handleCopy = useCallback(async () => {
		await navigator.clipboard.writeText(text);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	}, [text]);

	return (
		<button
			type="button"
			onClick={handleCopy}
			className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors hover:bg-primary/10 hover:text-primary data-[copied=true]:text-green-500"
			data-copied={copied}
		>
			{copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
			{copied ? "Copied" : "Copy"}
		</button>
	);
}

function CaptionVariationDisplay({
	variations: rawVariations,
	title,
	platformName,
	lengthType,
}: {
	variations?: { text: string; chars: number; limit: number; title?: string }[];
	title?: string | null;
	platformName?: string;
	lengthType?: string;
}) {
	const [activeIdx, setActiveIdx] = useState(0);
	if (!rawVariations || rawVariations.length === 0) return null;

	const v = rawVariations[activeIdx];
	const varTitle = v.title || title;
	const copyText = varTitle ? `Title: ${varTitle}\n\nCaption: ${v.text}` : v.text;
	const charRatio = v.chars / v.limit;
	const barWidth = Math.min(charRatio * 100, 100);
	const barColor =
		charRatio > 1.0 ? "bg-red-500" : charRatio > 0.8 ? "bg-amber-500" : "bg-green-500";

	return (
		<div className="space-y-4">
			{platformName && (
				<div className="flex items-center justify-between">
					<h3 className="text-base font-semibold text-foreground">{platformName}</h3>
					<span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
						{lengthType === "short" ? "Short" : "Long"}
					</span>
				</div>
			)}

			<div className="flex gap-1.5">
				{rawVariations.map((v, i) => (
					<button
						key={v.text}
						type="button"
						onClick={() => setActiveIdx(i)}
						className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
							activeIdx === i
								? "bg-primary text-primary-foreground"
								: "bg-muted text-muted-foreground hover:bg-muted/80"
						}`}
					>
						Variation {i + 1}
					</button>
				))}
			</div>

			<div className="space-y-2">
				{varTitle && (
					<div className="rounded-lg border border-primary/20 bg-primary/[0.02] p-3">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-xs text-muted-foreground mb-0.5">Title {activeIdx + 1}</p>
								<p className="text-sm font-medium text-foreground">{varTitle}</p>
							</div>
							<VariationCopyButton text={varTitle} />
						</div>
					</div>
				)}

				<div className="rounded-lg border border-border bg-card p-4">
					<div className="flex items-start justify-between gap-4">
						<p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap flex-1 min-w-0">
							{v.text}
						</p>
						<VariationCopyButton text={copyText} />
					</div>
					<div className="mt-3 flex items-center gap-2">
						<div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
							<div
								className={`${barColor} h-full rounded-full transition-all`}
								style={{ width: `${barWidth}%` }}
							/>
						</div>
						<span className="text-xs tabular-nums text-muted-foreground shrink-0">
							{v.chars} / {v.limit}
						</span>
					</div>
				</div>
			</div>
		</div>
	);
}

export function CaptionResultDisplay({ result }: { result: string }) {
	let parsed: {
		variations?: { text: string; chars: number; limit: number; title?: string }[];
		title?: string | null;
		metadata?: { platform_name?: string; platform?: string; length_type?: string };
	} | null = null;

	try {
		const data = JSON.parse(result);
		if (data.variations || data.title) {
			parsed = data;
		}
	} catch {
		// not JSON, fall through to raw display
	}

	if (!parsed) {
		return <pre className="whitespace-pre-wrap text-sm">{result}</pre>;
	}

	return (
		<CaptionVariationDisplay
			variations={parsed.variations}
			title={parsed.title}
			platformName={parsed.metadata?.platform_name || parsed.metadata?.platform}
			lengthType={parsed.metadata?.length_type}
		/>
	);
}
