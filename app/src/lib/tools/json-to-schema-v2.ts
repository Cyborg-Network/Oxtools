import type { ToolDefinition } from "@/types";

export const jsonToSchemaV2: ToolDefinition = {
	id: "json-to-schema-v2",
	name: "JSON to DB Schema (Agentic V2)",
	description:
		"Multi-agent schema generation: programmatic JSON parsing, LLM-powered schema design with iterative review, and deterministic compilation to PostgreSQL/MySQL/Prisma/Mongoose/Drizzle",
	category: "data",
	icon: "Database",
	status: "active",

	// Tier 2: runs in the unified Python tool runner
	tier: "tier2",

	defaultModel: "deepseek-r1-0528",
	requiredFields: ["json"],
	buildSystemPrompt: () => "",
	buildUserPrompt: ({ json }) => json,

	inputs: [
		{
			key: "json",
			label: "Paste your JSON data",
			type: "code",
			placeholder:
				'{\n  "users": [\n    {\n      "id": 1,\n      "name": "Alice",\n      "orders": [\n        { "id": 101, "total": 59.99 }\n      ]\n    }\n  ]\n}',
			rows: 12,
		},
		{
			key: "outputFormat",
			label: "Output Format",
			type: "select",
			options: [
				{ value: "postgresql", label: "PostgreSQL SQL" },
				{ value: "mysql", label: "MySQL SQL" },
				{ value: "prisma", label: "Prisma ORM" },
				{ value: "mongoose", label: "Mongoose (MongoDB)" },
				{ value: "drizzle", label: "Drizzle ORM" },
			],
		},
	],
};
