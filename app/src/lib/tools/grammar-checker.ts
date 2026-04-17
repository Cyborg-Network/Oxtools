import type { ToolDefinition } from "@/types";

export const grammarChecker: ToolDefinition = {
	id: "grammar-checker",
	name: "Grammar & Tone Checker",
	description: "Fix grammar and adjust tone for any text",
	category: "documentation",
	icon: "PenLine",
	status: "active",

	defaultModel: "llama-3.3-70b",
	requiredFields: ["text"],
	buildSystemPrompt: ({ tone }) =>
		`You are a professional editor and writing coach. Review and improve the provided text.

Target tone: ${tone || "professional"}

Provide:
1. **Corrected Version** - The full corrected text (ready to copy)
2. **Changes Made** - A numbered list of each change with brief explanation
3. **Tone Adjustments** - How the tone was adjusted
4. **Writing Tips** - 2-3 general writing tips based on common issues found

Format the corrected version clearly so it's easy to copy. Use markdown formatting.`,
	buildUserPrompt: ({ text, tone }) =>
		`Review and improve this text${tone ? ` (make it sound ${tone})` : ""}:\n\n${text}`,

	inputs: [
		{
			key: "text",
			label: "Paste your text",
			type: "textarea",
			placeholder: "Paste your email, documentation, article, or any text you want to improve...",
			rows: 8,
		},
		{
			key: "tone",
			label: "Target Tone",
			type: "select",
			options: [
				{ value: "professional", label: "Professional" },
				{ value: "casual", label: "Casual" },
				{ value: "technical", label: "Technical" },
				{ value: "friendly", label: "Friendly" },
				{ value: "formal", label: "Formal" },
				{ value: "concise", label: "Concise" },
			],
		},
	],
};
