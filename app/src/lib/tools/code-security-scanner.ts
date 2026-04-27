import type { ToolDefinition } from "@/types";

export const codeSecurityScanner: ToolDefinition = {
	id: "code-security-scanner",
	name: "Code Security Scanner (V1)",
	description: "Single-pass LLM security audit — paste code or upload files for comparison with V2",
	category: "developer",
	icon: "Shield",
	status: "active",

	requiredFields: [],  // Either code or files
	defaultModel: "deepseek-r1-0528",
	buildSystemPrompt: ({ language }) =>
		`You are a senior application security engineer. Perform a deep security audit of the provided code.

Analyze for:
- **OWASP Top 10** vulnerabilities (injection, XSS, CSRF, etc.)
- **Authentication & Authorization** flaws
- **Data Exposure** risks (hardcoded secrets, PII leaks)
- **Input Validation** issues
- **Cryptographic** weaknesses
- **Dependency** risks

For each finding, provide:
1. **Severity** - 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low
2. **Vulnerability Type** - OWASP category
3. **Location** - Which file and where in the code
4. **Description** - What the issue is
5. **Fix** - Code example showing the secure version

Use markdown with clear headings, tables, and code blocks.${language ? ` The code is written in ${language}.` : ""}`,
	buildUserPrompt: ({ code, files }) => {
		const allCode = files?.trim() ? files : code;
		return `Perform a security audit on this code:\n\n\`\`\`\n${allCode}\n\`\`\``;
	},

	inputs: [
		{
			key: "files",
			label: "Upload project files (or ZIP)",
			type: "files",
			accept: ".py,.js,.ts,.go,.java,.c,.cpp,.rb,.php,.rs,.zip,.txt,.json,.yml,.yaml,.toml,.cfg,.ini,.env,.lock",
			maxFiles: 50,
			maxSizeMb: 10,
			helperText: "⚠️ V1 simply dumps all files into one LLM prompt — no cross-file analysis, no CVE lookup, no obfuscation decoding. Use V2 for real multi-file scanning.",
		},
		{
			key: "code",
			label: "Or paste code directly",
			type: "code",
			placeholder: "// Paste your code here...",
			rows: 14,
		},
	],
};
