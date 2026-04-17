import type { ToolDefinition } from "@/types";

export const architectureDiagram: ToolDefinition = {
	id: "architecture-diagram",
	name: "Architecture Diagram",
	description: "Generate Mermaid diagrams from text descriptions",
	category: "design",
	icon: "GitFork",
	status: "active",

	defaultModel: "deepseek-r1-0528",
	requiredFields: ["description"],
	buildSystemPrompt: ({ diagramType }) =>
		`You are an expert system architect. Given a system description, generate a Mermaid diagram that visualizes the architecture.

RULES:
- Output ONLY a single fenced code block with language "mermaid" containing valid Mermaid syntax
- Preferred diagram type: ${diagramType || "flowchart TD"}
- Use clear, descriptive labels for all nodes
- Group related components with subgraph blocks where appropriate
- Use proper Mermaid arrow types: --> for flow, -.-> for async, ==> for strong dependency
- After the mermaid block, provide a brief explanation of the architecture in markdown

IMPORTANT: The mermaid code block MUST be valid Mermaid syntax. Test mentally before outputting.
Do NOT use parentheses, brackets, or special characters inside node labels unless properly quoted.`,
	buildUserPrompt: ({ description }) =>
		`Generate a Mermaid architecture diagram for the following system:\n\n${description}`,

	inputs: [
		{
			key: "description",
			label: "Describe your system architecture",
			type: "textarea",
			placeholder:
				"A microservices e-commerce platform with user service, product catalog, shopping cart, payment processing via Stripe, and a notification service that sends emails and push notifications...",
			rows: 6,
		},
		{
			key: "diagramType",
			label: "Diagram Type",
			type: "select",
			options: [
				{ value: "flowchart TD", label: "Flowchart (Top-Down)" },
				{ value: "flowchart LR", label: "Flowchart (Left-Right)" },
				{ value: "sequenceDiagram", label: "Sequence Diagram" },
				{ value: "classDiagram", label: "Class Diagram" },
				{ value: "erDiagram", label: "ER Diagram" },
			],
		},
	],
};
