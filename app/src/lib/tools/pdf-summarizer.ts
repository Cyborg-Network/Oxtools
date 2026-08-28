import type { ToolDefinition } from "@/types";

export const pdfSummarizer: ToolDefinition = {
	id: "pdf-summarizer",
	name: "PDF / Document Summarizer",
	description:
		"Upload any document — PDF, Word, Excel, CSV, or image — and get a structured executive summary with key findings, action items, and extracted data.",
	category: "documentation",
	icon: "FileSearch",
	status: "active",

	// Tier 2: runs in the unified Python tool runner
	tier: "tier2",

	requiredFields: ["documentText"],
	defaultModel: "deepseek-r1-0528",

	buildSystemPrompt: () => "",
	buildUserPrompt: () => "",

	inputs: [
		{
			key: "documentText",
			label: "Document",
			type: "pdf-drop",
			placeholder: "Drag a file here, or paste text directly...",
			rows: 14,
			accept: ".pdf,.txt,.md,.csv,.xlsx,.xls,.docx,.jpg,.jpeg,.png,.webp,.gif",
			maxSizeMb: 25,
			helperText: "PDF · Word · Excel · CSV · Images (JPG, PNG) · TXT · MD — Max 25 MB",
		},
		{
			key: "focus",
			label: "Focus Area (optional)",
			type: "textarea",
			placeholder: "E.g. 'Focus on financial projections and risks'",
			rows: 2,
		},
	],
};
