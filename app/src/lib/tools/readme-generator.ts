import type { ToolDefinition } from "@/types";

export const readmeGenerator: ToolDefinition = {
	id: "readme-generator",
	name: "Auto README Generator",
	description: "Generate professional README files from code",
	category: "documentation",
	icon: "BookOpen",
	status: "active",

	defaultModel: "llama-3.3-70b",
	requiredFields: ["projectInfo"],
	buildSystemPrompt: () =>
		`You are a technical writer specializing in developer documentation. Generate a professional, comprehensive README.md file.

Include these sections:
1. **Title & Badges** - Project name with relevant shields.io badges
2. **Description** - Clear 2-3 sentence overview
3. **Features** - Bullet-pointed feature list
4. **Tech Stack** - Technologies used
5. **Quick Start** - Installation and setup steps (exact commands)
6. **Usage** - Code examples showing how to use the project
7. **API Reference** - If applicable, document endpoints/methods
8. **Configuration** - Environment variables and config options
9. **Contributing** - How to contribute
10. **License** - License information

Output a complete, copy-pasteable markdown README. Use proper formatting, code blocks, and tables.`,
	buildUserPrompt: ({ projectInfo, techStack, features }) =>
		`Generate a README.md for this project:\n\n**Project Info:** ${projectInfo}\n${techStack ? `**Tech Stack:** ${techStack}\n` : ""}${features ? `**Features:** ${features}` : ""}`,

	inputs: [
		{
			key: "projectInfo",
			label: "Describe your project",
			type: "textarea",
			placeholder:
				"A real-time collaborative code editor built with WebSockets that supports multiple programming languages...",
			rows: 4,
		},
		{
			key: "techStack",
			label: "Tech stack (optional)",
			type: "text",
			placeholder: "React, Node.js, Socket.io, PostgreSQL, Docker",
		},
		{
			key: "features",
			label: "Key features (optional)",
			type: "textarea",
			placeholder:
				"- Real-time collaboration\n- Syntax highlighting for 50+ languages\n- File tree navigation",
			rows: 4,
		},
	],
};
