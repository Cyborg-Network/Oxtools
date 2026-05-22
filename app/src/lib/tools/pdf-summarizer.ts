import type { ToolDefinition } from "@/types";

export const pdfSummarizer: ToolDefinition = {
	id: "pdf-summarizer",
	name: "PDF / Document Summarizer",
	description:
		"Paste document text and get a structured executive summary with key findings, action items, and highlights.",
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
			label: "Document Text",
			type: "code",
			placeholder: "Paste the text content of your document here...",
			rows: 14,
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
