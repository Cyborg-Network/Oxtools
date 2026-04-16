import type { ToolDefinition } from "@/types";

export const mockApiGenerator: ToolDefinition = {
  id: "mock-api-generator",
  name: "Mock API Generator",
  description: "Generate realistic API responses from schemas",
  category: "data",
  icon: "Wand2",
  status: "active",

  defaultModel: "qwen-3-coder-30b",
  requiredFields: ["schema"],
  buildSystemPrompt: ({ count }) =>
    `You are an expert at generating realistic mock data for API testing. Given a JSON schema or endpoint description, generate ${count || "5"} realistic mock records.

Rules:
- Use realistic names, emails, addresses (not "test123")
- Respect data types and constraints from the schema
- Include edge cases (null values, empty arrays, long strings)
- Output as a valid JSON array
- Add a brief explanation of the mock data strategy

Use markdown with a JSON code block for the data.`,
  buildUserPrompt: ({ schema, count }) =>
    `Generate ${count || "5"} mock records for this API schema:\n\n\`\`\`json\n${schema}\n\`\`\``,

  inputs: [
    {
      key: "schema",
      label: "JSON Schema or API structure",
      type: "code",
      placeholder: '{\n  "user": {\n    "id": "number",\n    "name": "string",\n    "email": "string",\n    "role": "admin | user"\n  }\n}',
      rows: 10,
    },
    {
      key: "count",
      label: "Number of records",
      type: "select",
      options: [
        { value: "3", label: "3 records" },
        { value: "5", label: "5 records" },
        { value: "10", label: "10 records" },
        { value: "20", label: "20 records" },
      ],
    },
  ],
};
