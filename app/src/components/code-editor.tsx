"use client";

import { Badge, Textarea } from "@ansospace/ui";
import { Check, Copy } from "lucide-react";
import { useCallback, useRef, useState } from "react";

interface CodeEditorProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	language?: string;
	rows?: number;
	readOnly?: boolean;
}

export function CodeEditor({
	value,
	onChange,
	placeholder = "Enter your code here...",
	language,
	rows = 10,
	readOnly = false,
}: CodeEditorProps) {
	const [copied, setCopied] = useState(false);
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	const handleCopy = useCallback(async () => {
		if (!value) return;
		await navigator.clipboard.writeText(value);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	}, [value]);

	const lineCount = value ? value.split("\n").length : 0;

	return (
		<div className="group relative rounded-lg border border-input bg-background transition-colors focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20">
			{(language || value) && (
				<div className="flex items-center justify-between border-b border-border/50 px-3 py-1.5">
					<div className="flex items-center gap-2">
						{language && (
							<Badge variant="secondary" className="text-[10px] font-mono uppercase">
								{language}
							</Badge>
						)}
						{lineCount > 0 && (
							<span className="text-[10px] text-muted-foreground">
								{lineCount} {lineCount === 1 ? "line" : "lines"}
							</span>
						)}
					</div>
					{value && (
						<button
							type="button"
							onClick={handleCopy}
							className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
						>
							{copied ? (
								<>
									<Check className="h-3 w-3 text-green-500" />
									<span className="text-green-500">Copied</span>
								</>
							) : (
								<>
									<Copy className="h-3 w-3" />
									<span>Copy</span>
								</>
							)}
						</button>
					)}
				</div>
			)}
			<Textarea
				ref={textareaRef}
				value={value}
				onChange={(e) => onChange(e.target.value)}
				placeholder={placeholder}
				rows={rows}
				readOnly={readOnly}
				className="min-h-[120px] resize-y border-0 font-mono text-sm shadow-none focus-visible:ring-0"
				spellCheck={false}
			/>
		</div>
	);
}
