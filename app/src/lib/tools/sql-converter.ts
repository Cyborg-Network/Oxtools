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

	requiredFields: ["query"],
	defaultModel: "qwen-3-coder-30b",
	buildSystemPrompt: () => "",
	buildUserPrompt: ({ query, dialect, schema, schemaFile, sandboxQuery }) =>
		JSON.stringify({ query, dialect, schema, schemaFile, sandboxQuery }),

	inputs: [
		{
			key: "query",
			label: "Describe what you want to query",
			type: "textarea",
			placeholder:
				"Get all users who signed up in the last 30 days, ordered by most recent first...",
			rows: 4,
		},
		{
			key: "dialect",
			label: "SQL Dialect",
			type: "select",
			options: [
				{ value: "postgresql", label: "PostgreSQL" },
				{ value: "mysql", label: "MySQL" },
				{ value: "sqlite", label: "SQLite" },
				{ value: "mssql", label: "SQL Server" },
				{ value: "bigquery", label: "BigQuery" },
			],
		},
		{
			key: "schemaFile",
			label: "Upload schema file (optional)",
			type: "files",
			accept: ".sql,.ddl,.txt",
			maxFiles: 1,
			maxSizeMb: 5,
			helperText:
				"Drop a .sql or .ddl file here. If provided, this overrides the text field below.",
		},
		{
			key: "schema",
			label: "Or paste schema manually (optional)",
			type: "code",
			placeholder:
				"CREATE TABLE users (\n  id SERIAL PRIMARY KEY,\n  email VARCHAR(255),\n  created_at TIMESTAMP\n);",
			rows: 6,
			helperText: "Ignored when a file is uploaded above.",
		},
		{
			key: "sandboxQuery",
			label: "Sandbox test query (optional)",
			type: "code",
			placeholder:
				"Paste the generated SELECT query here to test it against mock data created from your schema.",
			rows: 8,
			helperText:
				"If filled, the tool skips AI generation and runs this query safely against generated mock data.",
		},
	],
};
