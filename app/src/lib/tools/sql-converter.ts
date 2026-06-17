import type { ToolDefinition } from "@/types";

export const sqlConverter: ToolDefinition = {
	id: "sql-converter",
	name: "Natural Language to SQL",
	description: "Convert plain English to dialect-aware SQL queries",
	category: "data",
	icon: "Database",
	status: "active",

	defaultModel: "qwen-3-coder-30b",
	requiredFields: ["query"],
	buildSystemPrompt: ({ dialect, schema }) =>
		`You are an expert SQL developer. Convert natural language descriptions into optimized SQL queries.

Rules:
- Target dialect: ${dialect || "PostgreSQL"}
- Output the SQL query in a fenced code block
- Include comments explaining complex parts
- Optimize for performance (proper indexing hints, JOINs over subqueries)
- If a schema is provided, respect its table/column names exactly
${schema ? `\nAvailable schema:\n\`\`\`sql\n${schema}\n\`\`\`` : ""}

After the query, provide:
1. **Explanation** - What the query does step by step
2. **Performance Notes** - Any indexing or optimization suggestions
3. **Variations** - Alternative approaches if applicable`,
	buildUserPrompt: ({ query, dialect }) => `Convert this to ${dialect || "SQL"}:\n\n${query}`,

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
			],
		},
		{
			key: "schema",
			label: "Table schema (optional)",
			type: "code",
			placeholder:
				"CREATE TABLE users (\n  id SERIAL PRIMARY KEY,\n  email VARCHAR(255),\n  created_at TIMESTAMP\n);",
			rows: 6,
		},
	],
};
