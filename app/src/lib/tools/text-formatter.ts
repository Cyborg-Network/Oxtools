import type { ToolDefinition } from "@/types";

export const textFormatter: ToolDefinition = {
  id: "text-formatter",
  name: "Unstructured Text Formatter",
  description:
    "Convert messy, unstructured text into clean markdown tables, CSV, JSON, or bullet lists.",
  category: "documentation",
  icon: "Type",
  status: "active",

  requiredFields: ["text"],
  defaultModel: "llama-3.3-70b",

  buildSystemPrompt: () =>
    `You are a text processing expert. Take unstructured, messy text and convert it into the requested clean format. Rules:

1. Infer column headers from the data patterns
2. Handle inconsistent delimiters (tabs, spaces, pipes, commas)
3. Clean up whitespace, fix obvious typos in structure
4. Preserve all data - never drop rows or columns
5. If the data has nested structures, flatten them appropriately

Output ONLY the formatted result with a brief note about what you inferred.`,

  buildUserPrompt: ({ text, outputFormat }) =>
    `**INPUT TEXT:**\n\`\`\`\n${text}\n\`\`\`\n\n**DESIRED OUTPUT FORMAT:** ${outputFormat || "Markdown table"}\n\nClean and reformat this data.`,

  inputs: [
    {
      key: "text",
      label: "Messy Text",
      type: "code",
      placeholder: `John Smith  john@email.com   Engineering   85000
Jane Doe    jane@email.com  Marketing     72000
Bob Wilson     bob@email.com      Sales   68000`,
      rows: 10,
    },
    {
      key: "outputFormat",
      label: "Output Format",
      type: "select",
      options: [
        { value: "Markdown table", label: "Markdown Table" },
        { value: "CSV", label: "CSV" },
        { value: "JSON array", label: "JSON Array" },
        { value: "YAML", label: "YAML" },
        { value: "Bullet list", label: "Bullet List" },
      ],
    },
  ],
};
