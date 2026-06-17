import type { ToolDefinition } from "@/types";

export const uiToCode: ToolDefinition = {
	id: "ui-to-code",
	name: "UI Description to Code",
	description:
		"Describe a UI component or screen in plain English and get production-ready React + Tailwind code.",
	category: "design",
	icon: "MonitorSmartphone",
	status: "active",

	requiredFields: ["uiDescription"],
	defaultModel: "qwen-3-coder-30b",

	buildSystemPrompt: ({ framework }) =>
		`You are a senior frontend developer. Convert UI descriptions into production-ready code. Rules:

1. You MUST output a single complete HTML file (starting with <!DOCTYPE html>) that can be previewed seamlessly in an iframe.
2. If the framework is ${framework || "React + Tailwind CSS"}, import the framework via CDN (e.g., React & ReactDOM via unpkg, use Babel standalone script type="text/babel", or Vue CDN).
3. Do NOT provide bare components. Assemble a fully working page.
4. Add Tailwind CSS via CDN script: <script src="https://cdn.tailwindcss.com"></script>.
5. Make it pixel-perfect, completely responsive, and visually stunning.`,

	buildUserPrompt: ({ uiDescription, framework, style }) =>
		`**UI DESCRIPTION:**\n${uiDescription}\n\n${style ? `**STYLE NOTES:** ${style}\n\n` : ""}**FRAMEWORK:** ${framework || "React + Tailwind CSS"}\n\nGenerate the complete component code.`,

	inputs: [
		{
			key: "uiDescription",
			label: "UI Description",
			type: "textarea",
			placeholder:
				"E.g. 'A pricing card with 3 tiers (Free, Pro, Enterprise). Each card shows the plan name, price, a list of features with check/cross icons, and a CTA button. The Pro tier should be highlighted as \"Most Popular\".'",
			rows: 6,
		},
		{
			key: "framework",
			label: "Framework",
			type: "select",
			options: [
				{ value: "React + Tailwind CSS", label: "React + Tailwind CSS" },
				{ value: "Next.js + Tailwind CSS", label: "Next.js + Tailwind CSS" },
				{ value: "Vue 3 + Tailwind CSS", label: "Vue 3 + Tailwind CSS" },
				{ value: "HTML + Vanilla CSS", label: "HTML + Vanilla CSS" },
				{ value: "Svelte", label: "Svelte" },
			],
		},
		{
			key: "style",
			label: "Style Notes (optional)",
			type: "textarea",
			placeholder: "E.g. 'Dark theme, glassmorphism, use Inter font'",
			rows: 2,
		},
	],
};
