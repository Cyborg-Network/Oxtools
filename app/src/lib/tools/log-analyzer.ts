import type { ToolDefinition } from "@/types";

export const logAnalyzer: ToolDefinition = {
  id: "log-analyzer",
  name: "System Log Analyzer",
  description:
    "Paste server logs and get instant root cause analysis, error patterns, and recommended fixes.",
  category: "devops",
  icon: "Terminal",
  status: "active",

  requiredFields: ["logs"],
  defaultModel: "deepseek-r1-0528",

  buildSystemPrompt: () =>
    `You are a senior DevOps/SRE engineer analyzing system logs. Provide:

1. **Severity Assessment** - Critical / Warning / Info - how urgent is this?
2. **Error Summary** - List each unique error type with occurrence count
3. **Root Cause Analysis** - What is most likely causing these errors?
4. **Timeline** - When did the issue start? Is it escalating or stable?
5. **Pattern Detection** - Are errors correlated? Time-based patterns? Cascading failures?
6. **Recommended Fixes** - Specific, actionable steps to resolve each issue
7. **Prevention** - Configuration or monitoring changes to prevent recurrence

Format as structured markdown. Use tables for error summaries. Highlight critical items with ⚠️.`,

  buildUserPrompt: ({ logs, context }) =>
    `${context ? `**CONTEXT:** ${context}\n\n` : ""}**SYSTEM LOGS:**\n\`\`\`\n${logs}\n\`\`\`\n\nAnalyze these logs and identify issues.`,

  inputs: [
    {
      key: "logs",
      label: "System Logs",
      type: "code",
      placeholder: `2026-04-14 10:32:15 ERROR [app.main] Connection refused: Redis at 10.0.1.5:6379
2026-04-14 10:32:16 WARN  [app.cache] Falling back to in-memory cache
2026-04-14 10:32:17 ERROR [app.main] Connection refused: Redis at 10.0.1.5:6379
2026-04-14 10:32:45 ERROR [app.api] Timeout waiting for response: 30s exceeded`,
      rows: 14,
    },
    {
      key: "context",
      label: "Context (optional)",
      type: "textarea",
      placeholder: "E.g. 'This started after deploying v2.3.1 to production at 10:30 AM'",
      rows: 2,
    },
  ],
};
