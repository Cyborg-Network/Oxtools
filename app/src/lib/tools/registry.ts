import type { CategoryInfo, ToolCategory, ToolDefinition } from "@/types";

// --- Core tool definitions ---
import { codeErrorDebugger } from "./code-error-debugger";
import { codeSecurityScanner } from "./code-security-scanner";
import { unitTestGenerator } from "./unit-test-generator";
import { prSummarizer } from "./pr-summarizer";
import { sqlConverter } from "./sql-converter";
import { apiValidator } from "./api-validator";
import { mockApiGenerator } from "./mock-api-generator";
import { jsonToSchema } from "./json-to-schema";
import { regexExplainer } from "./regex-explainer";
import { readmeGenerator } from "./readme-generator";
import { grammarChecker } from "./grammar-checker";
import { architectureDiagram } from "./architecture-diagram";

// --- Tools from Arun's fork (feat/Oxtools-refinements) ---
import { apiChangeAnalyzer } from "./api-change-analyzer";
import { csvInsightGenerator } from "./csv-insight-generator";

// --- Newly activated tools (previously stubs) ---
import { cssExplainer } from "./css-explainer";
import { sampleDatasetGenerator } from "./sample-dataset-generator";
import { textFormatter } from "./text-formatter";
import { pdfSummarizer } from "./pdf-summarizer";
import { uiToCode } from "./ui-to-code";
import { colorPalette } from "./color-palette";
import { logAnalyzer } from "./log-analyzer";
import { bugReplayer } from "./bug-replayer";
import { captionGenerator } from "./caption-generator";
import { seoWriter } from "./seo-writer";

// --- Tier 2 tools (Python services, proxied via gateway) ---
import { screenshotToCode } from "./screenshot-to-code";
import { deepResearch } from "./deep-research";

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
  // Developer Tools (5)
  codeErrorDebugger,
  codeSecurityScanner,
  unitTestGenerator,
  prSummarizer,
  cssExplainer,

  // Data & API (6)
  sqlConverter,
  apiValidator,
  apiChangeAnalyzer,
  mockApiGenerator,
  jsonToSchema,
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
  screenshotToCode,  // ← Tier 2: proxied to Python Docker container

  // DevOps & System (2)
  logAnalyzer,
  bugReplayer,

  // Content & Marketing (3)
  captionGenerator,
  seoWriter,
  deepResearch,     // Tier 2: LangGraph multi-agent Python service
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

