import type { ToolDefinition } from "@/types";

export const autoReadmeGeneratorTool: ToolDefinition = {
	id: "auto-readme-generator",
	name: "Auto README Generator",
	description:
		"Multi-agent pipeline that generates structured, validated READMEs.",
	category: "documentation",
	icon: "FileText",
	status: "active",
	
	// Tier 2: runs in the unified Python tool runner
	tier: "tier2",

	requiredFields: ["projectName", "projectDescription"],
	defaultModel: "llama-3.3-70b",
	buildSystemPrompt: () => "",
	buildUserPrompt: ({ projectName, projectDescription, techStack }) =>
		JSON.stringify({ projectName, projectDescription, techStack }),

	inputs: [
		{
			key: "projectName",
			label: "Project Name",
			type: "text",
			placeholder: "e.g. my-fastapi-app",
		},
		{
			key: "projectDescription",
			label: "Project Description",
			type: "textarea",
			placeholder: "What does your project do? Main features, target users.",
			rows: 5,
		},
		{
			key: "techStack",
			label: "Tech Stack (optional)",
			type: "text",
			placeholder: "e.g. Python, FastAPI, PostgreSQL, Docker",
		},
	],
};
