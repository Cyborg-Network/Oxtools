import type { ToolDefinition } from "@/types";

export const unitTestGenerator: ToolDefinition = {
	id: "unit-test-generator",
	name: "Unit Test Generator",
	description: "Auto-generate unit test cases from existing code",
	category: "developer",
	icon: "FlaskConical",
	status: "active",

	requiredFields: ["code"],
	defaultModel: "qwen-3-coder-30b",
	buildSystemPrompt: ({ framework, language }) =>
		`You are a senior test engineer. Generate comprehensive unit tests for the provided code.

Requirements:
- Use ${framework || "the appropriate testing framework"} for ${language || "the detected language"}
- Cover happy paths, edge cases, and error scenarios
- Use descriptive test names that explain the behavior being tested
- Include setup/teardown if needed
- Add comments explaining complex assertions
- Aim for high code coverage

Output format:
1. Brief analysis of what needs testing
2. Complete test file with all tests
3. Coverage summary (what's tested, what's not)

Use markdown with proper code blocks.`,
	buildUserPrompt: ({ code, language, framework }) =>
		`Generate unit tests for this ${language || ""} code${framework ? ` using ${framework}` : ""}:\n\n\`\`\`${language || ""}\n${code}\n\`\`\``,

	inputs: [
		{
			key: "code",
			label: "Paste the code to generate tests for",
			type: "code",
			placeholder: "// Paste your function or class here...",
			rows: 14,
		},
		{
			key: "language",
			label: "Language",
			type: "select",
			options: [
				{ value: "", label: "Auto-detect" },
				{ value: "javascript", label: "JavaScript" },
				{ value: "typescript", label: "TypeScript" },
				{ value: "python", label: "Python" },
				{ value: "java", label: "Java" },
				{ value: "go", label: "Go" },
				{ value: "rust", label: "Rust" },
			],
		},
		{
			key: "framework",
			label: "Testing Framework",
			type: "select",
			options: [
				{ value: "", label: "Auto-detect" },
				{ value: "jest", label: "Jest" },
				{ value: "vitest", label: "Vitest" },
				{ value: "mocha", label: "Mocha" },
				{ value: "pytest", label: "Pytest" },
				{ value: "junit", label: "JUnit" },
				{ value: "go-test", label: "Go testing" },
			],
		},
	],
};
