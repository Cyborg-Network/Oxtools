import type { ToolDefinition } from "@/types";

export const sampleDatasetGenerator: ToolDefinition = {
  id: "sample-dataset",
  name: "Sample Dataset Generator",
  description:
    "Generate realistic test datasets in CSV, JSON, or SQL format for development and testing.",
  category: "data",
  icon: "Table2",
  status: "active",

  requiredFields: ["description"],
  defaultModel: "llama-3.3-70b",

  buildSystemPrompt: () =>
    `You are a data engineer who creates realistic sample datasets. Given a description of the data needed, generate a complete, realistic dataset. Rules:

1. Use realistic names, emails, dates, amounts - never "test123" or "foo@bar.com"
2. Include edge cases: nulls, boundary values, duplicates where appropriate
3. Generate at least 15-20 rows unless specified otherwise
4. Output in the requested format (CSV, JSON, or SQL INSERT statements)
5. Add a brief schema description at the top as a comment

Make the data feel like it came from a real production system.`,

  buildUserPrompt: ({ description, format, rows }) =>
    `Generate a sample dataset with these requirements:\n\n**DESCRIPTION:** ${description}\n**FORMAT:** ${format || "CSV"}\n**ROWS:** ${rows || "20"}\n\nMake it realistic and production-quality.`,

  inputs: [
    {
      key: "description",
      label: "Dataset Description",
      type: "textarea",
      placeholder: "E.g. 'E-commerce orders table with customer info, product names, quantities, prices, and order dates from Jan-Mar 2026'",
      rows: 4,
    },
    {
      key: "format",
      label: "Output Format",
      type: "select",
      options: [
        { value: "CSV", label: "CSV" },
        { value: "JSON", label: "JSON" },
        { value: "SQL", label: "SQL INSERT statements" },
        { value: "markdown-table", label: "Markdown table" },
      ],
    },
    {
      key: "rows",
      label: "Number of Rows",
      type: "text",
      placeholder: "20",
    },
  ],
};
