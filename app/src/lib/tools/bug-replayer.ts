import type { ToolDefinition } from "@/types";

export const bugReplayer: ToolDefinition = {
	id: "bug-replayer",
	name: "Bug Reproduction Replayer",
	description:
		"Describe a bug with partial failure data and get a full reproduction script with API calls, test cases, and debugging steps.",
	category: "devops",
	icon: "Bug",
	status: "active",

	requiredFields: ["bugDescription"],
	defaultModel: "deepseek-r1-0528",

	buildSystemPrompt: () =>
		`You are a QA automation engineer. Given a bug description with partial failure data, reconstruct:

1. **Bug Summary** - Clear title and one-line description
2. **Steps to Reproduce** - Numbered step-by-step reproduction guide
3. **API Calls** - cURL commands or fetch() calls to reproduce the issue
4. **Test Script** - A minimal test case (Jest/Vitest or Python pytest) that demonstrates the bug
5. **Expected vs Actual** - Clear comparison
6. **Debugging Checklist** - What to check first (logs, network, env vars, etc.)
7. **Possible Root Causes** - Ranked by likelihood

Output runnable code that someone can copy and execute immediately.`,

	buildUserPrompt: ({ bugDescription, errorOutput, environment }) =>
		`**BUG DESCRIPTION:**\n${bugDescription}\n\n${errorOutput ? `**ERROR OUTPUT:**\n\`\`\`\n${errorOutput}\n\`\`\`\n\n` : ""}${environment ? `**ENVIRONMENT:** ${environment}\n\n` : ""}Generate a full reproduction script and debugging guide.`,

	inputs: [
		{
			key: "bugDescription",
			label: "Bug Description",
			type: "textarea",
			placeholder:
				"E.g. 'The /api/users endpoint returns 500 when the email contains a + sign. Works fine with normal emails. Started after we upgraded the validation library.'",
			rows: 5,
		},
		{
			key: "errorOutput",
			label: "Error Output / Stack Trace",
			type: "code",
			placeholder: "Paste any error messages, stack traces, or HTTP responses...",
			rows: 8,
		},
		{
			key: "environment",
			label: "Environment (optional)",
			type: "text",
			placeholder: "E.g. 'Node.js 20, Express, PostgreSQL, deployed on AWS ECS'",
		},
	],
};
