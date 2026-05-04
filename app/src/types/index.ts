export type ToolCategory = "developer" | "data" | "documentation" | "design" | "devops" | "content";

export type ToolStatus = "active" | "coming-soon";

export interface InputFieldConfig {
	key: string;
	label: string;
	type: "code" | "textarea" | "select" | "text" | "image";
	placeholder?: string;
	rows?: number;
	options?: { value: string; label: string }[];
}

export interface ToolDefinition {
	/** Unique tool identifier (used in URL slugs) */
	id: string;
	/** Human-readable tool name */
	name: string;
	/** One-line description */
	description: string;
	/** Category for grouping in sidebar/dashboard */
	category: ToolCategory;
	/** Lucide icon name (e.g. "Bug", "Shield", "Code2") */
	icon: string;
	/** Active or placeholder */
	status: ToolStatus;

	// --- Tier config ---
	/**
	 * "tier1" = runs as LLM prompt inside Next.js (default)
	 * "tier2" = runs in the unified Python tool runner (services/python-tools/)
	 */
	tier?: "tier1" | "tier2";

	// --- API route config ---
	/** Fields required in the request body (besides `model`) */
	requiredFields: string[];
	/** Build the system prompt from the parsed body */
	buildSystemPrompt: (body: Record<string, string>) => string;
	/** Build the user prompt from the parsed body */
	buildUserPrompt: (body: Record<string, string>) => string;
	/** Default model when none is provided */
	defaultModel?: string;
	/** Optional custom timeout in milliseconds */
	timeoutMs?: number;

	// --- UI config ---
	/** Declarative form field definitions */
	inputs: InputFieldConfig[];
}

export interface CategoryInfo {
	name: string;
	icon: string;
	description: string;
}

export interface OxloResponse {
	choices: Array<{
		message: {
			content: string;
		};
	}>;
}
