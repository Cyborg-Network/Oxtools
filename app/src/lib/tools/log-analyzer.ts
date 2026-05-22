import type { ToolDefinition } from "@/types";

export const logAnalyzer: ToolDefinition = {
	id: "log-analyzer",
	name: "System Log Analyzer",
	description:
		"Paste server logs and get instant root cause analysis, error patterns, and recommended fixes.",
	category: "devops",
	icon: "Terminal",
	status: "active",
	tier: "tier2",

	requiredFields: ["logs"],
	defaultModel: "deepseek-r1-0528",

	buildSystemPrompt: () => "",   // unused — tool.py / llm_client.py own the prompt
	buildUserPrompt: () => "",     // unused — tool.py builds the payload

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
		{
			key: "report_mode",
			label: "Report Mode",
			type: "select",
			options: [
				{
					value: "fix_only",
					label: "Fix Only — just tell me what to do right now",
				},
				{
					value: "detailed",
					label: "Full Report — root causes, timeline, patterns + fixes",
				},
			],
		},
	],
};