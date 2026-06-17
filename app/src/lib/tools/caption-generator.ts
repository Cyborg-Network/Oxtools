import type { ToolDefinition } from "@/types";

export const captionGenerator: ToolDefinition = {
	id: "caption-generator",
	name: "Social Media Captions",
	description:
		"Describe your content and get platform-optimized captions with hashtags for Instagram, Twitter/X, LinkedIn, and more.",
	category: "content",
	icon: "PenTool",
	status: "active",

	requiredFields: ["contentDescription"],
	defaultModel: "llama-3.3-70b",

	buildSystemPrompt: ({ platform }) =>
		`You are a social media content strategist. Generate engaging, platform-optimized captions. Rules:

1. **Match the platform tone** - ${platform || "All platforms"} style and conventions
2. **Hook first** - Start with an attention-grabbing line
3. **Include CTAs** - ask questions, invite engagement
4. **Hashtags** - 5-10 relevant hashtags (platform-appropriate)
5. **Emojis** - Use strategically, not excessively
6. **Character limits** - Respect platform limits (Twitter: 280, Instagram caption: 2200)

Generate 3 caption variations: Professional, Casual, and Bold/Edgy.`,

	buildUserPrompt: ({ contentDescription, platform, tone, cta }) =>
		`**CONTENT:** ${contentDescription}\n\n**PLATFORM:** ${platform || "All platforms"}\n\n${tone ? `**TONE:** ${tone}\n` : ""}${cta ? `**CALL TO ACTION:** ${cta}\n` : ""}\n\nGenerate 3 caption variations.`,

	inputs: [
		{
			key: "contentDescription",
			label: "Content Description",
			type: "textarea",
			placeholder:
				"E.g. 'We just launched our AI-powered developer tools platform. It has 22+ free tools for debugging, testing, and code generation.'",
			rows: 4,
		},
		{
			key: "platform",
			label: "Platform",
			type: "select",
			options: [
				{ value: "All platforms", label: "All Platforms" },
				{ value: "Instagram", label: "Instagram" },
				{ value: "Twitter/X", label: "Twitter / X" },
				{ value: "LinkedIn", label: "LinkedIn" },
				{ value: "TikTok", label: "TikTok" },
				{ value: "YouTube", label: "YouTube (description)" },
			],
		},
		{
			key: "tone",
			label: "Tone (optional)",
			type: "text",
			placeholder: "E.g. 'Professional but approachable'",
		},
		{
			key: "cta",
			label: "Call to Action (optional)",
			type: "text",
			placeholder: "E.g. 'Sign up for the beta'",
		},
	],
};
