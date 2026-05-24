import type { ToolDefinition } from "@/types";

export const pdfSummarizer: ToolDefinition = {
	id: "pdf-summarizer",
	name: "PDF / Document Summarizer",
	description:
		"Drag a PDF document.",
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
			placeholder: "Paste text here...",
			rows: 14,
			accept: ".pdf,.txt,.md",
			maxSizeMb: 20,
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
