import type { ToolDefinition } from "@/types";

export const codeSecurityScannerV2: ToolDefinition = {
	id: "code-security-scanner-v2",
	name: "Code Security Scanner (Agentic V2)",
	description: "Advanced multi-file security scanner: cross-file taint tracking, import chain analysis, obfuscation decoding, dependency CVE checks + LLM deep audit.",
	category: "developer",
	icon: "Shield",
	status: "active",
	tier: "tier2",

	requiredFields: [],  // Either code OR files — backend validates
	defaultModel: "deepseek-r1-0528",
	buildSystemPrompt: () => "",
	buildUserPrompt: () => "",

	inputs: [
		{
			key: "files",
			label: "Upload project files (or ZIP)",
			type: "files",
			accept: ".py,.js,.ts,.go,.java,.c,.cpp,.rb,.php,.rs,.zip,.txt,.json,.yml,.yaml,.toml,.cfg,.ini,.env,.lock",
			maxFiles: 50,
			maxSizeMb: 10,
			helperText: "Upload multiple files from your project or a ZIP archive. The scanner will analyze cross-file dependencies, imports, and taint flow. Languages are auto-detected from file extensions.",
		},
		{
			key: "code",
			label: "Or paste code directly",
			type: "code",
			placeholder: "// Paste your code here...\n// For multi-file scanning, use the file upload above instead.",
			rows: 10,
		},
	],
};
