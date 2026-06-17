import type { ToolDefinition } from "@/types";

const ENTERPRISE_ARCHITECTURE_PROMPT = `You are an expert enterprise architecture, workflow, and system topology designer.

Return exactly one JSON object and no markdown fences.

The JSON must follow this shape:
{
	"type": "enterpriseArchitecture",
	"title": "...",
	"layout_type": "pipeline | layered | hub_spoke | microservices_grid | system_context",
	"node_count": 0,
	"edge_count": 0,
	"fidelity_score": 0,
	"theme": "healthcare | cloud | fintech | ai | enterprise | cyber_security",
	"variant": "poster | infographic | system diagram | cloud architecture | workflow | technical architecture",
	"components": [{ "name": "...", "type": "...", "role": "...", "group": "..." }],
	"nodes": [{ "id": "...", "label": "...", "type": "...", "role": "...", "icon": "...", "importance": 1, "central": false }],
	"edges": [{ "from": "node-id", "to": "node-id", "label": "...", "style": "solid | dashed | curved | orthogonal" }],
	"connections": [{ "from": "node-id", "to": "node-id", "label": "..." }],
	"groups": [{ "id": "...", "label": "...", "nodeIds": ["node-id"] }]
}

Topology Rules:
- workflow/process/sequence => pipeline
- microservices/distributed/service mesh => microservices_grid
- agent/orchestrator/coordinator/hub => hub_spoke
- cloud/platform/frontend/backend/layers => layered
- context/external systems/partners => system_context

Do not output Mermaid. Do not output prose outside the JSON object.`;

export const architectureDiagram: ToolDefinition = {
	id: "architecture-diagram",
	name: "Architecture Diagram",
	description: "AI architecture diagram generator with Flux.1 Schnell image mode and SVG fallback",
	category: "design",
	icon: "GitFork",
	status: "active",
	tier: "tier1",
	timeoutMs: 60_000,

	defaultModel: "deepseek-r1-0528",
	requiredFields: ["description"],

	buildSystemPrompt: () => ENTERPRISE_ARCHITECTURE_PROMPT,

	buildUserPrompt: ({ description }) => description,

	inputs: [
		{
			key: "description",
			label: "Describe your system architecture",
			type: "textarea",
			placeholder:
				"A microservices e-commerce platform with user service, product catalog, shopping cart, payment processing via Stripe, and a notification service that sends emails and push notifications...",
			rows: 6,
		},
	],
};
