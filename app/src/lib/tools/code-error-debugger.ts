import type { ToolDefinition } from "@/types";

export const codeErrorDebugger: ToolDefinition = {
	id: "code-error-debugger",
	name: "Code Error Debugger",
	description: "Analyze error logs and stack traces to get actionable fixes",
	category: "developer",
	icon: "Bug",
	status: "active",

	defaultModel: "deepseek-r1-0528",
	requiredFields: ["errorLog"],
	buildSystemPrompt: () => `You are an expert software debugger. Analyze error logs and provide:
1. **Root Cause Analysis** - What exactly went wrong
2. **Step-by-Step Explanation** - Trace through the error
3. **Fix** - Actionable code fix with examples
4. **Prevention** - How to avoid this in the future

Use markdown formatting with code blocks. Be concise, clear, and practical.`,
	buildUserPrompt: ({ errorLog }) =>
		`Analyze this error log and help me fix it:\n\n\`\`\`\n${errorLog}\n\`\`\``,

	inputs: [
		{
			key: "errorLog",
			label: "Paste your error log or stack trace",
			type: "code",
			placeholder:
				"TypeError: Cannot read property 'map' of undefined\n    at Component.render (App.js:42:15)\n    at ...",
			rows: 12,
		},
	],
};
