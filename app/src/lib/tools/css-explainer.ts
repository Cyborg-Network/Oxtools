import type { ToolDefinition } from "@/types";

export const cssExplainer: ToolDefinition = {
	id: "css-explainer",
	name: "CSS Behavior Explainer",
	description:
		"Paste CSS that behaves unexpectedly and get a clear explanation of why, plus the correct fix.",
	category: "developer",
	icon: "Code2",
	status: "active",

	requiredFields: ["css"],
	defaultModel: "deepseek-v3.2",

	buildSystemPrompt: () =>
		`You are a CSS expert and browser rendering engine specialist. When given CSS code that behaves unexpectedly, you must:

1. **Explain the Behavior** - Why is the CSS behaving this way? Reference the CSS spec.
2. **Root Cause** - Identify the exact property, value, or interaction causing the issue.
3. **Visual Model** - Describe how the browser is interpreting the layout (box model, stacking context, flex/grid behavior).
4. **The Fix** - Provide the corrected CSS with inline comments.
5. **Pro Tip** - Share a best practice to avoid this class of issue.

Format output as clean markdown with code blocks.`,

	buildUserPrompt: ({ css, expected }) =>
		`**CSS CODE:**\n\`\`\`css\n${css}\n\`\`\`\n\n${expected ? `**EXPECTED BEHAVIOR:** ${expected}\n\n` : ""}Explain why this CSS behaves the way it does and how to fix it.`,

	inputs: [
		{
			key: "css",
			label: "CSS Code",
			type: "code",
			placeholder: `.container {\n  display: flex;\n  justify-content: center;\n  /* Why isn't this centering vertically? */\n}`,
			rows: 10,
		},
		{
			key: "expected",
			label: "Expected Behavior (optional)",
			type: "textarea",
			placeholder: "E.g. 'I expected the child to be centered vertically and horizontally'",
			rows: 2,
		},
	],
};
