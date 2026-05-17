import type { ToolDefinition } from "@/types";

export const captionGenerator: ToolDefinition = {
	id: "caption-generator",
	name: "Social Media Captions",
	description:
		"Describe your content and get platform-optimized captions with hashtags for Instagram, Twitter/X, LinkedIn, and more.",
	category: "content",
	icon: "PenTool",
	status: "active",
	tier: "tier2",
	requiredFields: ["prompt", "platform"],
	defaultModel: "kimi-k2.5",
	buildSystemPrompt: () => "",
	buildUserPrompt: () => "",

	inputs: [
		{
			key: "platform",
			label: "Platform",
			type: "select",
			options: [
				{ value: "youtube", label: "YouTube" },
				{ value: "youtube_shorts", label: "YouTube Shorts" },
				{ value: "tiktok", label: "TikTok" },
				{ value: "instagram", label: "Instagram" },
				{ value: "reddit", label: "Reddit" },
				{ value: "linkedin", label: "LinkedIn" },
				{ value: "x_twitter", label: "X (Twitter)" },
			],
		},
		{
			key: "prompt",
			label: "Caption Prompt",
			type: "textarea",
			rows: 4,
			placeholder:
				"E.g. 'We just launched our AI-powered developer tools platform. It has 22+ free tools for debugging, testing, and code generation.'",
		},
		{
			key: "image",
			label: "Image (optional)",
			type: "image",
		},
	],
};