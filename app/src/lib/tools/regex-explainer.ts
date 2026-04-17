import type { ToolDefinition } from "@/types";

export const regexExplainer: ToolDefinition = {
	id: "regex-explainer",
	name: "Regex Explainer",
	description: "Get plain-English explanations of regular expressions",
	category: "documentation",
	icon: "Regex",
	status: "active",

	defaultModel: "deepseek-v3.2",
	requiredFields: ["regex"],
	buildSystemPrompt: () =>
		`You are a regex expert. Given a regular expression, provide:

1. **Plain English Explanation** - What the regex matches, step by step
2. **Component Breakdown** - Each part of the regex explained in a table:
   | Component | Meaning |
   |-----------|---------|
   | \`^\`     | Start of string |
3. **Examples** - 3-5 strings that match and 3-5 that don't
4. **Common Pitfalls** - Edge cases this regex might miss
5. **Optimized Version** - If the regex can be simplified or improved

Use clean markdown formatting with code blocks and tables.`,
	buildUserPrompt: ({ regex }) => `Explain this regular expression:\n\n\`\`\`\n${regex}\n\`\`\``,

	inputs: [
		{
			key: "regex",
			label: "Paste your regular expression",
			type: "text",
			placeholder: "^(?=.*[A-Za-z])(?=.*\\d)[A-Za-z\\d]{8,}$",
		},
	],
};
