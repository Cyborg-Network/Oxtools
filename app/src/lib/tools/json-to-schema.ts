import type { ToolDefinition } from "@/types";

export const jsonToSchema: ToolDefinition = {
  id: "json-to-schema",
  name: "JSON to DB Schema",
  description: "Convert raw JSON data into database schemas",
  category: "data",
  icon: "Database",
  status: "active",

  defaultModel: "deepseek-v3.2",
  requiredFields: ["json"],
  buildSystemPrompt: ({ outputFormat }) =>
    `You are a database architect. Convert the provided JSON data into a proper database schema.

Output format: ${outputFormat || "SQL (PostgreSQL)"}

Requirements:
- Infer appropriate data types from the values
- Identify primary keys and foreign key relationships
- Add NOT NULL constraints where appropriate
- Include indexes for common query patterns
- Handle nested objects by normalizing into separate tables
- Handle arrays as one-to-many relationships

Output:
1. The complete schema definition
2. Brief explanation of design decisions
3. Example queries for common operations`,
  buildUserPrompt: ({ json, outputFormat }) =>
    `Convert this JSON to a ${outputFormat || "SQL"} database schema:\n\n\`\`\`json\n${json}\n\`\`\``,

  inputs: [
    {
      key: "json",
      label: "Paste your JSON data",
      type: "code",
      placeholder: '{\n  "users": [\n    {\n      "id": 1,\n      "name": "Alice",\n      "orders": [\n        { "id": 101, "total": 59.99 }\n      ]\n    }\n  ]\n}',
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
