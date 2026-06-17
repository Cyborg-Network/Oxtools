export const AVAILABLE_MODELS = [
	{ id: "llama-3.3-70b", name: "Llama 3.3 70B", tier: "Premium", category: "general" },
	{ id: "deepseek-r1-0528", name: "DeepSeek R1", tier: "Premium", category: "reasoning" },
	{ id: "kimi-k2.5", name: "Kimi K2.5", tier: "Premium", category: "general" },
	{ id: "qwen-3-32b", name: "Qwen 3 32B", tier: "Premium", category: "general" },
	{ id: "deepseek-coder-33b", name: "DeepSeek Coder 33B", tier: "Pro", category: "coding" },
	{ id: "deepseek-r1-70b", name: "DeepSeek R1 70B", tier: "Pro", category: "reasoning" },
	{ id: "deepseek-v3.2", name: "DeepSeek V3.2", tier: "Free", category: "general" },
	{ id: "llama-3.2-3b", name: "Llama 3.2 3B", tier: "Free", category: "general" },
	{ id: "mistral-7b", name: "Mistral 7B", tier: "Free", category: "general" },
] as const;

export const DEFAULT_IMAGE_MODEL = "flux.1-schnell";

export type ModelId = (typeof AVAILABLE_MODELS)[number]["id"];

export function getDefaultModel(category?: "general" | "coding" | "reasoning"): string {
	switch (category) {
		case "coding":
			return "deepseek-coder-33b";
		case "reasoning":
			return "deepseek-r1-0528";
		default:
			return "llama-3.3-70b";
	}
}
