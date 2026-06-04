import type { ToolDefinition } from "@/types";

export const sqlConverter: ToolDefinition = {
	id: "sql-converter",
	name: "Natural Language to SQL",
	description:
		"Multi-agent pipeline: parses schema, classifies intent, generates validated SQL.",
	category: "data",
	icon: "Database",
	status: "active",
	outputFormat: "streaming-text",

	// Routes requests to services/python-tools/tools/sql-converter/tool.py
	tier: "tier2",

	requiredFields: [], // ← Custom page handles its own validation
	defaultModel: "qwen-3-coder-30b",
	buildSystemPrompt: () => "",
	buildUserPrompt: ({ query, dialect, schema, schemaFile, sandboxQuery }) =>
		JSON.stringify({ query, dialect, schema, schemaFile, sandboxQuery }),

	inputs: [], // ← Custom page renders its own inputs
};
