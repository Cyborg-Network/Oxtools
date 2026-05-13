import type { CategoryInfo, ToolCategory, ToolDefinition } from "@/types";
// --- Tools from Arun's fork (feat/Oxtools-refinements) ---
import { apiChangeAnalyzer } from "./api-change-analyzer";
import { apiValidator } from "./api-validator";
import { architectureDiagram } from "./architecture-diagram";
import { bugReplayer } from "./bug-replayer";
import { captionGenerator } from "./caption-generator";
// --- Core tool definitions ---
import { codeErrorDebugger } from "./code-error-debugger";
import { codeSecurityScanner } from "./code-security-scanner";
import { codeSecurityScannerV2 } from "./code-security-scanner-v2";
import { colorPalette } from "./color-palette";
// --- Newly activated tools (previously stubs) ---
import { cssExplainer } from "./css-explainer";
import { csvInsightGenerator } from "./csv-insight-generator";
import { deepResearch } from "./deep-research";
import { grammarChecker } from "./grammar-checker";
import { jsonToSchema } from "./json-to-schema";
import { jsonToSchemaV2 } from "./json-to-schema-v2";
import { logAnalyzer } from "./log-analyzer";
import { mockApiGenerator } from "./mock-api-generator";
import { pdfSummarizer } from "./pdf-summarizer";
import { prSummarizer } from "./pr-summarizer";
import { readmeGenerator } from "./readme-generator";
import { regexExplainer } from "./regex-explainer";
import { sampleDatasetGenerator } from "./sample-dataset-generator";
// --- Tier 2 tools (Python services, proxied via gateway) ---
import { screenshotToCode } from "./screenshot-to-code";
import { seoWriter } from "./seo-writer";
import { sqlConverter } from "./sql-converter";
import { textFormatter } from "./text-formatter";
import { uiToCode } from "./ui-to-code";
import { unitTestGenerator } from "./unit-test-generator";
import { autoReadmeGeneratorTool } from "./auto-readme-generator";

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export const categories: Record<ToolCategory, CategoryInfo> = {
	developer: {
		name: "Developer Tools",
		icon: "Code2",
		description: "Debug, analyze, and generate code with AI",
	},
	data: {
		name: "Data & API",
		icon: "Database",
		description: "Work with APIs, SQL, and data schemas",
	},
	documentation: {
		name: "Docs & Text",
		icon: "FileText",
		description: "Generate documentation and format text",
	},
	design: {
		name: "Design & Visual",
		icon: "Palette",
		description: "Convert designs and extract visual data",
	},
	devops: {
		name: "DevOps & System",
		icon: "Server",
		description: "Analyze logs and reproduce bugs",
	},
	content: {
		name: "Content & Marketing",
		icon: "PenTool",
		description: "Generate captions, SEO copy, and more",
	},
};

// ---------------------------------------------------------------------------
// Tool Registry - the single source of truth
// ALL 24 tools are ACTIVE - zero stubs remaining.
// ---------------------------------------------------------------------------

export const tools: ToolDefinition[] = [
	// Developer Tools (6)
	codeErrorDebugger,
	codeSecurityScanner,
	codeSecurityScannerV2,
	unitTestGenerator,
	prSummarizer,
	cssExplainer,

	// Data & API (6)
	sqlConverter,
	apiValidator,
	apiChangeAnalyzer,
	mockApiGenerator,
	jsonToSchema,
	jsonToSchemaV2,
	csvInsightGenerator,
	sampleDatasetGenerator,

	// Documentation & Text (5)
	regexExplainer,
	readmeGenerator,
	grammarChecker,
	textFormatter,
	pdfSummarizer,

	// Design & Visual (4)
	architectureDiagram,
	uiToCode,
	colorPalette,
	screenshotToCode, // ← Tier 2: proxied to Python Docker container

	// DevOps & System (2)
	logAnalyzer,
	bugReplayer,

	// Content & Marketing (3)
	captionGenerator,
	seoWriter,
	deepResearch, // Tier 2: LangGraph multi-agent Python service
	autoReadmeGeneratorTool,
];

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

export function getToolsByCategory(): Record<ToolCategory, ToolDefinition[]> {
	return tools.reduce(
		(acc, tool) => {
			if (!acc[tool.category]) {
				acc[tool.category] = [];
			}
			acc[tool.category].push(tool);
			return acc;
		},
		{} as Record<ToolCategory, ToolDefinition[]>
	);
}

export function getToolById(id: string): ToolDefinition | undefined {
	return tools.find((t) => t.id === id);
}

export function getActiveTools(): ToolDefinition[] {
	return tools.filter((t) => t.status === "active");
}
