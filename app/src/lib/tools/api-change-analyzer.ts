import type { ToolDefinition } from "@/types";

export const apiChangeAnalyzer: ToolDefinition = {
	id: "api-change-analyzer",
	name: "API Change Analyzer",
	description:
		"Compare old and new API schemas to instantly detect breaking changes, deprecations, and structural differences.",
	category: "data",
	icon: "GitFork",
	status: "active",

	requiredFields: ["oldSchema", "newSchema"],
	defaultModel: "deepseek-r1-0528",

	buildSystemPrompt: () =>
		`You are a Senior API Architect. Compare the provided old and new API schemas and produce a structured markdown report covering:

1. **Summary of Differences** - high-level overview
2. **Breaking Changes** - anything that would cause existing clients to fail
3. **Non-Breaking Changes** - additions, optional fields
4. **Deprecations** - fields/endpoints marked for removal
5. **Migration Guide** - steps for consumers to upgrade

Use tables where appropriate. Highlight breaking changes with ⚠️ emoji.`,

	buildUserPrompt: ({ oldSchema, newSchema }) =>
		`**OLD API SCHEMA:**\n\`\`\`\n${oldSchema}\n\`\`\`\n\n**NEW API SCHEMA:**\n\`\`\`\n${newSchema}\n\`\`\`\n\nAnalyze the differences between these two API versions.`,

	inputs: [
		{
			key: "oldSchema",
			label: "Old API Schema (v1)",
			type: "code",
			placeholder: "Paste the old API schema, OpenAPI spec, or endpoint definitions...",
			rows: 10,
		},
		{
			key: "newSchema",
			label: "New API Schema (v2)",
			type: "code",
			placeholder: "Paste the new API schema, OpenAPI spec, or endpoint definitions...",
			rows: 10,
		},
	],
};
