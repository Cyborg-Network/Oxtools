import type { ToolDefinition } from "@/types";

export const apiValidator: ToolDefinition = {
	id: "api-validator",
	name: "API Schema Validator",
	description: "Validate API responses against schemas and flag issues",
	category: "data",
	icon: "Zap",
	status: "active",

	defaultModel: "deepseek-r1-0528",
	requiredFields: ["schema"],
	buildSystemPrompt: () =>
		`You are an API design expert. Analyze the provided API schema or endpoint definition and check for:

1. **Schema Compliance** - Valid JSON Schema / OpenAPI structure
2. **HTTP Standards** - Correct status codes, methods, and headers
3. **Security Issues** - Missing auth, exposed sensitive data, CORS problems
4. **Breaking Changes** - Fields that could break clients if changed
5. **Best Practices** - RESTful conventions, versioning, pagination

For each issue found, provide:
- 🔴 Breaking / 🟡 Warning / 🟢 Suggestion
- Description of the issue
- Recommended fix with code example

Use clean markdown with tables and code blocks.`,
	buildUserPrompt: ({ schema, response }) =>
		`Validate this API definition:\n\n\`\`\`json\n${schema}\n\`\`\`${response ? `\n\nActual response:\n\`\`\`json\n${response}\n\`\`\`` : ""}`,

	inputs: [
		{
			key: "schema",
			label: "API Schema or endpoint definition",
			type: "code",
			placeholder:
				'{\n  "endpoint": "/api/users",\n  "method": "GET",\n  "response": {\n    "users": [...]\n  }\n}',
			rows: 12,
		},
		{
			key: "response",
			label: "Actual API response (optional)",
			type: "code",
			placeholder: "Paste the actual JSON response to validate against...",
			rows: 6,
		},
	],
};
