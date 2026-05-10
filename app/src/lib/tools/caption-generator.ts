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
	requiredFields: ["prompt", "platform", "style"],
	defaultModel: "kimi-k2.5",
	buildSystemPrompt: () => "",
    buildUserPrompt: () => "",

	inputs: [
        { key: "prompt", label: "Prompt", type: "textarea", rows: 4, placeholder: "E.g. 'We just launched our AI-powered developer tools platform. It has 22+ free tools for debugging, testing, and code generation.'"},
        { key: "platform", label: "Platform", type: "select",
          options: [
            { value: "All platform", label: "All Platforms" },
			{ value: "Instagram", label: "Instagram" },
            { value: "X(Twitter)", label: "X (Twitter)" },
            { value: "Linkedin", label: "LinkedIn" },
            { value: "Youtube", label: "YouTube" },
            { value: "Tiktok", label: "TikTok" },
          ] },

        // { key: "style", label: "Style", type: "select",
        //   options: [
        //     { value: "professional", label: "Professional" },
        //     { value: "casual", label: "Casual" },
        //     { value: "bold", label: "Bold" },
        //   ],
        //   defaultValue: "professional" },
		  
        { key: "image", label: "Image (optional)", type: "image", }
    ],
};