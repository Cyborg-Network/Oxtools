import type { ToolDefinition } from "@/types";

export const colorPalette: ToolDefinition = {
	id: "color-palette",
	name: "Color Palette Generator",
	description:
		"Describe a brand, mood, or use case and get a complete color palette with HEX codes, CSS variables, and UI role assignments.",
	category: "design",
	icon: "Palette",
	status: "active",

	requiredFields: ["description"],
	defaultModel: "kimi-k2.5",

	buildSystemPrompt: () =>
		`You are a professional UI/UX designer and color theorist. Generate a complete color palette based on the description. Output:

1. **Palette Overview** - 6-8 harmonious colors as HEX codes with descriptive names
2. **Color Roles** - assign each color a UI role (Primary, Secondary, Accent, Background, Surface, Text, Success, Error)
3. **Color Theory** - explain why these colors work together (complementary, analogous, triadic, etc.)
4. **CSS Variables** - provide a \`:root\` block with the full palette
5. **Tailwind Config** - provide the \`colors\` section for tailwind.config.js

6. **VISUAL PREVIEW** - You MUST include exactly one \`\`\`html code block at the end containing a standalone HTML page (starting with <!DOCTYPE html>) that visually showcases ONLY the color swatches.
   - Load Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
   - Display a grid of large rounded color cards. Each card shows the color as a filled background, plus the color name and HEX code as text overlay.
   - DO NOT recreate any application UI, navigation bar, sidebar, or tool interface. Just show the palette colors as beautiful swatch cards in a centered grid.
   - The page background should be neutral (white or dark gray) so the colors stand out.`,

	buildUserPrompt: ({ description, style, count }) =>
		`**DESCRIPTION:** ${description}\n\n${style ? `**STYLE:** ${style}\n` : ""}${count ? `**NUMBER OF COLORS:** ${count}\n` : ""}\n\nGenerate a complete, production-ready color palette.`,

	inputs: [
		{
			key: "description",
			label: "Brand / Mood Description",
			type: "textarea",
			placeholder:
				"E.g. 'A fintech startup targeting millennials. Should feel modern, trustworthy, but not boring. Think dark mode with vibrant accents.'",
			rows: 4,
		},
		{
			key: "style",
			label: "Style Preference",
			type: "select",
			options: [
				{ value: "modern-minimal", label: "Modern & Minimal" },
				{ value: "vibrant-playful", label: "Vibrant & Playful" },
				{ value: "corporate-professional", label: "Corporate & Professional" },
				{ value: "dark-luxe", label: "Dark & Luxurious" },
				{ value: "pastel-soft", label: "Pastel & Soft" },
				{ value: "nature-organic", label: "Nature & Organic" },
			],
		},
		{
			key: "count",
			label: "Number of Colors",
			type: "text",
			placeholder: "8",
		},
	],
};
