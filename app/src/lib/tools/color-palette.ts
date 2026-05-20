import type { ToolDefinition } from "@/types";

export const colorPalette: ToolDefinition = {
	id: "color-palette",
	name: "Color Palette Generator",
	description: "Extract all colors from an uploaded image.",

	category: "design",
	icon: "Palette",
	status: "active",
	tier: "tier2",

	requiredFields: ["image"],
	defaultModel: "kimi-k2.6",

	buildSystemPrompt: () => `
You are a color extraction specialist.

Extract all distinct colors from the provided image and return them as a JSON array.
- Identify all unique colors in the image
- Include both dominant and accent colors
- Return hex color codes

Return STRICT JSON format with extractedColors array only.`,

	buildUserPrompt: ({ image: _image }) => {
		return `
Extract all colors from the uploaded image.

Return JSON with format:
{
  "extractedColors": ["#xxxxxx", "#xxxxxx", "#xxxxxx", ...]
}

Include all distinct colors found in the image.
`;
	},

	inputs: [
		{
			key: "image",
			label: "Upload Image",
			type: "image",
			helperText: "Upload an image. All colors will be extracted and displayed.",
		},
	],
};
