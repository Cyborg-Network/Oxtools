import type { ToolDefinition } from "@/types";

export const codeSecurityScanner: ToolDefinition = {
  id: "code-security-scanner",
  name: "Code Security Scanner",
  description: "Detect OWASP vulnerabilities and security issues in code",
  category: "developer",
  icon: "Shield",
  status: "active",

  requiredFields: ["code"],
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
3. **Location** - Where in the code
4. **Description** - What the issue is
5. **Fix** - Code example showing the secure version

Use markdown with clear headings, tables, and code blocks.${language ? ` The code is written in ${language}.` : ""}`,
  buildUserPrompt: ({ code, language }) =>
    `Perform a security audit on this code:\n\n\`\`\`${language || ""}\n${code}\n\`\`\``,

  inputs: [
    {
      key: "code",
      label: "Paste your code to scan",
      type: "code",
      placeholder: "// Paste your code here...",
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
        { value: "php", label: "PHP" },
        { value: "ruby", label: "Ruby" },
        { value: "csharp", label: "C#" },
      ],
    },
  ],
};
