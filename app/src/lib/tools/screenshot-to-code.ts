import type { ToolDefinition } from "@/types";

/**
 * Screenshot to Code - TIER 2 TOOL
 *
 * This tool CANNOT run in Next.js because it needs:
 * - Python PIL for image compression
 * - Playwright + Chromium for headless HTML rendering
 * - Pixel-diff comparison between original and generated UI
 *
 * It runs as a Docker container on Azure, and the Next.js
 * API route proxies requests to it via the Traefik gateway.
 */
export const screenshotToCode: ToolDefinition = {
	id: "screenshot-to-code",
	name: "Screenshot to Code",
	description:
		"Upload a UI screenshot and get production-ready HTML + Tailwind CSS code with pixel-accuracy scoring.",
	category: "design",
	icon: "Camera",
	status: "active",

	// Tier 2: runs in the unified Python tool runner
	tier: "tier2",

	// For Tier 2 tools, these are still used for the UI form rendering
	// but the prompts are handled by the Python service, not Next.js
	requiredFields: ["image"],
	defaultModel: "kimi-k2.5",
	buildSystemPrompt: () => "",
	buildUserPrompt: () => "",

	inputs: [
		{
			key: "image",
			label: "UI Screenshot",
			type: "image",
			placeholder: "Select an image file...",
		},
	],
};
