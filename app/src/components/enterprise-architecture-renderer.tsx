"use client";

import { Button } from "@ansospace/ui";
import dagre from "dagre";
import {
	BarChart3,
	Bot,
	Boxes,
	Cloud,
	Cpu,
	CreditCard,
	Database,
	Download,
	FileText,
	GitBranch,
	Hospital,
	Layers3,
	LayoutGrid,
	Link2,
	Mail,
	MessageSquare,
	Mic,
	Radar,
	Server,
	ShieldCheck,
	Users,
	Workflow,
} from "lucide-react";
import * as React from "react";

type LayoutType = "pipeline" | "layered" | "hub_spoke" | "system_context" | "microservices_grid";
type ThemeKey = "healthcare" | "cloud" | "fintech" | "ai" | "enterprise" | "cyber_security";
type VariantKey =
	| "poster"
	| "infographic"
	| "system diagram"
	| "cloud architecture"
	| "workflow"
	| "technical architecture";

type EnterpriseNodeInput = {
	id?: unknown;
	name?: unknown;
	label?: unknown;
	title?: unknown;
	icon?: unknown;
	type?: unknown;
	role?: unknown;
	group?: unknown;
	bullets?: unknown;
	items?: unknown;
	details?: unknown;
	importance?: unknown;
	central?: unknown;
	layer?: unknown;
	note?: unknown;
};

type EnterpriseEdgeInput = {
	from?: unknown;
	to?: unknown;
	label?: unknown;
	style?: unknown;
	dashed?: unknown;
	feedback?: unknown;
	bidirectional?: unknown;
};

type EnterpriseGroupInput = {
	id?: unknown;
	label?: unknown;
	type?: unknown;
	nodeIds?: unknown;
	note?: unknown;
};

type EnterpriseTierInput = {
	name?: unknown;
	title?: unknown;
	group?: unknown;
	nodes?: unknown;
	items?: unknown;
	type?: unknown;
};

type EnterpriseGraphInput = {
	title?: unknown;
	name?: unknown;
	description?: unknown;
	prompt?: unknown;
	components?: EnterpriseNodeInput[];
	prompt_sections?: unknown;
	extracted_sections?: unknown;
	extracted_layers?: unknown;
	layout_type?: unknown;
	layoutType?: unknown;
	layout?: unknown;
	theme?: unknown;
	themeKey?: unknown;
	variant?: unknown;
	renderVariant?: unknown;
	tiers?: EnterpriseTierInput[];
	stages?: EnterpriseNodeInput[];
	nodes?: EnterpriseNodeInput[];
	edges?: EnterpriseEdgeInput[];
	connections?: EnterpriseEdgeInput[];
	groups?: EnterpriseGroupInput[];
};

type GraphNode = {
	id: string;
	label: string;
	icon?: string;
	type?: string;
	role?: string;
	group?: string;
	bullets?: string[];
	importance?: number;
	central?: boolean;
	layer?: string;
	note?: string;
	x?: number;
	y?: number;
	width?: number;
	height?: number;
};

type GraphEdge = {
	from: string;
	to: string;
	label?: string;
	style: "solid" | "dashed" | "orthogonal" | "curved";
	dashed?: boolean;
	feedback?: boolean;
	bidirectional?: boolean;
};

type GraphGroup = {
	id: string;
	label: string;
	nodeIds?: string[];
	type?: string;
	note?: string;
};

type PositionedNode = GraphNode & {
	x: number;
	y: number;
	width: number;
	height: number;
};

type PositionedEdge = GraphEdge & {
	path: string;
	labelX: number;
	labelY: number;
	labelWidth?: number;
	labelHeight?: number;
	strokeDasharray?: string;
	points?: Array<{ x: number; y: number }>;
};

type PositionedGroup = GraphGroup & {
	x: number;
	y: number;
	width: number;
	height: number;
};

type GraphData = {
	title: string;
	layoutType: LayoutType;
	theme: ThemeKey;
	variant: VariantKey;
	nodes: GraphNode[];
	edges: GraphEdge[];
	groups: GraphGroup[];
};

const ENTERPRISE_CANVAS_WIDTH = 1600;
const ENTERPRISE_CANVAS_HEIGHT = 900;

const THEME_STYLES = {
	healthcare: {
		shell: "#f8fdff",
		shellAccent: "#cffafe",
		text: "#0f172a",
		muted: "#475569",
		border: "#cbd5e1",
		panel: "#ffffff",
		panelSoft: "#f1f5f9",
		edge: "#0891b2",
		glow: "rgba(8, 145, 178, 0.18)",
	},
	cloud: {
		shell: "#f8fbff",
		shellAccent: "#dbeafe",
		text: "#0f172a",
		muted: "#475569",
		border: "#cbd5e1",
		panel: "#ffffff",
		panelSoft: "#eff6ff",
		edge: "#2563eb",
		glow: "rgba(37, 99, 235, 0.16)",
	},
	fintech: {
		shell: "#fffaf5",
		shellAccent: "#ffedd5",
		text: "#0f172a",
		muted: "#57534e",
		border: "#d6d3d1",
		panel: "#ffffff",
		panelSoft: "#fff7ed",
		edge: "#ea580c",
		glow: "rgba(234, 88, 12, 0.16)",
	},
	ai: {
		shell: "#faf8ff",
		shellAccent: "#ede9fe",
		text: "#0f172a",
		muted: "#475569",
		border: "#cbd5e1",
		panel: "#ffffff",
		panelSoft: "#f5f3ff",
		edge: "#7c3aed",
		glow: "rgba(124, 58, 237, 0.16)",
	},
	enterprise: {
		shell: "#f8fafc",
		shellAccent: "#e2e8f0",
		text: "#0f172a",
		muted: "#475569",
		border: "#cbd5e1",
		panel: "#ffffff",
		panelSoft: "#f1f5f9",
		edge: "#0f766e",
		glow: "rgba(15, 118, 110, 0.16)",
	},
	cyber_security: {
		shell: "#f8fbff",
		shellAccent: "#dbeafe",
		text: "#0f172a",
		muted: "#475569",
		border: "#cbd5e1",
		panel: "#ffffff",
		panelSoft: "#eff6ff",
		edge: "#1d4ed8",
		glow: "rgba(29, 78, 216, 0.16)",
	},
} satisfies Record<
	ThemeKey,
	{
		shell: string;
		shellAccent: string;
		text: string;
		muted: string;
		border: string;
		panel: string;
		panelSoft: string;
		edge: string;
		glow: string;
	}
>;

const VARIANT_STYLES = {
	poster: {
		density: 1.05,
		titleScale: "text-3xl md:text-4xl",
		radius: "28px",
		badge: "Poster",
	},
	infographic: {
		density: 1.15,
		titleScale: "text-2xl md:text-3xl",
		radius: "22px",
		badge: "Infographic",
	},
	"system diagram": {
		density: 1,
		titleScale: "text-2xl md:text-3xl",
		radius: "20px",
		badge: "System Diagram",
	},
	"cloud architecture": {
		density: 1.02,
		titleScale: "text-2xl md:text-3xl",
		radius: "24px",
		badge: "Cloud Architecture",
	},
	workflow: {
		density: 0.98,
		titleScale: "text-2xl md:text-3xl",
		radius: "20px",
		badge: "Workflow",
	},
	"technical architecture": {
		density: 1.08,
		titleScale: "text-xl md:text-2xl",
		radius: "18px",
		badge: "Technical Architecture",
	},
} satisfies Record<
	VariantKey,
	{
		density: number;
		titleScale: string;
		radius: string;
		badge: string;
	}
>;

function escapeSvgText(value: string): string {
	return value
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

type TextMeasureOptions = {
	fontSize?: number;
	fontWeight?: number;
	letterSpacing?: number;
};

let sharedMeasureCanvas: HTMLCanvasElement | null = null;

function measureTextWidth(text: string, options?: TextMeasureOptions): number {
	if (!text) return 0;
	const fontSize = options?.fontSize ?? 16;
	const fontWeight = options?.fontWeight ?? 600;
	const letterSpacing = options?.letterSpacing ?? 0;

	if (typeof document !== "undefined") {
		sharedMeasureCanvas = sharedMeasureCanvas || document.createElement("canvas");
		const context = sharedMeasureCanvas.getContext("2d");
		if (context) {
			context.font = `${fontWeight} ${fontSize}px Aptos, Segoe UI, sans-serif`;
			const measured = context.measureText(text).width;
			return measured + Math.max(0, text.length - 1) * letterSpacing;
		}
	}

	// Fallback estimate when canvas is unavailable.
	return text.length * fontSize * 0.56 + Math.max(0, text.length - 1) * letterSpacing;
}

function wrapSvgText(value: string, maxWidth: number, options?: TextMeasureOptions): string[] {
	const words = value.trim().split(/\s+/).filter(Boolean);
	if (words.length === 0) return [""];
	const lines: string[] = [];
	let current = "";

	for (const word of words) {
		const candidate = current ? `${current} ${word}` : word;
		if (measureTextWidth(candidate, options) <= maxWidth || !current) {
			current = candidate;
			continue;
		}
		lines.push(current);
		current = word;
	}
	if (current) lines.push(current);

	if (lines.length <= 1) return lines;

	// Balance line lengths to improve readability while preserving whole words.
	for (let i = 0; i < lines.length - 1; i++) {
		const currentWords = lines[i].split(/\s+/);
		if (currentWords.length <= 1) continue;
		const lastWord = currentWords[currentWords.length - 1];
		const currentCandidate = currentWords.slice(0, -1).join(" ");
		const nextCandidate = `${lastWord} ${lines[i + 1]}`;
		if (!currentCandidate) continue;

		const currentWidth = measureTextWidth(lines[i], options);
		const nextWidth = measureTextWidth(lines[i + 1], options);
		const balancedCurrentWidth = measureTextWidth(currentCandidate, options);
		const balancedNextWidth = measureTextWidth(nextCandidate, options);
		const beforeGap = Math.abs(currentWidth - nextWidth);
		const afterGap = Math.abs(balancedCurrentWidth - balancedNextWidth);

		if (afterGap < beforeGap && balancedNextWidth <= maxWidth) {
			lines[i] = currentCandidate;
			lines[i + 1] = nextCandidate;
		}
	}

	return lines;
}

function normalizeText(value: unknown): string {
	if (typeof value === "string") return value.trim();
	if (typeof value === "number" || typeof value === "boolean") return String(value);
	return "";
}

function cleanNodeLabel(raw: string, title?: string): string {
	const source = raw.trim();
	if (!source) return "";

	let label = source
		.replace(/^[\s,:;.-]+|[\s,:;.-]+$/g, "")
		.replace(/\b(create|generate|build|design|draw|make)\b/gi, " ")
		.replace(/\b(architecture|diagram|system)\b/gi, " ")
		.replace(/\s+/g, " ")
		.trim();

	label = label.replace(/^(for|of|the|a|an)\s+/i, "").trim();
	if (/\b(using|with|that|which|where)\b/i.test(label) && label.split(/\s+/).length > 3) {
		label = label.split(/\b(?:using|with|that|which|where|to)\b/i)[0].trim();
	}

	if (title) {
		const normalizedTitle = title
			.toLowerCase()
			.replace(/[^a-z0-9\s]/g, " ")
			.replace(/\s+/g, " ")
			.trim();
		const normalizedLabel = label
			.toLowerCase()
			.replace(/[^a-z0-9\s]/g, " ")
			.replace(/\s+/g, " ")
			.trim();
		if (
			normalizedLabel &&
			normalizedTitle.includes(normalizedLabel) &&
			normalizedLabel.length > 18
		) {
			const shortSegment = label.split(/[,;:.]/)[0]?.trim();
			if (shortSegment) label = shortSegment;
		}
	}

	if (!label) return source;
	return label
		.replace(/\s+/g, " ")
		.replace(/^[\s,:;.-]+|[\s,:;.-]+$/g, "")
		.trim();
}

function normalizeMeaningKey(value: string): string {
	return value
		.toLowerCase()
		.replace(/&/g, " and ")
		.replace(/[^a-z0-9\s]/g, " ")
		.replace(/\b(the|a|an)\b/g, " ")
		.replace(/\b(system|service|component|node|module|entity)\b/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

function isGenericArchitectureLabel(label?: unknown): boolean {
	if (typeof label !== "string") return false;
	const cleaned = label
		.toLowerCase()
		.replace(/[^a-z0-9\s]/g, " ")
		.replace(/\s+/g, " ")
		.trim();
	if (!cleaned) return true;
	const genericLabels = new Set([
		"create",
		"generate",
		"build",
		"draw",
		"make",
		"platform",
		"diagram",
		"architecture",
		"system",
		"enterprise architecture",
		"nodes",
		"node",
		"components",
		"component",
		"groups",
		"group",
		"debug",
		"metadata",
		"data",
		"response",
	]);
	return genericLabels.has(cleaned);
}

/**
 * Returns true if the label is a visual/layout requirement phrase rather than
 * a real system component. These must never become architecture nodes.
 *
 * Covers: layout types, visual quality terms, design instructions, topology names,
 * spacing/sizing directives, and imperative sentences.
 */
function isRequirementPhrase(label: string): boolean {
	if (!label) return false;
	const lower = label.toLowerCase().trim();

	// --- Explicit topology / layout-type names that describe the diagram, not a component ---
	const topologyNames =
		/^(hub[\s-]?spoke|hub[\s-]?and[\s-]?spoke|radial|star topology|pipeline|layered|microservices grid|system context|workflow diagram|flow diagram|architecture diagram|enterprise architecture|technical architecture|cloud architecture|network topology|topology|data flow|event flow|message flow)$/i;
	if (topologyNames.test(lower)) return true;

	// --- Visual / layout / design requirement keywords anywhere in the phrase ---
	const requirementKeywords =
		/\b(layout|style|styled|readable|readability|utilization|spacing|overlap|arrow|arrows|arrowhead|professional|clean|canvas|visual|design|balanced|alignment|align|padding|margin|font|color|colour|theme|render|rendering|display|presentation|format|formatted|formatting|aesthetic|aesthetics|quality|resolution|pixel|16:9|aspect ratio|whitespace|white space|grid spacing|column|row|layer spacing|node spacing|edge routing|routing|placement|position|positioned|centered|centred|symmetr|radial layout|circular layout|linear layout|horizontal layout|vertical layout|flow direction|left.right|top.down|full canvas|canvas utilization|viewport|clipping|cropping|off.screen|off screen|visible|visibility|bounding box|safe padding|scale uniformly|uniform scale)\b/i;
	if (requirementKeywords.test(lower)) return true;

	// --- Imperative/instructional sentence starters ---
	const imperativePatterns =
		/^(use|ensure|make|keep|avoid|add|show|display|place|position|arrange|distribute|spread|fit|fill|center|centre|align|balance|improve|fix|set|apply|enable|disable|include|exclude|render|draw|generate|create|produce|output|never|always|must|should)\b/i;
	if (imperativePatterns.test(lower)) return true;

	// --- Modal requirement verbs ---
	if (/\b(should|must|need|needs|want|wants|require|requires|required)\b/i.test(lower)) return true;

	// --- Numeric ratio / unit phrases like "16:9", "70%", "40px", "85%" ---
	if (/\d+\s*[:%]\s*\d*|\d+\s*px\b/.test(lower)) return true;

	// --- Phrases that are clearly describing diagram quality, not a system ---
	const qualityPhrases =
		/\b(clear labels?|clean arrows?|full canvas|balanced layout|professional style|enterprise style|modern style|clean design|no overlap|no clipping|no cropping|evenly spaced|equal spacing|equal angles?|minimum gap|node gap|collision avoidance|canvas fitting|viewport fitting|16:9 canvas|hub.spoke layout|hub.spoke architecture|radial placement|center dominant|center node|spoke placement)\b/i;
	if (qualityPhrases.test(lower)) return true;

	return false;
}

function isTitleLeakLabel(label: string, title?: string): boolean {
	if (!title) return false;
	const labelKey = normalizeMeaningKey(label);
	const titleKey = normalizeMeaningKey(title);
	return Boolean(
		labelKey &&
			titleKey &&
			(labelKey === titleKey ||
				(labelKey.length > 28 && titleKey.includes(labelKey)) ||
				(titleKey.length > 28 && labelKey.includes(titleKey)))
	);
}

function isPromptArtifactLabel(label?: unknown): boolean {
	if (typeof label !== "string") return false;
	const lower = label.toLowerCase();
	return (
		isGenericArchitectureLabel(label) ||
		isRequirementPhrase(label) ||
		/^(output|result|response|answer|artifact|generated|prompt)/.test(lower) ||
		/^(nodes|components|groups|debug|metadata)\b/i.test(label.trim()) ||
		lower.includes("this is") ||
		lower.includes("the following")
	);
}

function slug(input: string, fallback: string): string {
	if (!input) return fallback;
	return (
		input
			.toLowerCase()
			.trim()
			.replace(/[^\w\s-]/g, "")
			.replace(/[\s_]+/g, "-")
			.replace(/-+/g, "-")
			.replace(/^-|-$/g, "") || fallback
	);
}

function clamp(value: number, min: number, max: number): number {
	return Math.max(min, Math.min(max, value));
}

/** Stable numeric hash for consistent theming/accent selection from prompt text. */
function hashString(value: string): number {
	let hash = 0;
	for (let i = 0; i < value.length; i++) {
		hash = (hash << 5) - hash + value.charCodeAt(i);
		hash |= 0;
	}
	return Math.abs(hash);
}

function toStringList(value: unknown): string[] {
	if (Array.isArray(value)) {
		return value.map((item) => (typeof item === "string" ? item.trim() : "")).filter(Boolean);
	}
	if (typeof value === "string") {
		return value
			.split(",")
			.map((item) => item.trim())
			.filter(Boolean);
	}
	return [];
}

/**
 * Extracts only real system component names from free-form text.
 *
 * HARD RULE: If a "Components:" / "Services:" / "Nodes:" / "Layers:" / "Agents:" section
 * exists in the text, ONLY items from that section become nodes. No fallback, no guessing,
 * no title parsing, no requirement parsing. The section is the absolute source of truth.
 *
 * Fallback (no section found): strip requirement/instruction blocks line-by-line,
 * then parse bullet/comma lists, filtering every candidate through isRequirementPhrase.
 *
 * Logs both accepted components and rejected requirement phrases.
 */
function extractSemanticComponentsFromText(text: string): string[] {
	const normalized = text
		.replace(/\r/g, "\n")
		.replace(/["'`]/g, "")
		.trim();
	if (!normalized) return [];

	// ─── HARD SOURCE-OF-TRUTH: explicit component section ───────────────────────
	// Match "Components:\n- item\n- item" style blocks (any of the section keywords).
	// The section ends at a blank line OR another section header OR end of string.
	const componentSectionRe =
		/(?:^|\n)\s*(?:components?|services?|nodes?|layers?|agents?|systems?|modules?|apis?|databases?|infrastructure)\s*:\s*\n([\s\S]+?)(?=\n\s*\n|\n\s*(?:requirements?|goals?|notes?|instructions?|layout|style|design|visual|rendering|output|format|topology|diagram)\s*:|\s*$)/i;
	const componentSectionMatch = normalized.match(componentSectionRe);

	if (componentSectionMatch?.[1]) {
		const sectionText = componentSectionMatch[1];
		const components: string[] = [];
		const ignoredRequirements: string[] = [];
		const seen = new Set<string>();

		sectionText
			.split(/\n|,|;/)
			.map((part) =>
				part
					.replace(/^\s*[-*•]\s*/, "")
					.replace(/^\s*\d+[.)]\s*/, "")
					.replace(/\([^)]*\)/g, "")
					.trim()
			)
			.filter(Boolean)
			.forEach((part) => {
				const cleaned = cleanNodeLabel(part);
				const key = normalizeMeaningKey(cleaned);
				if (!cleaned || !key || seen.has(key)) return;
				if (isRequirementPhrase(cleaned) || isGenericArchitectureLabel(cleaned)) {
					ignoredRequirements.push(cleaned);
					return;
				}
				seen.add(key);
				components.push(cleaned);
			});

		console.info("[component extraction]", {
			source: "explicit-section",
			components,
			ignoredRequirements,
		});
		return components;
	}

	// ─── FALLBACK: no explicit section — strip requirement blocks, parse lists ───
	// Step 1: remove named requirement/instruction sections entirely
	const requirementSectionRe =
		/(?:^|\n)\s*(?:requirements?|goals?|notes?|instructions?|layout|style|design|visual|rendering|output format|format|topology|diagram style|visual requirements?)\s*:\s*\n[\s\S]+?(?=\n\s*\n|\n\s*\w[\w\s]*:\s*\n|$)/gi;

	// Step 2: filter individual lines that are pure requirement phrases
	const strippedText = normalized
		.replace(requirementSectionRe, "")
		.split("\n")
		.filter((line) => {
			const trimmed = line.replace(/^\s*[-*•\d.)]+\s*/, "").trim();
			if (!trimmed) return true; // keep blank lines (section separators)
			return !isRequirementPhrase(trimmed);
		})
		.join("\n")
		.replace(/\b(?:create|generate|build|draw|make)\b[^:\n]*:\s*/gi, "")
		.trim();

	const candidateRegions: string[] = [];
	const withMatch = strippedText.match(
		/\b(?:with|including|includes|containing|contains|has|consists of|composed of)\b\s*:?\s*([\s\S]+)/i
	);
	if (withMatch?.[1]) candidateRegions.push(withMatch[1]);
	if (/^\s*[-*•]/m.test(strippedText)) candidateRegions.push(strippedText);
	if (candidateRegions.length === 0) candidateRegions.push(strippedText);

	const components: string[] = [];
	const ignoredRequirements: string[] = [];
	const seen = new Set<string>();

	candidateRegions.forEach((region) => {
		const stripped = region
			.replace(
				/\b(?:as|in|for)\s+(?:a|an|the)?\s*(?:poster|diagram|architecture|system diagram).*$/gi,
				""
			)
			.replace(/\.$/, "");

		stripped
			.split(/\n|,|;|\s+\+\s+|\s+and\s+|\s*&\s*/i)
			.map((part) =>
				part
					.replace(/^\s*[-*•]\s*/, "")
					.replace(/^\s*\d+[.)]\s*/, "")
					.replace(/\([^)]*\)/g, "")
					.trim()
			)
			.filter(Boolean)
			.forEach((part) => {
				const cleaned = cleanNodeLabel(part);
				const key = normalizeMeaningKey(cleaned);
				if (!cleaned || cleaned.split(/\s+/).length > 5) return;
				if (isRequirementPhrase(cleaned) || isGenericArchitectureLabel(cleaned)) {
					if (cleaned) ignoredRequirements.push(cleaned);
					return;
				}
				if (!key || seen.has(key)) return;
				seen.add(key);
				components.push(cleaned);
			});
	});

	console.info("[component extraction]", {
		source: "fallback-parse",
		components,
		ignoredRequirements,
	});
	return components;
}

function normalizeComponentNode(
	component: EnterpriseNodeInput | string,
	index: number,
	title?: string
): GraphNode | null {
	const rawLabel =
		typeof component === "string"
			? component
			: normalizeText(component?.label) ||
				normalizeText(component?.title) ||
				normalizeText(component?.name);
	const label = cleanNodeLabel(rawLabel, title);
	if (!label || isPromptArtifactLabel(label) || isTitleLeakLabel(label, title)) return null;
	// Reject requirement phrases even when they come from structured component objects
	if (isRequirementPhrase(label)) return null;
	const id =
		typeof component === "object" && component
			? normalizeText(component.id) || slug(label, `component-${index + 1}`)
			: slug(label, `component-${index + 1}`);
	return {
		id,
		label,
		icon:
			typeof component === "object" && component
				? normalizeText(component.icon) || undefined
				: undefined,
		type:
			typeof component === "object" && component
				? normalizeText(component.type) || undefined
				: undefined,
		role:
			(typeof component === "object" && component
				? normalizeText(component.role) || undefined
				: undefined) || "inferred component",
		group:
			typeof component === "object" && component
				? normalizeText(component.group) || undefined
				: undefined,
		bullets:
			typeof component === "object" && component
				? toStringList(component.bullets || component.items || component.details)
				: [],
		importance:
			typeof component === "object" && component && typeof component.importance === "number"
				? component.importance
				: undefined,
		central: Boolean(typeof component === "object" && component ? component.central : false),
		layer:
			typeof component === "object" && component
				? normalizeText(component.layer) || undefined
				: undefined,
		note:
			typeof component === "object" && component
				? normalizeText(component.note) || undefined
				: undefined,
	};
}

function dedupeNodes(nodes: GraphNode[]): GraphNode[] {
	const seen = new Set<string>();
	return nodes.filter((node) => {
		const key = normalizeMeaningKey(node.label);
		if (!key || seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

function normalizeLayoutType(value: unknown, sourceText: string, nodeCount: number): LayoutType {
	const explicit = normalizeText(value)
		.toLowerCase()
		.replace(/[-\s]+/g, "_");
	const aliases: Record<string, LayoutType> = {
		pipeline: "pipeline",
		layered: "layered",
		hub_spoke: "hub_spoke",
		"hub spoke": "hub_spoke",
		system_context: "system_context",
		"system context": "system_context",
		microservices_grid: "microservices_grid",
		"microservices grid": "microservices_grid",
	};
	const text = sourceText.toLowerCase();
	if (/\borchestrator\b|\bcoordinator\b|\bagents?\b|\bhub\b/.test(text)) return "hub_spoke";
	if (aliases[explicit]) return aliases[explicit];

	if (/microservice|micro-services|service grid/.test(text)) return "microservices_grid";
	if (/context|ecosystem/.test(text)) return "system_context";
	if (/layer|stack|layered/.test(text)) return "layered";
	if (/workflow|process|pipeline|etl|flow/.test(text)) return "pipeline";
	return nodeCount > 6 ? "microservices_grid" : "pipeline";
}

function normalizeTheme(value: unknown, sourceText: string): ThemeKey {
	const explicit = normalizeText(value)
		.toLowerCase()
		.replace(/[-\s]+/g, "_");
	const aliasMap: Record<string, ThemeKey> = {
		healthcare: "healthcare",
		health: "healthcare",
		cloud: "cloud",
		fintech: "fintech",
		finance: "fintech",
		banking: "fintech",
		ai: "ai",
		enterprise: "enterprise",
		cybersecurity: "cyber_security",
		cyber_security: "cyber_security",
		security: "cyber_security",
	};
	if (aliasMap[explicit]) return aliasMap[explicit];

	const text = sourceText.toLowerCase();
	if (/hospital|health|clinic|patient|medical/.test(text)) return "healthcare";
	if (/payment|fintech|bank|billing|ledger|transaction|card|trading/.test(text)) return "fintech";
	if (/security|cyber|threat|auth|zero trust|incident|vulnerability/.test(text))
		return "cyber_security";
	if (/agent|llm|model|prompt|chat|copilot|assistant/.test(text)) return "ai";
	if (/cloud|kubernetes|infra|platform|deployment|terraform|aws|azure|gcp/.test(text))
		return "cloud";
	return "enterprise";
}

function normalizeVariant(value: unknown, sourceText: string, layoutType: LayoutType): VariantKey {
	const explicit = normalizeText(value).toLowerCase();
	const aliases: Record<string, VariantKey> = {
		poster: "poster",
		infographic: "infographic",
		"system diagram": "system diagram",
		"cloud architecture": "cloud architecture",
		workflow: "workflow",
		"technical architecture": "technical architecture",
	};
	if (aliases[explicit]) return aliases[explicit];

	const text = sourceText.toLowerCase();
	if (/workflow|process|pipeline/.test(text)) return "workflow";
	if (/cloud|platform|infrastructure/.test(text)) return "cloud architecture";
	if (/technical|service|api|system/.test(text)) return "technical architecture";
	if (layoutType === "hub_spoke" || layoutType === "system_context") return "system diagram";
	return "infographic";
}

function inferIconKey(node: { label: string; type?: string; role?: string }) {
	const key = `${node.label} ${node.type || ""} ${node.role || ""}`.toLowerCase();
	if (
		key.includes("database") ||
		key.includes("db") ||
		key.includes("warehouse") ||
		key.includes("storage")
	)
		return "database";
	if (
		key.includes("agent") ||
		key.includes("bot") ||
		key.includes("assistant") ||
		key.includes("orchestrator") ||
		key.includes("copilot")
	)
		return "bot";
	if (key.includes("cloud") || key.includes("platform") || key.includes("infra")) return "cloud";
	if (
		key.includes("security") ||
		key.includes("secure") ||
		key.includes("auth") ||
		key.includes("threat") ||
		key.includes("shield")
	)
		return "shield";
	if (key.includes("chat") || key.includes("message") || key.includes("slack")) return "message";
	if (key.includes("email") || key.includes("mail")) return "mail";
	if (key.includes("hospital") || key.includes("clinical") || key.includes("patient"))
		return "hospital";
	if (key.includes("payment") || key.includes("card") || key.includes("billing")) return "payment";
	if (key.includes("api") || key.includes("server") || key.includes("service")) return "server";
	if (key.includes("layer") || key.includes("stack")) return "layers";
	if (key.includes("workflow") || key.includes("process") || key.includes("pipeline"))
		return "workflow";
	if (key.includes("group") || key.includes("cluster") || key.includes("microservice"))
		return "boxes";
	if (key.includes("hub") || key.includes("context") || key.includes("orchestrator"))
		return "radar";
	if (key.includes("integration") || key.includes("external") || key.includes("connector"))
		return "link";
	if (key.includes("chart") || key.includes("dashboard") || key.includes("analytics"))
		return "chart";
	if (key.includes("user") || key.includes("customer") || key.includes("person")) return "users";
	if (key.includes("document") || key.includes("doc") || key.includes("contract")) return "file";
	if (key.includes("voice") || key.includes("mic")) return "mic";
	return "cpu";
}

function iconFromKey(key: string, className = "h-6 w-6") {
	switch (key) {
		case "database":
			return <Database className={className} />;
		case "bot":
			return <Bot className={className} />;
		case "cloud":
			return <Cloud className={className} />;
		case "shield":
			return <ShieldCheck className={className} />;
		case "message":
			return <MessageSquare className={className} />;
		case "mail":
			return <Mail className={className} />;
		case "hospital":
			return <Hospital className={className} />;
		case "payment":
			return <CreditCard className={className} />;
		case "server":
			return <Server className={className} />;
		case "layers":
			return <Layers3 className={className} />;
		case "workflow":
			return <Workflow className={className} />;
		case "boxes":
			return <Boxes className={className} />;
		case "radar":
			return <Radar className={className} />;
		case "link":
			return <Link2 className={className} />;
		case "chart":
			return <BarChart3 className={className} />;
		case "users":
			return <Users className={className} />;
		case "file":
			return <FileText className={className} />;
		case "mic":
			return <Mic className={className} />;
		case "branch":
			return <GitBranch className={className} />;
		case "grid":
			return <LayoutGrid className={className} />;
		default:
			return <Cpu className={className} />;
	}
}

function iconForNode(node: GraphNode) {
	return iconFromKey(node.icon || inferIconKey(node), "h-6 w-6");
}

function buildNodeList(data: EnterpriseGraphInput, title: string, sourceText: string) {
	// Helper to log and return final node list
	const finalize = (nodes: GraphNode[], source: string): GraphNode[] => {
		const rejectedRequirementNodes = nodes
			.filter((n) => isRequirementPhrase(n.label))
			.map((n) => n.label);
		const clean = dedupeNodes(nodes.filter((n) => !isRequirementPhrase(n.label)));
		console.info("[requirement filtering]", {
			source,
			accepted: clean.map((n) => n.label),
			rejectedRequirementNodes,
		});
		return clean;
	};

	const componentNodes = Array.isArray(data?.components)
		? data.components
				.map((component, index) => normalizeComponentNode(component, index, title))
				.filter((node): node is GraphNode => Boolean(node))
		: [];
	if (componentNodes.length > 0) return finalize(componentNodes, "components");

	const tiers = Array.isArray(data?.tiers) ? data.tiers : [];
	if (tiers.length > 0) {
		const tierNodes = tiers
			.flatMap((tier, tierIndex) => {
				const tierName =
					normalizeText(tier?.name) || normalizeText(tier?.title) || `Tier ${tierIndex + 1}`;
				const tierGroup = normalizeText(tier?.group) || tierName;
				const tierItems = Array.isArray(tier?.nodes)
					? tier.nodes
					: Array.isArray(tier?.items)
						? tier.items
						: [];
				const nodesForTier = tierItems
					.map((item, nodeIndex) => {
						const itemLabel =
							typeof item === "string"
								? item
								: normalizeText(item?.label) ||
									normalizeText(item?.title) ||
									`Node ${nodeIndex + 1}`;
						if (isPromptArtifactLabel(itemLabel)) return null;
						const node: GraphNode = {
							id:
								normalizeText(item && typeof item === "object" ? item.id : undefined) ||
								slug(`${tierName}-${itemLabel}`, `node-${tierIndex + 1}-${nodeIndex + 1}`),
							label: itemLabel,
							icon:
								normalizeText(item && typeof item === "object" ? item.icon : undefined) ||
								undefined,
							type:
								normalizeText(item && typeof item === "object" ? item.type : undefined) ||
								normalizeText(tier?.type) ||
								undefined,
							role:
								normalizeText(item && typeof item === "object" ? item.role : undefined) ||
								"component",
							group: isPromptArtifactLabel(tierGroup) ? undefined : tierGroup,
							bullets: toStringList(
								item && typeof item === "object" ? item.bullets || item.items || item.details : []
							),
							importance:
								typeof item === "object" && item && typeof item.importance === "number"
									? item.importance
									: 1,
							central: Boolean(item && typeof item === "object" ? item.central : false),
							layer: tierName,
							note:
								normalizeText(item && typeof item === "object" ? item.note : undefined) ||
								undefined,
						};
						return node;
					})
					.filter((node): node is GraphNode => Boolean(node));

				if (
					nodesForTier.length === 0 &&
					!isPromptArtifactLabel(tierName) &&
					!isTitleLeakLabel(tierName, title)
				) {
					nodesForTier.push({
						id: slug(tierName, `tier-${tierIndex + 1}`),
						label: tierName,
						icon: inferIconKey({ label: tierName }),
						type: normalizeText(tier?.type) || undefined,
						role: normalizeText(tier?.type) || "layer",
						group: isPromptArtifactLabel(tierGroup) ? undefined : tierGroup,
						bullets: [],
						importance: 2,
						central: false,
						layer: tierName,
						note: undefined,
					});
				}

				return nodesForTier;
			})
			.filter(
				(node) =>
					node.label && !isPromptArtifactLabel(node.label) && !isTitleLeakLabel(node.label, title)
			);
		const inferredComponents = extractSemanticComponentsFromText(sourceText);
		if (
			inferredComponents.length > 1 &&
			tierNodes.some((node) => isTitleLeakLabel(node.label, title))
		) {
			return finalize(
				inferredComponents
					.map((component, index) => normalizeComponentNode(component, index, title))
					.filter((node): node is GraphNode => Boolean(node)),
				"inferred-from-tiers"
			);
		}
		return finalize(tierNodes, "tiers");
	}

	const nodes: GraphNode[] = Array.isArray(data?.nodes)
		? data.nodes
				.map((node: EnterpriseNodeInput, index: number) => ({
					id:
						normalizeText(node?.id) ||
						slug(normalizeText(node?.label) || `node-${index + 1}`, `node-${index + 1}`),
					label: normalizeText(node?.label) || normalizeText(node?.title) || `Node ${index + 1}`,
					icon: normalizeText(node?.icon) || undefined,
					type: normalizeText(node?.type) || undefined,
					role: normalizeText(node?.role) || undefined,
					group: normalizeText(node?.group) || undefined,
					bullets: toStringList(node?.bullets || node?.items || node?.details),
					importance: typeof node?.importance === "number" ? node.importance : undefined,
					central: Boolean(node?.central),
					layer: normalizeText(node?.layer) || undefined,
					note: normalizeText(node?.note) || undefined,
				}))
				.filter(
					(node) =>
						node.label &&
						!isPromptArtifactLabel(node.label) &&
						!isTitleLeakLabel(node.label, title) &&
						!isRequirementPhrase(node.label)
				)
		: [];

	const inferredComponents = extractSemanticComponentsFromText(sourceText);
	if (inferredComponents.length > 1) {
		const inferredNodes = inferredComponents
			.map((component, index) => normalizeComponentNode(component, index, title))
			.filter((node): node is GraphNode => Boolean(node));
		const nodeKeys = new Set(nodes.map((node) => normalizeMeaningKey(node.label)));
		const missingInferred = inferredNodes.filter(
			(node) => !nodeKeys.has(normalizeMeaningKey(node.label))
		);
		const hasTitleLeak = nodes.some((node) => isTitleLeakLabel(node.label, title));
		if (nodes.length === 0 || hasTitleLeak || missingInferred.length > 0)
			return finalize(inferredNodes, "inferred-from-text");
	}

	if (nodes.length > 0) return finalize(nodes, "data-nodes");

	const stages = Array.isArray(data?.stages) ? data.stages : [];
	const stageNodes = stages
		.map((stage: EnterpriseNodeInput, index: number) => ({
			id:
				normalizeText(stage?.id) ||
				slug(normalizeText(stage?.title) || `stage-${index + 1}`, `stage-${index + 1}`),
			label: normalizeText(stage?.title) || `Stage ${index + 1}`,
			icon: normalizeText(stage?.icon) || undefined,
			type: normalizeText(stage?.type) || undefined,
			role: normalizeText(stage?.role) || undefined,
			group: normalizeText(stage?.group) || undefined,
			bullets: toStringList(stage?.items || stage?.bullets || stage?.details),
			importance: typeof stage?.importance === "number" ? stage.importance : undefined,
			central: Boolean(stage?.central),
			layer: normalizeText(stage?.layer) || undefined,
			note: normalizeText(stage?.note) || undefined,
		}))
		.filter(
			(node) =>
				node.label &&
				!isPromptArtifactLabel(node.label) &&
				!isTitleLeakLabel(node.label, title) &&
				!isRequirementPhrase(node.label)
		);
	return finalize(stageNodes, "stages");
}

function buildEdges(data: EnterpriseGraphInput, nodes: GraphNode[], layoutType: LayoutType) {
	const nodeIds = new Set(nodes.map((node) => node.id));
	const centralNode =
		nodes.find((node) => /\borchestrator\b/i.test(node.label)) ||
		nodes.find((node) => node.central) ||
		nodes.find((node) => /\b(hub|coordinator)\b/i.test(`${node.label} ${node.role || ""}`)) ||
		(layoutType === "hub_spoke" ? nodes[0] : undefined);
	if (
		(layoutType === "hub_spoke" || centralNode?.label.match(/\borchestrator\b/i)) &&
		centralNode
	) {
		return nodes
			.filter((node) => node.id !== centralNode.id)
			.map((node) => ({
				from: centralNode.id,
				to: node.id,
				style: "curved" as const,
			}));
	}

	const explicitEdges: GraphEdge[] = Array.isArray(data?.edges)
		? (data.edges
				.map((edge: EnterpriseEdgeInput) => ({
					from: normalizeText(edge?.from),
					to: normalizeText(edge?.to),
					label: normalizeText(edge?.label) || undefined,
					style: (normalizeText(edge?.style) === "dashed"
						? "dashed"
						: normalizeText(edge?.style) === "orthogonal"
							? "orthogonal"
							: normalizeText(edge?.style) === "curved"
								? "curved"
								: "solid") as "solid" | "dashed" | "orthogonal" | "curved",
					dashed: Boolean(edge?.dashed),
					feedback: Boolean(edge?.feedback),
					bidirectional: Boolean(edge?.bidirectional),
				}))
				.filter((edge) => edge.from && edge.to)
				.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to)) as GraphEdge[])
		: [];

	if (explicitEdges.length > 0) return explicitEdges;

	const connections: GraphEdge[] = Array.isArray(data?.connections)
		? (data.connections
				.map((connection: EnterpriseEdgeInput) => ({
					from: normalizeText(connection?.from),
					to: normalizeText(connection?.to),
					label: normalizeText(connection?.label) || undefined,
					style: (normalizeText(connection?.style) === "dashed"
						? "dashed"
						: normalizeText(connection?.style) === "orthogonal"
							? "orthogonal"
							: normalizeText(connection?.style) === "curved"
								? "curved"
								: "solid") as "solid" | "dashed" | "orthogonal" | "curved",
					dashed: Boolean(connection?.dashed),
					feedback: Boolean(connection?.feedback),
					bidirectional: Boolean(connection?.bidirectional),
				}))
				.filter((edge) => edge.from && edge.to)
				.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to)) as GraphEdge[])
		: [];

	if (connections.length > 0) return connections;

	if (nodes.length <= 1) return [];

	return nodes.slice(0, -1).map((node, index) => ({
		from: node.id,
		to: nodes[index + 1].id,
		style: (layoutType === "layered" ? "orthogonal" : "solid") as GraphEdge["style"],
	}));
}

function buildGroups(data: EnterpriseGraphInput, nodes: GraphNode[]) {
	const providedGroups: GraphGroup[] = Array.isArray(data?.groups)
		? data.groups
				.map((group: EnterpriseGroupInput, index: number) => ({
					id:
						normalizeText(group?.id) ||
						slug(normalizeText(group?.label) || `group-${index + 1}`, `group-${index + 1}`),
					label: normalizeText(group?.label) || `Group ${index + 1}`,
					nodeIds: Array.isArray(group?.nodeIds)
						? group.nodeIds.map((value: unknown) => normalizeText(value)).filter(Boolean)
						: undefined,
					type: normalizeText(group?.type) || undefined,
					note: normalizeText(group?.note) || undefined,
				}))
				.filter((group) => group.id && group.label && !isPromptArtifactLabel(group.label))
		: [];

	if (providedGroups.length > 0) return providedGroups;

	const broadGroupKeys = new Set([
		"default",
		"component",
		"stage",
		"node",
		"system",
		"process",
		"architecture",
		"general",
	]);
	const grouped = new Map<string, string[]>();
	nodes.forEach((node) => {
		const groupId = node.group || node.layer || node.role || node.type || "default";
		if (broadGroupKeys.has(groupId.toLowerCase()) || isPromptArtifactLabel(groupId)) return;
		const bucket = grouped.get(groupId) || [];
		bucket.push(node.id);
		grouped.set(groupId, bucket);
	});

	return Array.from(grouped.entries())
		.filter(([, nodeIds]) => nodeIds.length > 1 && nodeIds.length < nodes.length)
		.map(([groupId, nodeIds]) => ({
			id: slug(groupId, groupId),
			label: groupId === "default" ? "Architecture" : groupId,
			nodeIds,
			type: groupId,
		}));
}

function buildGraph(data: EnterpriseGraphInput): GraphData {
	const title =
		normalizeText(data?.title) || normalizeText(data?.name) || "Enterprise Architecture";
	const combinedText = [
		title,
		normalizeText(data?.description),
		normalizeText(data?.prompt),
		toStringList(data?.prompt_sections).join(" "),
		toStringList(data?.extracted_sections).join(" "),
		toStringList(data?.extracted_layers).join(" "),
		JSON.stringify(data?.components || []),
		JSON.stringify(data?.tiers || []),
		JSON.stringify(data?.stages || []),
		JSON.stringify(data?.nodes || []),
	].join(" ");
	const nodes = buildNodeList(data, title, combinedText);
	const layoutType = normalizeLayoutType(
		data?.layout_type || data?.layoutType || data?.layout,
		combinedText,
		nodes.length
	);
	const theme = normalizeTheme(data?.theme || data?.themeKey, combinedText);
	const variant = normalizeVariant(data?.variant || data?.renderVariant, combinedText, layoutType);
	const groups = buildGroups(data, nodes);
	const edges = buildEdges(data, nodes, layoutType);

	const seededText = `${combinedText} ${layoutType} ${theme} ${variant}`;
	const enrichedNodes = nodes.map((node, index) => ({
		...node,
		label: cleanNodeLabel(node.label, title) || node.label,
		importance:
			node.importance ??
			(node.central
				? 3
				: /central|platform|core|orchestrator|hub/.test(
							`${node.label} ${node.role || ""} ${node.type || ""}`.toLowerCase()
						)
					? 3
					: /database|store|infra|security|api|service/.test(
								`${node.label} ${node.role || ""} ${node.type || ""}`.toLowerCase()
							)
						? 2
						: 1),
		bullets: node.bullets?.slice(0, 5) || [],
		icon: node.icon || inferIconKey(node),
		note: node.note || (index === 0 && layoutType === "pipeline" ? "Start" : undefined),
		central:
			node.central ||
			/\borchestrator\b/i.test(node.label) ||
			(index === 0 &&
				(layoutType === "hub_spoke" || layoutType === "system_context") &&
				/orchestrator|platform|hub|context|ai|agent/.test(node.label.toLowerCase())),
	}));

	if (enrichedNodes.length > 0 && !enrichedNodes.some((node) => node.central)) {
		const candidateIndex = enrichedNodes.findIndex((node) =>
			/orchestrator|platform|hub|context|ai|agent|control/.test(
				`${node.label} ${node.role || ""} ${node.type || ""}`.toLowerCase()
			)
		);
		if (candidateIndex >= 0)
			enrichedNodes[candidateIndex] = {
				...enrichedNodes[candidateIndex],
				central: true,
				importance: 4,
			};
	}

	// Stable accent selection so the same prompt stays consistent while different prompts feel distinct.
	const accentSeed = hashString(seededText) % 360;
	void accentSeed;

	return {
		title,
		layoutType,
		theme,
		variant,
		nodes: enrichedNodes,
		edges,
		groups,
	};
}

type NodeTextLayout = {
	labelLines: string[];
	bulletLines: string[];
	contentWidth: number;
	contentHeight: number;
};

function getNodeTextLayout(
	node: GraphNode,
	variant: VariantKey,
	layoutType: LayoutType
): NodeTextLayout {
	const variantDensity = VARIANT_STYLES[variant].density;
	const labelFontSize = 18;
	const bulletFontSize = 12;
	const tagHeight = 22;
	const headerPaddingTop = 16;
	const topAccentHeight = 10;
	const titleGap = 14;
	const sectionGap = 10;
	const labelLineHeight = 20;
	const bulletLineHeight = 16;
	const bottomPadding = 18;
	const xPadding = 16;

	const importance = node.importance ?? 1;
	const baseWrapWidth =
		layoutType === "pipeline"
			? 260
			: layoutType === "hub_spoke"
				? 250
				: layoutType === "system_context"
					? 270
					: 280;
	const targetWrapWidth = clamp(
		Math.round((baseWrapWidth + importance * 18) * variantDensity),
		220,
		420
	);

	const cleanedLabel = cleanNodeLabel(node.label) || node.label;
	const labelLines = wrapSvgText(cleanedLabel, targetWrapWidth, {
		fontSize: labelFontSize,
		fontWeight: 700,
	});
	const bulletLines = (node.bullets || [])
		.slice(0, 4)
		.flatMap((bullet) => wrapSvgText(bullet, targetWrapWidth - 14, { fontSize: bulletFontSize }));

	const labelWidth = Math.max(
		...labelLines.map((line) =>
			measureTextWidth(line, { fontSize: labelFontSize, fontWeight: 700 })
		),
		measureTextWidth(cleanedLabel, { fontSize: labelFontSize, fontWeight: 700 })
	);
	const bulletWidth =
		bulletLines.length > 0
			? Math.max(...bulletLines.map((line) => measureTextWidth(line, { fontSize: bulletFontSize })))
			: 0;
	const contentWidth = Math.max(labelWidth, bulletWidth + 12);

	const labelHeight = Math.max(1, labelLines.length) * labelLineHeight;
	const bulletsHeight =
		bulletLines.length > 0 ? bulletLines.length * bulletLineHeight + sectionGap : 0;
	const contentHeight =
		topAccentHeight +
		headerPaddingTop +
		tagHeight +
		titleGap +
		labelHeight +
		(node.note ? 16 : 0) +
		bulletsHeight +
		bottomPadding;

	void xPadding;
	return {
		labelLines,
		bulletLines,
		contentWidth,
		contentHeight,
	};
}

function estimateNodeSize(node: GraphNode, variant: VariantKey, layoutType: LayoutType) {
	const variantDensity = VARIANT_STYLES[variant].density;
	const minWidth = Math.round(176 * variantDensity);
	const minHeight = Math.round(118 * variantDensity);
	const layout = getNodeTextLayout(node, variant, layoutType);
	const horizontalPadding = 32;
	const verticalPadding = 8;

	let width = Math.max(minWidth, Math.ceil(layout.contentWidth + horizontalPadding));
	let height = Math.max(minHeight, Math.ceil(layout.contentHeight + verticalPadding));

	// Central node in hub_spoke gets a larger footprint for visual dominance
	if ((layoutType === "hub_spoke" || layoutType === "system_context") && node.central) {
		width = Math.round(width * 1.35);
		height = Math.round(height * 1.25);
	}

	return { width, height };
}

function chooseCentralNode(nodes: PositionedNode[]) {
	// Priority 1: explicitly flagged central node
	const explicit = nodes.find((node) => node.central);
	if (explicit) return explicit;

	// Priority 2: semantic hub keywords in label/role/type
	const hubKeywords = /\b(orchestrator|router|hub|coordinator|manager|controller|gateway|platform|core|central|master|broker)\b/i;
	const semantic = nodes.find((node) =>
		hubKeywords.test(`${node.label} ${node.role || ""} ${node.type || ""}`)
	);
	if (semantic) return semantic;

	// Priority 3: highest importance score
	return nodes.reduce<PositionedNode | undefined>((best, node) => {
		if (!best) return node;
		return (node.importance || 0) > (best.importance || 0) ? node : best;
	}, undefined);
}

function pointOnNode(
	node: PositionedNode,
	target: { x: number; y: number },
	preferredAxis?: "horizontal" | "vertical"
) {
	const dx = target.x - node.x;
	const dy = target.y - node.y;
	const horizontal =
		preferredAxis === "horizontal" || (!preferredAxis && Math.abs(dx) >= Math.abs(dy));
	if (horizontal) {
		const anchorX = node.x + (dx >= 0 ? node.width / 2 : -node.width / 2);
		return { x: anchorX, y: node.y + clamp(dy, -node.height / 3, node.height / 3) };
	}
	const anchorY = node.y + (dy >= 0 ? node.height / 2 : -node.height / 2);
	return { x: node.x + clamp(dx, -node.width / 3, node.width / 3), y: anchorY };
}

type LayoutAttemptConfig = {
	rankdir: "LR" | "TB";
	nodesep: number;
	ranksep: number;
	align: "UL" | "UR" | "DL" | "DR";
	nodeMargin: number;
	edgeMargin: number;
	hubRadius?: number;
};

type LayoutOutput = {
	width: number;
	height: number;
	nodes: PositionedNode[];
	edges: PositionedEdge[];
};

type LayoutComputeResult = {
	layout: LayoutOutput;
	usedFallback: boolean;
	fastMode: boolean;
};

const FAST_NODE_THRESHOLD = 8;
const LAYOUT_BUDGET_MS = 3000;
const FAST_LAYOUT_BUDGET_MS = 2000;
const MAX_LAYOUT_ATTEMPTS = 2;

const RENDER_STAGES = ["Parsing", "Planning", "Layout", "Validation", "Done"] as const;
type RenderStage = (typeof RENDER_STAGES)[number];

function detectCollisions(nodes: PositionedNode[], minSeparation = 20): { a: string; b: string }[] {
	const collisions: { a: string; b: string }[] = [];
	for (let i = 0; i < nodes.length; i++) {
		for (let j = i + 1; j < nodes.length; j++) {
			const a = nodes[i];
			const b = nodes[j];
			const dx = a.x - b.x;
			const dy = a.y - b.y;
			const minDist = (a.width + b.width) / 2 + (a.height + b.height) / 4 + minSeparation;
			if (Math.sqrt(dx * dx + dy * dy) < minDist) {
				collisions.push({ a: a.id, b: b.id });
			}
		}
	}
	return collisions;
}

type Rect = { x: number; y: number; width: number; height: number };

function intersectsRect(a: Rect, b: Rect, padding = 0) {
	return !(
		a.x + a.width + padding < b.x ||
		a.x > b.x + b.width + padding ||
		a.y + a.height + padding < b.y ||
		a.y > b.y + b.height + padding
	);
}

function nodeRect(node: PositionedNode): Rect {
	return {
		x: node.x - node.width / 2,
		y: node.y - node.height / 2,
		width: node.width,
		height: node.height,
	};
}

function placeEdgeLabelBox(
	label: string,
	anchorX: number,
	anchorY: number,
	nodes: PositionedNode[],
	placed: Rect[]
) {
	const labelWidth = clamp(
		Math.ceil(measureTextWidth(label, { fontSize: 11, fontWeight: 600 }) + 20),
		56,
		220
	);
	const labelHeight = 24;
	const offsets = [0, -24, 24, -40, 40, -56, 56, -72, 72];

	for (const dy of offsets) {
		const candidate: Rect = {
			x: anchorX - labelWidth / 2,
			y: anchorY - labelHeight / 2 + dy,
			width: labelWidth,
			height: labelHeight,
		};
		const collidesNode = nodes.some((node) => intersectsRect(candidate, nodeRect(node), 6));
		const collidesLabel = placed.some((rect) => intersectsRect(candidate, rect, 4));
		if (!collidesNode && !collidesLabel) {
			placed.push(candidate);
			return {
				labelX: candidate.x + candidate.width / 2,
				labelY: candidate.y + candidate.height / 2,
				labelWidth,
				labelHeight,
			};
		}
	}

	const fallback: Rect = {
		x: anchorX - labelWidth / 2,
		y: anchorY - labelHeight / 2,
		width: labelWidth,
		height: labelHeight,
	};
	placed.push(fallback);
	return {
		labelX: fallback.x + fallback.width / 2,
		labelY: fallback.y + fallback.height / 2,
		labelWidth,
		labelHeight,
	};
}

function buildLoopPath(node: PositionedNode, offset = 0) {
	const radiusX = node.width * 0.95 + offset;
	const radiusY = node.height * 0.9 + offset;
	const x = node.x + node.width / 2;
	const y = node.y - node.height / 2;
	return `M ${x} ${y} C ${x + radiusX} ${y - radiusY}, ${x + radiusX} ${y + radiusY * 1.15}, ${x} ${y + radiusY * 1.75}`;
}

function buildOrthogonalPath(
	source: { x: number; y: number },
	target: { x: number; y: number },
	offset = 0
): string {
	const midX = (source.x + target.x) / 2;
	const midY = (source.y + target.y) / 2 + offset;

	// Three-segment orthogonal path (more professional)
	if (Math.abs(source.x - target.x) > Math.abs(source.y - target.y)) {
		// Horizontal primary
		return `M ${source.x} ${source.y} L ${midX} ${source.y} L ${midX} ${target.y} L ${target.x} ${target.y}`;
	}
	// Vertical primary
	return `M ${source.x} ${source.y} L ${source.x} ${midY} L ${target.x} ${midY} L ${target.x} ${target.y}`;
}

function buildCurvedPath(
	source: { x: number; y: number },
	target: { x: number; y: number },
	offset = 0,
	tension = 0.35
): string {
	const dx = target.x - source.x;
	const dy = target.y - source.y;
	const mid1X = source.x + dx * tension;
	const mid1Y = source.y + dy * tension + offset;
	const mid2X = source.x + dx * (1 - tension);
	const mid2Y = source.y + dy * (1 - tension) - offset;

	return `M ${source.x} ${source.y} C ${mid1X} ${mid1Y}, ${mid2X} ${mid2Y}, ${target.x} ${target.y}`;
}

function getGroupBounds(
	group: GraphGroup,
	nodes: PositionedNode[]
): { x: number; y: number; width: number; height: number } | null {
	const members = group.nodeIds ? nodes.filter((node) => group.nodeIds?.includes(node.id)) : [];
	if (members.length === 0) return null;

	const minX = Math.min(...members.map((node) => node.x - node.width / 2));
	const maxX = Math.max(...members.map((node) => node.x + node.width / 2));
	const minY = Math.min(...members.map((node) => node.y - node.height / 2));
	const maxY = Math.max(...members.map((node) => node.y + node.height / 2));

	const padding = 48;
	const titleHeight = 48;

	return {
		x: minX - padding,
		y: minY - padding - titleHeight,
		width: maxX - minX + padding * 2,
		height: maxY - minY + padding * 2 + titleHeight,
	};
}

function buildEdgePolylinePath(points: Array<{ x: number; y: number }>) {
	if (points.length === 0) return "";
	const commands = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`);
	return commands.join(" ");
}

function summarizeLayout(nodes: PositionedNode[], width: number, height: number) {
	const minX = Math.min(...nodes.map((node) => node.x - node.width / 2));
	const maxX = Math.max(...nodes.map((node) => node.x + node.width / 2));
	const minY = Math.min(...nodes.map((node) => node.y - node.height / 2));
	const maxY = Math.max(...nodes.map((node) => node.y + node.height / 2));
	const contentWidth = Math.max(1, maxX - minX);
	const contentHeight = Math.max(1, maxY - minY);
	return {
		minX,
		minY,
		maxX,
		maxY,
		contentWidth,
		contentHeight,
		utilization: Math.min(contentWidth / width, contentHeight / height),
	};
}

function fitLayoutToCanvas(layout: LayoutOutput) {
	if (layout.nodes.length === 0) return layout;

	// ── Constants ────────────────────────────────────────────────────────────
	const SAFE_PAD = 64;           // px safe margin on every side
	const TARGET_W = ENTERPRISE_CANVAS_WIDTH - SAFE_PAD * 2;   // 1472
	const TARGET_H = ENTERPRISE_CANVAS_HEIGHT - SAFE_PAD * 2;  // 772
	const MIN_UTIL = 0.75;         // upscale if below this
	const MAX_UTIL = 0.90;         // downscale if above this

	// ── Helpers ──────────────────────────────────────────────────────────────
	const computeBounds = (nodes: PositionedNode[]) => {
		const minX = Math.min(...nodes.map((n) => n.x - n.width / 2));
		const maxX = Math.max(...nodes.map((n) => n.x + n.width / 2));
		const minY = Math.min(...nodes.map((n) => n.y - n.height / 2));
		const maxY = Math.max(...nodes.map((n) => n.y + n.height / 2));
		return { minX, maxX, minY, maxY, w: Math.max(1, maxX - minX), h: Math.max(1, maxY - minY) };
	};

	const centerOnCanvas = (nodes: PositionedNode[]) => {
		const b = computeBounds(nodes);
		const ox = ENTERPRISE_CANVAS_WIDTH / 2 - (b.minX + b.maxX) / 2;
		const oy = ENTERPRISE_CANVAS_HEIGHT / 2 - (b.minY + b.maxY) / 2;
		nodes.forEach((n) => { n.x += ox; n.y += oy; });
	};

	const scaleAroundCentroid = (nodes: PositionedNode[], s: number) => {
		const b = computeBounds(nodes);
		const cx = (b.minX + b.maxX) / 2;
		const cy = (b.minY + b.maxY) / 2;
		nodes.forEach((n) => {
			n.x = cx + (n.x - cx) * s;
			n.y = cy + (n.y - cy) * s;
		});
	};

	// ── Step 1: scale to fit inside safe area ────────────────────────────────
	const b0 = computeBounds(layout.nodes);
	// Scale to fill TARGET area — allow both up and down scaling
	const scaleFit = Math.min(TARGET_W / b0.w, TARGET_H / b0.h);
	if (Math.abs(scaleFit - 1) > 0.01) {
		scaleAroundCentroid(layout.nodes, scaleFit);
	}

	// ── Step 2: center on canvas ─────────────────────────────────────────────
	centerOnCanvas(layout.nodes);

	// ── Step 3: utilization check — nudge scale to hit 75–90% target ─────────
	const b1 = computeBounds(layout.nodes);
	const util = Math.min(b1.w / ENTERPRISE_CANVAS_WIDTH, b1.h / ENTERPRISE_CANVAS_HEIGHT);

	if (util < MIN_UTIL) {
		// Too small — upscale to hit MIN_UTIL
		const upscale = MIN_UTIL / util;
		scaleAroundCentroid(layout.nodes, upscale);
		centerOnCanvas(layout.nodes);
	} else if (util > MAX_UTIL) {
		// Too large — downscale to hit MAX_UTIL
		const downscale = MAX_UTIL / util;
		scaleAroundCentroid(layout.nodes, downscale);
		centerOnCanvas(layout.nodes);
	}

	// ── Step 4: per-node clamp — catch any node still outside safe zone ───────
	const clippedNodes: string[] = [];
	layout.nodes.forEach((node) => {
		const left   = node.x - node.width / 2;
		const right  = node.x + node.width / 2;
		const top    = node.y - node.height / 2;
		const bottom = node.y + node.height / 2;
		let moved = false;
		if (left   < SAFE_PAD)                              { node.x += SAFE_PAD - left;                                    moved = true; }
		if (right  > ENTERPRISE_CANVAS_WIDTH  - SAFE_PAD)  { node.x -= right  - (ENTERPRISE_CANVAS_WIDTH  - SAFE_PAD);    moved = true; }
		if (top    < SAFE_PAD)                              { node.y += SAFE_PAD - top;                                     moved = true; }
		if (bottom > ENTERPRISE_CANVAS_HEIGHT - SAFE_PAD)  { node.y -= bottom - (ENTERPRISE_CANVAS_HEIGHT - SAFE_PAD);    moved = true; }
		if (moved) clippedNodes.push(node.id);
	});

	// ── Step 5: re-center after clamp (clamp can shift centroid) ─────────────
	if (clippedNodes.length > 0) centerOnCanvas(layout.nodes);

	// ── Debug ─────────────────────────────────────────────────────────────────
	const bFinal = computeBounds(layout.nodes);
	const finalUtil = Math.min(
		bFinal.w / ENTERPRISE_CANVAS_WIDTH,
		bFinal.h / ENTERPRISE_CANVAS_HEIGHT
	);
	const canvasCenterX = ENTERPRISE_CANVAS_WIDTH / 2;
	const canvasCenterY = ENTERPRISE_CANVAS_HEIGHT / 2;
	const graphCenterX  = (bFinal.minX + bFinal.maxX) / 2;
	const graphCenterY  = (bFinal.minY + bFinal.maxY) / 2;
	const centered =
		Math.abs(graphCenterX - canvasCenterX) < 8 &&
		Math.abs(graphCenterY - canvasCenterY) < 8;

	console.info("[poster fit]", {
		utilization: `${Math.round(finalUtil * 100)}%`,
		centered,
		clippedNodes,
		canvas: `${ENTERPRISE_CANVAS_WIDTH}×${ENTERPRISE_CANVAS_HEIGHT}`,
		graphSize: `${Math.round(bFinal.w)}×${Math.round(bFinal.h)}`,
	});

	layout.width  = ENTERPRISE_CANVAS_WIDTH;
	layout.height = ENTERPRISE_CANVAS_HEIGHT;
	return layout;
}

function getSyntheticEdges(
	nodes: GraphNode[],
	layoutType: LayoutType,
	explicitEdges: GraphEdge[]
): GraphEdge[] {
	if (explicitEdges.length > 0) return explicitEdges;
	if (nodes.length <= 1) return [] as GraphEdge[];

	const orderedNodes = [...nodes];
	const centralNode = orderedNodes.find((node) => node.central) || orderedNodes[0];

	if (layoutType === "hub_spoke" || layoutType === "system_context") {
		return orderedNodes
			.filter((node) => node.id !== centralNode.id)
			.map(
				(node) =>
					({
						from: centralNode.id,
						to: node.id,
						style: "curved",
					}) satisfies GraphEdge
			);
	}

	if (layoutType === "microservices_grid") {
		const clusters = new Map<string, GraphNode[]>();
		orderedNodes.forEach((node) => {
			const clusterKey = node.group || node.layer || node.role || node.type || "cluster";
			const cluster = clusters.get(clusterKey) || [];
			cluster.push(node);
			clusters.set(clusterKey, cluster);
		});

		const groupedEdges: GraphEdge[] = [];
		Array.from(clusters.values()).forEach((clusterNodes) => {
			clusterNodes.slice(0, -1).forEach((node, index) => {
				groupedEdges.push({
					from: node.id,
					to: clusterNodes[index + 1].id,
					style: "orthogonal",
				});
			});
		});

		const clusterLeaders = Array.from(clusters.values())
			.map((clusterNodes) => clusterNodes[0])
			.filter(Boolean);
		clusterLeaders.slice(0, -1).forEach((node, index) => {
			groupedEdges.push({
				from: node.id,
				to: clusterLeaders[index + 1].id,
				style: "orthogonal",
			});
		});
		return groupedEdges;
	}

	return orderedNodes.slice(0, -1).map((node, index) => ({
		from: node.id,
		to: orderedNodes[index + 1].id,
		style: (layoutType === "pipeline" || layoutType === "layered"
			? "orthogonal"
			: "curved") as GraphEdge["style"],
	}));
}

/**
 * Dedicated microservices grid layout engine — poster mode.
 *
 * Places nodes in a balanced 2–4 column grid, centered on the 1600×900 canvas.
 * - Columns: 2 for ≤4 nodes, 3 for ≤9, 4 for ≤16, else ceil(sqrt(n))
 * - Fixed horizontal and vertical gap of 80px
 * - Entire grid centered in canvas
 * - fitLayoutToCanvas handles final 75–90% utilization pass
 * - Edges connect card centers via straight lines
 */
function layoutMicroservicesGrid(graph: GraphData, baseNodes: PositionedNode[]): LayoutOutput {
	const H_GAP = 80;
	const V_GAP = 80;
	const n = baseNodes.length;

	// ── 1. Determine column count ─────────────────────────────────────────────
	const cols = n <= 2 ? 2
		: n <= 4  ? 2
		: n <= 6  ? 3
		: n <= 9  ? 3
		: n <= 12 ? 4
		: n <= 16 ? 4
		: Math.min(4, Math.ceil(Math.sqrt(n)));
	const rows = Math.ceil(n / cols);

	// ── 2. Uniform cell size — use the largest node as the cell template ──────
	const cellW = Math.max(...baseNodes.map((nd) => nd.width));
	const cellH = Math.max(...baseNodes.map((nd) => nd.height));

	// ── 3. Compute total grid dimensions ─────────────────────────────────────
	const gridW = cols * cellW + (cols - 1) * H_GAP;
	const gridH = rows * cellH + (rows - 1) * V_GAP;

	// ── 4. Top-left origin so grid is centered in canvas ─────────────────────
	const originX = (ENTERPRISE_CANVAS_WIDTH  - gridW) / 2 + cellW / 2;
	const originY = (ENTERPRISE_CANVAS_HEIGHT - gridH) / 2 + cellH / 2;

	// ── 5. Assign grid positions ──────────────────────────────────────────────
	const nodes: PositionedNode[] = baseNodes.map((node, i) => {
		const col = i % cols;
		const row = Math.floor(i / cols);
		return {
			...node,
			width:  cellW,
			height: cellH,
			x: originX + col * (cellW + H_GAP),
			y: originY + row * (cellH + V_GAP),
		};
	});

	// ── 6. Build edges — straight lines between card centers ─────────────────
	const supportEdges = getSyntheticEdges(nodes, graph.layoutType, graph.edges);
	const nodeMap = new Map(nodes.map((nd) => [nd.id, nd] as const));
	const edges: PositionedEdge[] = supportEdges
		.map((edge) => {
			const src = nodeMap.get(edge.from);
			const tgt = nodeMap.get(edge.to);
			if (!src || !tgt) return null;
			const start = pointOnNode(src, tgt);
			const end   = pointOnNode(tgt, src);
			return {
				...edge,
				path: `M ${start.x} ${start.y} L ${end.x} ${end.y}`,
				labelX: (start.x + end.x) / 2,
				labelY: (start.y + end.y) / 2 - 14,
				strokeDasharray: edge.dashed || edge.style === "dashed" ? "8 6" : undefined,
			} satisfies PositionedEdge;
		})
		.filter(Boolean) as PositionedEdge[];

	// ── 7. fitLayoutToCanvas: center + 75–90% utilization ────────────────────
	const result = fitLayoutToCanvas({
		width:  ENTERPRISE_CANVAS_WIDTH,
		height: ENTERPRISE_CANVAS_HEIGHT,
		nodes,
		edges,
	});

	// ── 8. Debug ──────────────────────────────────────────────────────────────
	const bFinal = (() => {
		const minX = Math.min(...result.nodes.map((nd) => nd.x - nd.width  / 2));
		const maxX = Math.max(...result.nodes.map((nd) => nd.x + nd.width  / 2));
		const minY = Math.min(...result.nodes.map((nd) => nd.y - nd.height / 2));
		const maxY = Math.max(...result.nodes.map((nd) => nd.y + nd.height / 2));
		return { w: maxX - minX, h: maxY - minY };
	})();
	const utilization = Math.round(
		Math.min(bFinal.w / ENTERPRISE_CANVAS_WIDTH, bFinal.h / ENTERPRISE_CANVAS_HEIGHT) * 100
	);
	const clippedNodes = result.nodes
		.filter((nd) =>
			nd.x - nd.width  / 2 < 0 ||
			nd.x + nd.width  / 2 > ENTERPRISE_CANVAS_WIDTH  ||
			nd.y - nd.height / 2 < 0 ||
			nd.y + nd.height / 2 > ENTERPRISE_CANVAS_HEIGHT
		)
		.map((nd) => nd.id);

	console.info("[microservices-grid]", {
		rows,
		cols,
		utilization: `${utilization}%`,
		clippedNodes,
	});

	return result;
}

/**
 * Produces a clean, centered, professional radial arrangement:
 * - Equal angular spoke placement starting from top (−π/2)
 * - Adaptive radius: min(W*0.28, max(W*0.18, nodeCount*32))
 * - Center node 1.5× larger, visually dominant
 * - Collision avoidance with radius expansion
 * - fitLayoutToCanvas handles final centering + 75–90% utilization
 */
function layoutHubSpoke(graph: GraphData, baseNodes: PositionedNode[]): LayoutOutput {
	const CX = ENTERPRISE_CANVAS_WIDTH  * 0.5;
	const CY = ENTERPRISE_CANVAS_HEIGHT * 0.5;

	// ── 1. Center node detection ─────────────────────────────────────────────
	const centralNode = chooseCentralNode(baseNodes) || baseNodes[0];
	const spokes      = baseNodes.filter((n) => n.id !== centralNode.id);
	const nodeCount   = spokes.length;

	// ── 2. Adaptive radius: poster-friendly, not too aggressive ──────────────
	// min(W*0.28, max(W*0.18, nodeCount*32))
	const radiusMin = ENTERPRISE_CANVAS_WIDTH * 0.18;   // 288
	const radiusMax = ENTERPRISE_CANVAS_WIDTH * 0.28;   // 448
	const radiusBase = clamp(nodeCount * 32, radiusMin, radiusMax);

	// Also ensure arc gap ≥ node footprint + 32px gap
	const maxNodeDim = Math.max(...spokes.map((n) => Math.max(n.width, n.height)), 140);
	const radiusForSpacing = nodeCount > 1
		? Math.ceil((maxNodeDim + 32) * nodeCount / (2 * Math.PI))
		: 0;
	const radius = clamp(Math.max(radiusBase, radiusForSpacing), radiusMin, radiusMax);

	console.info("[hub-spoke layout]", {
		centerNode: centralNode.label,
		radius,
		nodeCount: baseNodes.length,
	});

	// ── 3. Place spokes at equal angular intervals ────────────────────────────
	const placeSpokes = (r: number): PositionedNode[] =>
		baseNodes.map((node) => {
			if (node.id === centralNode.id) return { ...node, x: CX, y: CY };
			const idx   = spokes.findIndex((s) => s.id === node.id);
			const angle = (idx / Math.max(nodeCount, 1)) * Math.PI * 2 - Math.PI / 2;
			return { ...node, x: CX + Math.cos(angle) * r, y: CY + Math.sin(angle) * r };
		});

	// ── 4. Collision avoidance — expand radius up to 3 passes ────────────────
	let nodes = placeSpokes(radius);
	let currentRadius = radius;
	for (let pass = 0; pass < 3; pass++) {
		if (detectCollisions(nodes, 32).length === 0) break;
		currentRadius = Math.min(currentRadius * 1.15, radiusMax * 1.05);
		nodes = placeSpokes(currentRadius);
	}

	// ── 5. Build straight edges (clean poster look) ───────────────────────────
	const supportEdges = getSyntheticEdges(nodes, graph.layoutType, graph.edges);
	const nodeMap = new Map(nodes.map((n) => [n.id, n] as const));
	const edges: PositionedEdge[] = supportEdges
		.map((edge) => {
			const src = nodeMap.get(edge.from);
			const tgt = nodeMap.get(edge.to);
			if (!src || !tgt) return null;
			const start = pointOnNode(src, tgt);
			const end   = pointOnNode(tgt, src);
			return {
				...edge,
				path: `M ${start.x} ${start.y} L ${end.x} ${end.y}`,
				labelX: (start.x + end.x) / 2,
				labelY: (start.y + end.y) / 2 - 14,
				strokeDasharray: edge.dashed || edge.style === "dashed" ? "8 6" : undefined,
			} satisfies PositionedEdge;
		})
		.filter(Boolean) as PositionedEdge[];

	// ── 6. fitLayoutToCanvas handles centering + 75–90% utilization ──────────
	return fitLayoutToCanvas({
		width:  ENTERPRISE_CANVAS_WIDTH,
		height: ENTERPRISE_CANVAS_HEIGHT,
		nodes,
		edges,
	});
}

function layoutSimpleFallback(graph: GraphData, baseNodes: PositionedNode[]): LayoutOutput {
	if (graph.layoutType === "hub_spoke" || graph.layoutType === "system_context") {
		return layoutHubSpoke(graph, baseNodes);
	}
	if (graph.layoutType === "microservices_grid") {
		return layoutMicroservicesGrid(graph, baseNodes);
	}

	const horizontal = graph.layoutType === "pipeline" || graph.layoutType === "microservices_grid";
	const count = Math.max(baseNodes.length, 1);
	const nodes = baseNodes.map((node, index) => {
		if (horizontal) {
			const spacing = Math.min(240, (ENTERPRISE_CANVAS_WIDTH * 0.72) / count);
			return {
				...node,
				x: ENTERPRISE_CANVAS_WIDTH * 0.14 + index * spacing,
				y: ENTERPRISE_CANVAS_HEIGHT * 0.5,
			};
		}
		const spacing = Math.min(150, (ENTERPRISE_CANVAS_HEIGHT * 0.65) / count);
		return {
			...node,
			x: ENTERPRISE_CANVAS_WIDTH * 0.5,
			y: ENTERPRISE_CANVAS_HEIGHT * 0.16 + index * spacing,
		};
	});

	const supportEdges = getSyntheticEdges(nodes, graph.layoutType, graph.edges);
	const nodeMap = new Map(nodes.map((node) => [node.id, node] as const));
	const edges: PositionedEdge[] = supportEdges
		.map((edge, edgeIndex) => {
			const source = nodeMap.get(edge.from);
			const target = nodeMap.get(edge.to);
			if (!source || !target) return null;
			const axis = horizontal ? ("horizontal" as const) : ("vertical" as const);
			const start = pointOnNode(source, target, axis);
			const end = pointOnNode(target, source, axis);
			const path = buildOrthogonalPath(start, end, ((edgeIndex % 3) - 1) * 8);
			return {
				...edge,
				path,
				labelX: (start.x + end.x) / 2,
				labelY: (start.y + end.y) / 2 - 14,
				strokeDasharray: edge.dashed || edge.style === "dashed" ? "8 6" : undefined,
				bidirectional: edge.bidirectional,
			} satisfies PositionedEdge;
		})
		.filter(Boolean) as PositionedEdge[];

	return fitLayoutToCanvas({
		width: ENTERPRISE_CANVAS_WIDTH,
		height: ENTERPRISE_CANVAS_HEIGHT,
		nodes,
		edges,
	});
}

function layoutWithDagre(
	graph: GraphData,
	nodes: PositionedNode[],
	layoutType: LayoutType,
	config: LayoutAttemptConfig,
	fastMode = false
): LayoutOutput {
	const dagreGraph = new dagre.graphlib.Graph({ multigraph: true });
	dagreGraph.setDefaultEdgeLabel(() => ({}));
	dagreGraph.setGraph({
		rankdir: config.rankdir,
		nodesep: config.nodesep,
		ranksep: config.ranksep,
		edgesep: config.edgeMargin,
		marginx: config.nodeMargin,
		marginy: config.nodeMargin,
		align: config.align,
		ranker: fastMode ? "tight-tree" : "network-simplex",
	});

	const supportEdges = getSyntheticEdges(nodes, layoutType, graph.edges);
	const nodeMap = new Map(nodes.map((node) => [node.id, node] as const));
	const centralNode = chooseCentralNode(nodes);

	nodes.forEach((node) => {
		dagreGraph.setNode(node.id, {
			width: node.width,
			height: node.height,
		});
	});

	supportEdges.forEach((edge, index) => {
		if (!nodeMap.has(edge.from) || !nodeMap.has(edge.to)) return;
		dagreGraph.setEdge(
			edge.from,
			edge.to,
			{
				minlen: edge.feedback ? 2 : layoutType === "pipeline" ? 1 : 2,
				weight: edge.bidirectional ? 1.2 : edge.style === "dashed" ? 0.8 : 1,
			},
			`edge-${index}`
		);
	});

	dagre.layout(dagreGraph);

	nodes.forEach((node) => {
		const position = dagreGraph.node(node.id) as { x: number; y: number } | undefined;
		if (position) {
			node.x = position.x;
			node.y = position.y;
		}
	});

	if ((layoutType === "hub_spoke" || layoutType === "system_context") && centralNode) {
		const spokes = nodes.filter((node) => node.id !== centralNode.id);
		const nodeCount = spokes.length;

		// Same radius formula as layoutHubSpoke — poster-friendly
		const radiusMin = ENTERPRISE_CANVAS_WIDTH * 0.18;
		const radiusMax = ENTERPRISE_CANVAS_WIDTH * 0.28;
		const maxNodeDim = Math.max(...spokes.map((n) => Math.max(n.width, n.height)), 140);
		const radiusForSpacing = nodeCount > 1
			? Math.ceil((maxNodeDim + 32) * nodeCount / (2 * Math.PI))
			: 0;
		let currentRadius = clamp(
			Math.max(nodeCount * 32, radiusForSpacing, config.hubRadius || radiusMin),
			radiusMin,
			radiusMax
		);

		const centerX = centralNode.x;
		const centerY = centralNode.y;

		console.info("[hub-spoke layout]", {
			centerNode: centralNode.label,
			radius: currentRadius,
			nodeCount: nodes.length,
		});

		const placeAtRadius = (r: number) => {
			spokes.forEach((node, index) => {
				const angle = (index / Math.max(nodeCount, 1)) * Math.PI * 2 - Math.PI / 2;
				node.x = centerX + Math.cos(angle) * r;
				node.y = centerY + Math.sin(angle) * r;
			});
		};

		placeAtRadius(currentRadius);

		// Collision avoidance — up to 3 passes
		for (let attempt = 0; attempt < 3; attempt++) {
			if (detectCollisions(nodes, 32).length === 0) break;
			currentRadius = Math.min(currentRadius * 1.15, radiusMax * 1.05);
			placeAtRadius(currentRadius);
		}
	}

	const minX = Math.min(...nodes.map((node) => node.x - node.width / 2));
	const maxX = Math.max(...nodes.map((node) => node.x + node.width / 2));
	const minY = Math.min(...nodes.map((node) => node.y - node.height / 2));
	const maxY = Math.max(...nodes.map((node) => node.y + node.height / 2));
	const canvasWidth = Math.max(1400, Math.round((maxX - minX) / 0.84) + 160);
	const canvasHeight = Math.max(900, Math.round((maxY - minY) / 0.84) + 160);

	nodes.forEach((node) => {
		node.x += canvasWidth / 2 - (minX + maxX) / 2;
		node.y += canvasHeight / 2 - (minY + maxY) / 2;
	});

	const layout: LayoutOutput = {
		width: canvasWidth,
		height: canvasHeight,
		nodes,
		edges: buildEdgeRoutings(graph, layoutType, nodes, dagreGraph, supportEdges),
	};

	return fitLayoutToCanvas(layout);
}

function validateLayout(
	layout: LayoutOutput,
	graph: GraphData,
	options?: { relaxed?: boolean; fastMode?: boolean }
) {
	const relaxed = options?.relaxed || options?.fastMode;
	const collisions = detectCollisions(layout.nodes, relaxed ? 8 : 18);
	const uniqueNodeIds = new Set(layout.nodes.map((node) => node.id));
	const bounds = summarizeLayout(layout.nodes, layout.width, layout.height);
	const edgeCoverage = layout.edges.length > 0 && graph.nodes.length > 1;
	const canvasUsage = Math.min(
		bounds.contentWidth / layout.width,
		bounds.contentHeight / layout.height
	);
	const aspectRatio = layout.width / layout.height;
	const aspectOk = relaxed ? aspectRatio > 0.5 : Math.abs(aspectRatio - 16 / 9) <= 0.06;
	const usageOk = relaxed ? canvasUsage >= 0.45 : canvasUsage >= 0.72 && canvasUsage <= 0.98;
	const promptTextDetected = layout.nodes.some((node) => isPromptArtifactLabel(node.label));
	const duplicateNodes = uniqueNodeIds.size !== layout.nodes.length;
	const unreadableNodes = layout.nodes.filter((node) => {
		const textLayout = getNodeTextLayout(node, graph.variant, graph.layoutType);
		const requiredWidth = textLayout.contentWidth + 32;
		const requiredHeight = textLayout.contentHeight + 8;
		return node.width + 0.5 < requiredWidth || node.height + 0.5 < requiredHeight;
	});
	const brokenWordWrap = layout.nodes.some((node) => {
		const textLayout = getNodeTextLayout(node, graph.variant, graph.layoutType);
		const normalizedOriginal = cleanNodeLabel(node.label).toLowerCase().replace(/\s+/g, " ").trim();
		const normalizedWrapped = textLayout.labelLines
			.join(" ")
			.toLowerCase()
			.replace(/\s+/g, " ")
			.trim();
		return normalizedOriginal !== normalizedWrapped;
	});

	const nodeRects = layout.nodes.map((node) => nodeRect(node));
	const edgeLabelCollisions = layout.edges.filter((edge) => {
		if (!edge.label || !edge.labelWidth || !edge.labelHeight) return false;
		const rect: Rect = {
			x: edge.labelX - edge.labelWidth / 2,
			y: edge.labelY - edge.labelHeight / 2,
			width: edge.labelWidth,
			height: edge.labelHeight,
		};
		return nodeRects.some((candidate) => intersectsRect(rect, candidate, 4));
	});

	const pipelineFlowOk =
		graph.layoutType !== "pipeline" ||
		layout.edges.length === 0 ||
		layout.edges.filter((edge) => {
			const source = layout.nodes.find((node) => node.id === edge.from);
			const target = layout.nodes.find((node) => node.id === edge.to);
			if (!source || !target) return false;
			return source.x <= target.x;
		}).length /
			layout.edges.length >=
			0.7;

	const coreValid =
		layout.nodes.length > 0 &&
		edgeCoverage &&
		!promptTextDetected &&
		!duplicateNodes &&
		unreadableNodes.length === 0 &&
		edgeLabelCollisions.length === 0 &&
		!brokenWordWrap;
	const strictValid = collisions.length === 0 && aspectOk && usageOk && pipelineFlowOk && coreValid;

	return {
		valid: relaxed ? coreValid : strictValid,
		collisions,
		canvasUsage,
		aspectRatio,
		promptTextDetected,
		duplicateNodes,
		unreadableNodes,
		edgeLabelCollisions,
		brokenWordWrap,
	};
}

function computePositions(graph: GraphData): LayoutComputeResult {
	const startedAt = Date.now();
	const fastMode = graph.nodes.length <= FAST_NODE_THRESHOLD;
	const budgetMs = fastMode ? FAST_LAYOUT_BUDGET_MS : LAYOUT_BUDGET_MS;
	const baseNodes: PositionedNode[] = graph.nodes.map((node) => ({
		...node,
		x: node.x ?? 0,
		y: node.y ?? 0,
		...estimateNodeSize(node, graph.variant, graph.layoutType),
	}));
	const fallbackLayout = () =>
		layoutSimpleFallback(
			graph,
			baseNodes.map((node) => ({ ...node }))
		);

	// Hub-spoke and system_context layouts use the dedicated radial engine directly —
	// dagre produces left-heavy clusters for these topologies.
	if (graph.layoutType === "hub_spoke" || graph.layoutType === "system_context") {
		const hubLayout = layoutHubSpoke(graph, baseNodes.map((node) => ({ ...node })));
		const validation = validateLayout(hubLayout, graph, { relaxed: true, fastMode });
		if (validation.valid || hubLayout.nodes.length > 0) {
			return { layout: hubLayout, usedFallback: false, fastMode };
		}
		return { layout: fallbackLayout(), usedFallback: true, fastMode };
	}

	const configs: LayoutAttemptConfig[] = (() => {
		const lt = graph.layoutType as string;
		if (lt === "pipeline") return [
			{ rankdir: "LR" as const, nodesep: 56, ranksep: 168, align: "UL" as const, nodeMargin: 36, edgeMargin: 24 },
			{ rankdir: "LR" as const, nodesep: 72, ranksep: 204, align: "UL" as const, nodeMargin: 42, edgeMargin: 28 },
		];
		if (lt === "layered") return [
			{ rankdir: "TB" as const, nodesep: 54, ranksep: 158, align: "UL" as const, nodeMargin: 38, edgeMargin: 24 },
			{ rankdir: "TB" as const, nodesep: 68, ranksep: 188, align: "UL" as const, nodeMargin: 44, edgeMargin: 28 },
		];
		if (lt === "hub_spoke" || lt === "system_context") return [
			{ rankdir: "TB" as const, nodesep: 60, ranksep: 170, align: "UL" as const, nodeMargin: 38, edgeMargin: 26, hubRadius: lt === "system_context" ? 280 : 250 },
			{ rankdir: "TB" as const, nodesep: 72, ranksep: 200, align: "UL" as const, nodeMargin: 44, edgeMargin: 30, hubRadius: lt === "system_context" ? 300 : 270 },
		];
		return [
			{ rankdir: "LR" as const, nodesep: 62, ranksep: 164, align: "UL" as const, nodeMargin: 38, edgeMargin: 26 },
			{ rankdir: "LR" as const, nodesep: 78, ranksep: 196, align: "UL" as const, nodeMargin: 44, edgeMargin: 30 },
		];
	})();

	const attemptConfigs = fastMode ? configs.slice(0, 1) : configs.slice(0, MAX_LAYOUT_ATTEMPTS);
	let bestLayout: LayoutOutput | null = null;

	for (const config of attemptConfigs) {
		if (Date.now() - startedAt > budgetMs) break;
		const nodesForAttempt = baseNodes.map((node) => ({ ...node }));
		const layout = layoutWithDagre(graph, nodesForAttempt, graph.layoutType, config, fastMode);
		const validation = validateLayout(layout, graph, { fastMode, relaxed: fastMode });
		if (validation.valid) {
			return { layout, usedFallback: false, fastMode };
		}

		const needsReadabilityRetry =
			validation.unreadableNodes.length > 0 ||
			validation.edgeLabelCollisions.length > 0 ||
			validation.brokenWordWrap;
		if (needsReadabilityRetry && Date.now() - startedAt <= budgetMs) {
			const expandedNodes = baseNodes.map((node) => ({
				...node,
				width: Math.ceil(node.width * 1.12 + 8),
				height: Math.ceil(node.height * 1.1 + 8),
			}));
			const retryLayout = layoutWithDagre(graph, expandedNodes, graph.layoutType, config, fastMode);
			const retryValidation = validateLayout(retryLayout, graph, {
				fastMode,
				relaxed: fastMode,
			});
			if (retryValidation.valid) {
				return { layout: retryLayout, usedFallback: false, fastMode };
			}
			bestLayout = retryLayout;
			continue;
		}
		bestLayout = layout;
	}

	if (bestLayout && Date.now() - startedAt <= budgetMs) {
		const relaxedCheck = validateLayout(bestLayout, graph, { relaxed: true, fastMode });
		if (relaxedCheck.valid) {
			return { layout: bestLayout, usedFallback: false, fastMode };
		}
	}

	return { layout: fallbackLayout(), usedFallback: true, fastMode };
}

function buildEdgeRoutings(
	_graph: GraphData,
	layoutType: LayoutType,
	nodes: PositionedNode[],
	dagreGraph: dagre.graphlib.Graph,
	edges: GraphEdge[]
): PositionedEdge[] {
	const nodeMap = new Map(nodes.map((node) => [node.id, node] as const));
	const edgeCounts = new Map<string, number>();
	const placedLabelRects: Rect[] = [];

	return edges
		.map((edge, edgeIndex) => {
			const source = nodeMap.get(edge.from);
			const target = nodeMap.get(edge.to);
			if (!source || !target) return null;

			const key = `${edge.from}->${edge.to}`;
			const index = edgeCounts.get(key) || 0;
			edgeCounts.set(key, index + 1);

			const routed = dagreGraph.edge({ v: edge.from, w: edge.to, name: `edge-${edgeIndex}` }) as
				| { points?: Array<{ x: number; y: number }> }
				| undefined;
			const points = (routed?.points || [])
				.filter(Boolean)
				.map((point) => ({ x: point.x, y: point.y }));
			if (edge.feedback || edge.from === edge.to) {
				const edgeLabelPlacement = edge.label
					? placeEdgeLabelBox(
							edge.label,
							source.x + source.width * 0.95 + index * 6,
							source.y - source.height * 0.9,
							nodes,
							placedLabelRects
						)
					: {
							labelX: source.x + source.width * 0.95 + index * 6,
							labelY: source.y - source.height * 0.9,
							labelWidth: undefined,
							labelHeight: undefined,
						};
				const loop = buildLoopPath(source, index * 8);
				return {
					...edge,
					path: loop,
					labelX: edgeLabelPlacement.labelX,
					labelY: edgeLabelPlacement.labelY,
					labelWidth: edgeLabelPlacement.labelWidth,
					labelHeight: edgeLabelPlacement.labelHeight,
					strokeDasharray: edge.dashed || edge.style === "dashed" ? "8 6" : undefined,
					bidirectional: edge.bidirectional,
					points,
				} satisfies PositionedEdge;
			}

			const hasPoints = points.length >= 2;
			const useCurvedPath =
				edge.style === "curved" || layoutType === "hub_spoke" || layoutType === "system_context";
			const path =
				useCurvedPath && hasPoints
					? buildCurvedPath(points[0], points[points.length - 1], ((index % 3) - 1) * 12, 0.34)
					: hasPoints
						? buildEdgePolylinePath(points)
						: buildOrthogonalPath(
								pointOnNode(
									source,
									target,
									layoutType === "pipeline"
										? "horizontal"
										: layoutType === "layered"
											? "vertical"
											: undefined
								),
								pointOnNode(
									target,
									source,
									layoutType === "pipeline"
										? "horizontal"
										: layoutType === "layered"
											? "vertical"
											: undefined
								),
								((index % 3) - 1) * 12
							);

			const labelPoint = hasPoints
				? points[Math.floor(points.length / 2)]
				: { x: (source.x + target.x) / 2, y: (source.y + target.y) / 2 };
			const edgeLabelPlacement = edge.label
				? placeEdgeLabelBox(edge.label, labelPoint.x, labelPoint.y - 10, nodes, placedLabelRects)
				: {
						labelX: labelPoint.x,
						labelY: labelPoint.y - 10,
						labelWidth: undefined,
						labelHeight: undefined,
					};
			return {
				...edge,
				path,
				labelX: edgeLabelPlacement.labelX,
				labelY: edgeLabelPlacement.labelY,
				labelWidth: edgeLabelPlacement.labelWidth,
				labelHeight: edgeLabelPlacement.labelHeight,
				strokeDasharray: edge.dashed || edge.style === "dashed" ? "8 6" : undefined,
				bidirectional: edge.bidirectional,
				points,
			} satisfies PositionedEdge;
		})
		.filter(Boolean) as PositionedEdge[];
}

function edgeMarkerId(theme: ThemeKey) {
	return `ea-arrow-${theme}`;
}

function nodeTone(theme: ThemeKey, node: PositionedNode, seed: number) {
	const palette = {
		healthcare: ["#ecfeff", "#cffafe", "#bae6fd"],
		cloud: ["#eff6ff", "#dbeafe", "#bfdbfe"],
		fintech: ["#fff7ed", "#ffedd5", "#fed7aa"],
		ai: ["#f5f3ff", "#ede9fe", "#ddd6fe"],
		enterprise: ["#f8fafc", "#e2e8f0", "#cbd5e1"],
		cyber_security: ["#eff6ff", "#dbeafe", "#bfdbfe"],
	}[theme];
	const index = (hashString(node.id + seed.toString()) + (node.importance || 1)) % palette.length;
	return palette[index];
}

function buildEnterpriseExportSvg({
	graph,
	layout,
	theme,
	variant,
	positionedNodes,
	groupBounds,
	edges,
	centralNode,
}: {
	graph: GraphData;
	layout: LayoutOutput;
	theme: (typeof THEME_STYLES)[ThemeKey];
	variant: (typeof VARIANT_STYLES)[VariantKey];
	positionedNodes: PositionedNode[];
	groupBounds: PositionedGroup[];
	edges: PositionedEdge[];
	centralNode: PositionedNode | undefined;
}) {
	const width = layout.width;
	const height = layout.height;
	const titleLines = wrapSvgText(graph.title, Math.min(920, width - 220), {
		fontSize: 34,
		fontWeight: 700,
	});
	const subtitle = `${graph.layoutType.replace(/_/g, " ")} • ${graph.theme.replace(/_/g, " ")} theme`;
	const markerId = `export-${edgeMarkerId(graph.theme)}`;
	const titleHeight = titleLines.length * 28;
	void subtitle;
	void titleHeight;

	return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbfdff"/>
      <stop offset="50%" stop-color="#f4f7fb"/>
      <stop offset="100%" stop-color="#eef3f8"/>
    </linearGradient>
    <marker id="${markerId}" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="${theme.edge}" />
    </marker>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.12" />
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)" />
  <rect x="40" y="40" width="${width - 80}" height="${height - 80}" rx="30" fill="${theme.panel}" stroke="${theme.border}" stroke-width="2" />
  <rect x="64" y="64" width="${width - 128}" height="${height - 128}" rx="24" fill="none" stroke="${theme.border}" stroke-dasharray="8 6" opacity="0.55" />
  ${titleLines
		.map(
			(line, index) =>
				`<text x="90" y="${118 + index * 34}" font-family="Aptos, Segoe UI, sans-serif" font-size="${index === 0 ? 34 : 30}" font-weight="700" fill="${theme.text}">${escapeSvgText(line)}</text>`
		)
		.join("\n  ")}

  ${groupBounds
		.map(
			(group) => `
  <g>
    <rect x="${group.x}" y="${group.y}" width="${group.width}" height="${group.height}" rx="24" fill="${theme.panelSoft}" stroke="${theme.border}" stroke-width="1.5" stroke-dasharray="10 8" opacity="0.95" />
  </g>`
		)
		.join("\n  ")}

  ${edges
		.map(
			(edge) => `
  <path d="${edge.path}" fill="none" stroke="${theme.edge}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"${edge.strokeDasharray ? ` stroke-dasharray="${edge.strokeDasharray}"` : ""} marker-end="url(#${markerId})"${edge.bidirectional ? ` marker-start="url(#${markerId})"` : ""} opacity="${edge.dashed ? 0.8 : 0.92}" />`
		)
		.join("\n  ")}

  ${positionedNodes
		.map((node) => {
			const tone = nodeTone(graph.theme, node, hashString(graph.title));
			const highlight = node.central || node === centralNode;
			const textLayout = getNodeTextLayout(node, graph.variant, graph.layoutType);
			const labelLines = textLayout.labelLines;
			const bulletLines = textLayout.bulletLines.slice(0, 5);
			const labelStartY = node.y - node.height / 2 + 42;
			const bulletStartY = labelStartY + labelLines.length * 20 + 18;
			const tag = node.type || node.role || node.group || "component";
			return `
  <g filter="url(#softShadow)">
    <rect x="${node.x - node.width / 2}" y="${node.y - node.height / 2}" width="${node.width}" height="${node.height}" rx="${variant.radius.replace(/px$/, "")}" fill="${tone}" stroke="${highlight ? theme.edge : theme.border}" stroke-width="${highlight ? 2.6 : 1.4}" />
    <rect x="${node.x - node.width / 2}" y="${node.y - node.height / 2}" width="${node.width}" height="10" rx="${variant.radius.replace(/px$/, "")}" fill="${theme.edge}" opacity="0.9" />
    <rect x="${node.x - node.width / 2 + 14}" y="${node.y - node.height / 2 + 16}" width="72" height="22" rx="11" fill="${theme.panel}" stroke="${theme.border}" stroke-width="1" />
    <text x="${node.x - node.width / 2 + 50}" y="${node.y - node.height / 2 + 31}" text-anchor="middle" font-family="Aptos, Segoe UI, sans-serif" font-size="10" font-weight="700" fill="${theme.muted}" letter-spacing="0.12em">${escapeSvgText(tag.toUpperCase())}</text>
    ${labelLines
			.map(
				(line, index) =>
					`<text x="${node.x - node.width / 2 + 16}" y="${labelStartY + index * 20}" font-family="Aptos, Segoe UI, sans-serif" font-size="18" font-weight="700" fill="${theme.text}">${escapeSvgText(line)}</text>`
			)
			.join("\n    ")}
    ${node.note ? `<text x="${node.x - node.width / 2 + 16}" y="${labelStartY + labelLines.length * 20 + 16}" font-family="Aptos, Segoe UI, sans-serif" font-size="11" fill="${theme.muted}">${escapeSvgText(node.note)}</text>` : ""}
    ${bulletLines
			.map(
				(line, index) =>
					`<text x="${node.x - node.width / 2 + 20}" y="${bulletStartY + index * 16}" font-family="Aptos, Segoe UI, sans-serif" font-size="12" fill="${theme.muted}">• ${escapeSvgText(line)}</text>`
			)
			.join("\n    ")}
  </g>`;
		})
		.join("\n  ")}
</svg>`;
}

export default function EnterpriseArchitectureRenderer({ data }: { data: EnterpriseGraphInput }) {
	const graph = React.useMemo(() => buildGraph(data), [data]);
	const previewLayout = React.useMemo(
		() =>
			graph.nodes.length > 0
				? layoutSimpleFallback(
						graph,
						graph.nodes.map((node) => ({
							...node,
							x: node.x ?? 0,
							y: node.y ?? 0,
							...estimateNodeSize(node, graph.variant, graph.layoutType),
						}))
					)
				: null,
		[graph]
	);

	const [, setRenderStage] = React.useState<RenderStage>("Parsing");
	const [layoutResult, setLayoutResult] = React.useState<LayoutComputeResult | null>(null);

	React.useEffect(() => {
		if (graph.nodes.length === 0) {
			setRenderStage("Done");
			setLayoutResult(null);
			return;
		}

		setRenderStage("Parsing");
		const parsingTimer = window.setTimeout(() => setRenderStage("Planning"), 40);
		const planningTimer = window.setTimeout(() => setRenderStage("Layout"), 80);

		if (previewLayout) {
			setLayoutResult({
				layout: previewLayout,
				usedFallback: true,
				fastMode: graph.nodes.length <= FAST_NODE_THRESHOLD,
			});
		}

		const layoutTimer = window.setTimeout(() => {
			setRenderStage("Validation");
			const computed = computePositions(graph);
			setLayoutResult(computed);
			setRenderStage("Done");
		}, 0);

		const layoutDeadline = window.setTimeout(() => {
			setLayoutResult((current) => {
				if (current?.layout) return current;
				if (!previewLayout) return current;
				return { layout: previewLayout, usedFallback: true, fastMode: true };
			});
			setRenderStage("Done");
		}, LAYOUT_BUDGET_MS);

		return () => {
			window.clearTimeout(parsingTimer);
			window.clearTimeout(planningTimer);
			window.clearTimeout(layoutTimer);
			window.clearTimeout(layoutDeadline);
		};
	}, [graph, previewLayout]);

	const layout = (layoutResult?.layout ??
		previewLayout ?? {
			width: ENTERPRISE_CANVAS_WIDTH,
			height: ENTERPRISE_CANVAS_HEIGHT,
			nodes: [],
			edges: [],
		}) as LayoutOutput;
	const edges = layout.edges;

	const theme = THEME_STYLES[graph.theme];
	const variant = VARIANT_STYLES[graph.variant];
	const seed = hashString(`${graph.title} ${graph.layoutType} ${graph.theme} ${graph.variant}`);
	const positionedNodes = layout.nodes as PositionedNode[];
	const width = ENTERPRISE_CANVAS_WIDTH;
	const height = ENTERPRISE_CANVAS_HEIGHT;
	const groupBounds = graph.groups
		.map((group) => {
			const bounds = getGroupBounds(group, positionedNodes);
			return bounds ? { ...group, ...bounds } : null;
		})
		.filter(Boolean) as PositionedGroup[];
	const centralNode = chooseCentralNode(positionedNodes);
	const displayTitle = isPromptArtifactLabel(graph.title)
		? positionedNodes[0]?.label || "Enterprise Architecture"
		: graph.title;
	const exportSvg = React.useCallback(
		() =>
			buildEnterpriseExportSvg({
				graph: { ...graph, title: displayTitle },
				layout,
				theme,
				variant,
				positionedNodes,
				groupBounds,
				edges,
				centralNode: centralNode || undefined,
			}),
		[centralNode, displayTitle, edges, graph, groupBounds, layout, positionedNodes, theme, variant]
	);
	const downloadBlob = React.useCallback((blob: Blob, filename: string) => {
		const url = URL.createObjectURL(blob);
		const anchor = document.createElement("a");
		anchor.href = url;
		anchor.download = filename;
		document.body.appendChild(anchor);
		anchor.click();
		document.body.removeChild(anchor);
		URL.revokeObjectURL(url);
	}, []);
	const handleDownloadSvg = React.useCallback(() => {
		const svg = exportSvg();
		downloadBlob(
			new Blob([svg], { type: "image/svg+xml;charset=utf-8" }),
			"architecture-diagram.svg"
		);
	}, [downloadBlob, exportSvg]);
	const handleDownloadPng = React.useCallback(() => {
		const svg = exportSvg();
		const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
		const url = URL.createObjectURL(blob);
		const image = new Image();
		image.onload = () => {
			const canvas = document.createElement("canvas");
			canvas.width = width;
			canvas.height = height;
			const context = canvas.getContext("2d");
			if (!context) {
				URL.revokeObjectURL(url);
				return;
			}
			context.fillStyle = "#ffffff";
			context.fillRect(0, 0, width, height);
			context.drawImage(image, 0, 0, width, height);
			canvas.toBlob((pngBlob) => {
				if (pngBlob) downloadBlob(pngBlob, "architecture-diagram.png");
				URL.revokeObjectURL(url);
			}, "image/png");
		};
		image.onerror = () => URL.revokeObjectURL(url);
		image.src = url;
	}, [downloadBlob, exportSvg]);

	if (graph.nodes.length === 0) {
		return (
			<div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700 shadow-sm">
				<div className="text-sm font-semibold">Enterprise parsing error</div>
				<div className="mt-1 text-sm text-rose-600">
					The enterprise architecture JSON did not include any nodes to render.
				</div>
			</div>
		);
	}

	return (
		<div
			className="enterprise-arch relative w-full overflow-hidden p-4 text-zinc-950 md:p-6"
			style={{
				background: theme.shell,
				color: theme.text,
			}}
		>
			{/* Dot-grid background */}
			<div className="pointer-events-none absolute inset-0 opacity-[0.18] [background-image:radial-gradient(#64748b_1px,transparent_1px)] [background-size:18px_18px]" />
			<div
				className="pointer-events-none absolute inset-0"
				style={{
					background: `radial-gradient(circle at 20% 20%, ${theme.shellAccent} 0%, transparent 35%), radial-gradient(circle at 80% 20%, ${theme.glow} 0%, transparent 30%), radial-gradient(circle at 50% 80%, ${theme.shellAccent} 0%, transparent 35%)`,
				}}
			/>

			<div className="relative flex flex-col gap-5">
				{/* Header row: title + download buttons */}
				<div className="flex items-start justify-between gap-4">
					<div className="max-w-4xl">
						<h3
							className={`${variant.titleScale} font-semibold tracking-tight`}
							style={{ color: theme.text }}
						>
							{displayTitle}
						</h3>
					</div>
					<div className="flex gap-2 shrink-0">
						<Button
							variant="outline"
							size="sm"
							onClick={handleDownloadPng}
							className="h-8 gap-1.5 text-xs"
						>
							<Download className="h-3.5 w-3.5" />
							Download PNG
						</Button>
						<Button
							variant="outline"
							size="sm"
							onClick={handleDownloadSvg}
							className="h-8 gap-1.5 text-xs"
						>
							<Download className="h-3.5 w-3.5" />
							Download SVG
						</Button>
					</div>
				</div>

				{/* ── Poster canvas ─────────────────────────────────────────────────────
				    Single SVG with viewBox="0 0 1600 900" + preserveAspectRatio="xMidYMid meet".
				    The browser scales and centers the entire diagram automatically.
				    Node cards are rendered as <foreignObject> so they keep HTML styling.
				    Edges are plain SVG paths drawn in the same coordinate space.
				─────────────────────────────────────────────────────────────────────── */}
				<div
					className="w-full overflow-hidden rounded-[28px] border shadow-[0_22px_70px_rgba(15,23,42,0.09)]"
					style={{ borderColor: theme.border, background: theme.panel }}
				>
					<svg
						viewBox={`0 0 ${width} ${height}`}
						preserveAspectRatio="xMidYMid meet"
						xmlns="http://www.w3.org/2000/svg"
						style={{ display: "block", width: "100%", height: "auto" }}
						aria-label={displayTitle}
					>
						<defs>
							<marker
								id={edgeMarkerId(graph.theme)}
								markerWidth="10"
								markerHeight="10"
								refX="9"
								refY="3"
								orient="auto"
							>
								<path d="M0,0 L0,6 L9,3 z" fill={theme.edge} />
							</marker>
							<filter id="ea-node-shadow" x="-20%" y="-20%" width="140%" height="140%">
								<feDropShadow dx="0" dy="3" stdDeviation="6" floodColor="#0f172a" floodOpacity="0.10" />
							</filter>
							<filter id="ea-center-shadow" x="-25%" y="-25%" width="150%" height="150%">
								<feDropShadow dx="0" dy="4" stdDeviation="10" floodColor="#0f172a" floodOpacity="0.16" />
							</filter>
						</defs>

						{/* Group boundary boxes */}
						{groupBounds.map((group) => (
							<rect
								key={group.id}
								x={group.x}
								y={group.y}
								width={group.width}
								height={group.height}
								rx="24"
								fill={theme.panelSoft}
								stroke={theme.border}
								strokeWidth="1.5"
								strokeDasharray="10 7"
								opacity="0.7"
							/>
						))}

						{/* Edges */}
						{edges.map((edge) => (
							<g key={`${edge.from}-${edge.to}-${edge.labelX}`}>
								<path
									d={edge.path}
									stroke={theme.edge}
									strokeWidth="2.2"
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeDasharray={edge.strokeDasharray}
									fill="none"
									opacity={edge.dashed ? 0.75 : 0.88}
									markerEnd={`url(#${edgeMarkerId(graph.theme)})`}
									markerStart={
										edge.bidirectional
											? `url(#${edgeMarkerId(graph.theme)})`
											: undefined
									}
								/>
								{edge.label && (
									<g>
										<rect
											x={edge.labelX - (edge.labelWidth || 80) / 2}
											y={edge.labelY - 11}
											rx="5"
											width={edge.labelWidth || 80}
											height={22}
											fill={theme.panel}
											stroke={theme.border}
											strokeWidth="1"
										/>
										<text
											x={edge.labelX}
											y={edge.labelY + 4}
											textAnchor="middle"
											fontSize="10"
											fontWeight="600"
											fill={theme.muted}
											fontFamily="system-ui, sans-serif"
										>
											{edge.label}
										</text>
									</g>
								)}
							</g>
						))}

						{/* Node cards via foreignObject */}
						{positionedNodes.map((node, index) => {
							const tone = nodeTone(graph.theme, node, seed);
							const highlight = node.central || node === centralNode;
							const importance = node.importance || 1;
							const textLayout = getNodeTextLayout(node, graph.variant, graph.layoutType);
							const labelLines = textLayout.labelLines;
							const bulletLines = textLayout.bulletLines;
							const nx = node.x - node.width / 2;
							const ny = node.y - node.height / 2;

							return (
								<g
									key={node.id}
									filter={highlight ? "url(#ea-center-shadow)" : "url(#ea-node-shadow)"}
								>
									{/* Card background */}
									<rect
										x={nx}
										y={ny}
										width={node.width}
										height={node.height}
										rx={parseInt(variant.radius)}
										fill={tone}
										stroke={highlight ? theme.edge : theme.border}
										strokeWidth={highlight ? 2.4 : 1.2}
									/>
									{/* Glow ring for center node */}
									{highlight && (
										<rect
											x={nx - 5}
											y={ny - 5}
											width={node.width + 10}
											height={node.height + 10}
											rx={parseInt(variant.radius) + 4}
											fill="none"
											stroke={theme.edge}
											strokeWidth="1"
											opacity="0.25"
										/>
									)}
									{/* Top accent bar */}
									<rect
										x={nx}
										y={ny}
										width={node.width}
										height={8}
										rx={parseInt(variant.radius)}
										fill={theme.edge}
										opacity="0.85"
									/>
									{/* foreignObject for HTML content */}
									<foreignObject
										x={nx}
										y={ny}
										width={node.width}
										height={node.height}
									>
										<div
											style={{
												width: "100%",
												height: "100%",
												display: "flex",
												flexDirection: "column",
												gap: "8px",
												padding: "14px 14px 10px",
												boxSizing: "border-box",
												fontFamily: "system-ui, -apple-system, sans-serif",
												overflow: "hidden",
											}}
										>
											{/* Tag + label row */}
											<div style={{ display: "flex", alignItems: "flex-start", gap: "8px", marginTop: "6px" }}>
												{/* Icon box */}
												<div
													style={{
														width: 36,
														height: 36,
														flexShrink: 0,
														display: "flex",
														alignItems: "center",
														justifyContent: "center",
														borderRadius: highlight ? "12px" : "10px",
														border: `1.2px solid ${theme.border}`,
														background: "rgba(255,255,255,0.85)",
														boxShadow: highlight ? `0 0 0 4px ${theme.glow}` : undefined,
													}}
												>
													{iconForNode(node)}
												</div>
												<div style={{ minWidth: 0, flex: 1 }}>
													{/* Type badge */}
													<div
														style={{
															display: "inline-flex",
															borderRadius: "999px",
															border: `1px solid ${theme.border}`,
															background: theme.panel,
															color: theme.muted,
															fontSize: "9px",
															fontWeight: 700,
															letterSpacing: "0.14em",
															textTransform: "uppercase",
															padding: "2px 8px",
															marginBottom: "4px",
														}}
													>
														{node.type || node.role || node.group || "component"}
													</div>
													{/* Label */}
													<div
														style={{
															fontSize: highlight ? "15px" : "13px",
															fontWeight: 700,
															lineHeight: 1.25,
															color: theme.text,
															wordBreak: "break-word",
														}}
													>
														{labelLines.map((line, li) => (
															<div key={li}>{line}</div>
														))}
													</div>
													{node.note && (
														<div style={{ fontSize: "10px", color: theme.muted, marginTop: "2px" }}>
															{node.note}
														</div>
													)}
												</div>
											</div>

											{/* Bullets */}
											{bulletLines.length > 0 && (
												<ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "3px" }}>
													{bulletLines.slice(0, 4).map((bullet, bi) => (
														<li
															key={bi}
															style={{
																display: "flex",
																alignItems: "flex-start",
																gap: "5px",
																fontSize: "10px",
																color: theme.muted,
																lineHeight: 1.3,
															}}
														>
															<span
																style={{
																	width: 5,
																	height: 5,
																	borderRadius: "50%",
																	background: theme.edge,
																	flexShrink: 0,
																	marginTop: "3px",
																}}
															/>
															{bullet}
														</li>
													))}
												</ul>
											)}

											{/* Footer: priority indicator */}
											{importance > 1 && (
												<div
													style={{
														marginTop: "auto",
														fontSize: "9px",
														color: theme.muted,
														textTransform: "uppercase",
														letterSpacing: "0.12em",
													}}
												>
													{highlight ? "⬡ Hub" : `P${importance}`}
												</div>
											)}
										</div>
									</foreignObject>
								</g>
							);
						})}
					</svg>
				</div>
			</div>
		</div>
	);
}
