import type { ToolDefinition } from "@/types";

export const deepResearch: ToolDefinition = {
	id: "deep-research",
	name: "Deep Research Agent",
	description:
		"Multi-agent AI research system that plans, searches, analyzes, verifies, and writes comprehensive research reports on any topic",
	category: "content",
	icon: "Search",
	status: "active",

	// Tier 2: runs in the unified Python tool runner
	tier: "tier2",

	defaultModel: "deepseek-r1-0528",
	requiredFields: ["query"],
	buildSystemPrompt: () => "",
	buildUserPrompt: ({ query }) => query,

	inputs: [
		{
			key: "query",
			label: "Research Topic",
			type: "textarea",
			placeholder:
				"Enter a research topic or question. Example: What is the current state of quantum computing and its potential impact on cryptography by 2030?",
			rows: 4,
		},
		{
			key: "depth",
			label: "Research Depth",
			type: "select",
			options: [
				{ value: "quick", label: "Quick (1 iteration, faster)" },
				{ value: "standard", label: "Standard (2 iterations, balanced)" },
				{ value: "deep", label: "Deep (3 iterations, most thorough)" },
			],
		},
	],
};
