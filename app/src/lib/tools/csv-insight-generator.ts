import type { ToolDefinition } from "@/types";

export const csvInsightGenerator: ToolDefinition = {
	id: "csv-insight-generator",
	name: "CSV Insight Generator",
	description:
		"Paste CSV data and get a comprehensive analytical report with statistics, trends, anomalies, and actionable recommendations.",
	category: "data",
	icon: "BarChart3",
	status: "active",

	requiredFields: ["csvData"],
	defaultModel: "deepseek-r1-0528",

	buildSystemPrompt: () =>
		`You are a senior data analyst. Analyze the provided CSV data and write a structured markdown report covering:

1. **Dataset Overview** - number of rows, columns, data types
2. **Key Statistics** - mean, median, mode, min, max for numeric columns; unique counts for categorical
3. **Trends & Patterns** - time-based trends, correlations, distributions
4. **Anomalies & Outliers** - unusual values, missing data patterns
5. **Actionable Recommendations** - what to investigate, clean, or use for decision-making

Use tables and code blocks where appropriate. Be specific with numbers.`,

	buildUserPrompt: ({ csvData, context }) =>
		`${context ? `**CONTEXT:** ${context}\n\n` : ""}**CSV DATA:**\n\`\`\`csv\n${csvData}\n\`\`\`\n\nAnalyze this dataset thoroughly.`,

	inputs: [
		{
			key: "csvData",
			label: "CSV Data",
			type: "code",
			placeholder:
				"name,age,salary,department\nAlice,32,85000,Engineering\nBob,28,72000,Marketing\n...",
			rows: 12,
		},
		{
			key: "context",
			label: "Context (optional)",
			type: "textarea",
			placeholder: "E.g. 'This is Q2 sales data for our SaaS product'",
			rows: 2,
		},
	],
};
