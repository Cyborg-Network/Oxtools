# Adding a Frontend Tool (Tier 1) to Oxtools

## Overview

Tier 1 tools are **pure prompt-engineered LLM tools** that run entirely in the frontend.
They don't require any custom backend — the Next.js API route sends the prompt directly
to the Oxlo API and streams the response back to the user.

Most tools in Oxtools are Tier 1. If your tool is essentially "send a prompt, get text back",
this is the right approach.

## Quick Start (10 minutes)

### 1. Create the tool definition

Create a new file in `app/src/lib/tools/`:

```typescript
// app/src/lib/tools/my-tool.ts
import type { ToolDefinition } from "@/types";

export const myTool: ToolDefinition = {
  id: "my-tool",                    // URL-safe, kebab-case
  name: "My Tool Name",
  description: "One sentence describing what this tool does.",
  category: "developer",            // developer | data | documentation | design | devops | content
  icon: "Wrench",                   // Any Lucide icon name
  status: "active",

  defaultModel: "llama-3.3-70b",    // Pick from Oxlo's model catalog
  requiredFields: ["query"],         // Fields that must be filled before running

  buildSystemPrompt: ({ language }) =>
    `You are an expert ${language || "general"} developer. Help the user with their request.`,

  buildUserPrompt: ({ query }) =>
    `${query}`,

  inputs: [
    {
      key: "query",
      label: "Your Question",
      type: "textarea",              // text | textarea | select | image
      placeholder: "Describe what you need...",
      rows: 4,
    },
    {
      key: "language",
      label: "Language",
      type: "select",
      options: [
        { value: "javascript", label: "JavaScript" },
        { value: "python", label: "Python" },
        { value: "rust", label: "Rust" },
      ],
    },
  ],
};
```

### 2. Register in the tool registry

Open `app/src/lib/tools/registry.ts` and add your tool:

```typescript
// Add the import
import { myTool } from "./my-tool";

// Add to the tools array under the correct category
export const tools: ToolDefinition[] = [
  // Developer Tools
  codeErrorDebugger,
  myTool,              // ← Add here
  // ...
];
```

### 3. Test locally

```bash
cd app && npm run dev
# → Open http://localhost:3001/tools/my-tool
```

That's it! The dashboard auto-generates the form, handles streaming, persists history,
and manages usage limits — all from your single tool definition file.

## Tool Definition Reference

### `ToolDefinition` Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | ✅ | URL-safe kebab-case identifier |
| `name` | `string` | ✅ | Display name shown in sidebar & dashboard |
| `description` | `string` | ✅ | One-line description |
| `category` | `ToolCategory` | ✅ | Groups the tool in the sidebar |
| `icon` | `string` | ✅ | [Lucide icon](https://lucide.dev/icons) name |
| `status` | `"active" \| "coming-soon"` | ✅ | Set to `"active"` |
| `defaultModel` | `string` | ✅ | Oxlo model ID to use by default |
| `requiredFields` | `string[]` | ✅ | Input keys that must have values |
| `buildSystemPrompt` | `(inputs) => string` | ✅ | Builds the system prompt from user inputs |
| `buildUserPrompt` | `(inputs) => string` | ✅ | Builds the user prompt from user inputs |
| `inputs` | `InputFieldConfig[]` | ✅ | Form field definitions |
| `tier` | `"tier2"` | ❌ | Only set for Python-backed tools |

### Input Field Types

| Type | Renders As | Use Case |
|---|---|---|
| `text` | Single-line input | Short values (names, numbers) |
| `textarea` | Multi-line textarea | Code, descriptions, long text |
| `select` | Dropdown menu | Fixed option lists |
| `image` | File picker + preview | Image upload (base64 encoded) |

### Available Categories

| Key | Display Name |
|---|---|
| `developer` | Developer Tools |
| `data` | Data & API |
| `documentation` | Docs & Text |
| `design` | Design & Visual |
| `devops` | DevOps & System |
| `content` | Content & Marketing |

## Enabling Visual Previews

If your tool generates HTML output, the ResultViewer will automatically detect it and show a
**Preview / Code** toggle. To enable this:

1. **For tools generating full HTML pages**: Make your system prompt instruct the AI to output
   a complete `<!DOCTYPE html>` document. The viewer will detect it and render in an iframe.

2. **For tools generating Mermaid diagrams**: Output a fenced `mermaid` code block. The viewer
   will auto-render the diagram as an interactive SVG.

Example system prompt for HTML preview:

```typescript
buildSystemPrompt: () =>
  `You MUST output a single complete HTML file starting with <!DOCTYPE html>.
   Load Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>.
   The HTML must be self-contained and visually stunning.`,
```

## Tips for Great Tool Prompts

1. **Be specific** — vague prompts produce vague results
2. **Set boundaries** — tell the AI what NOT to include
3. **Use the framework field** — let users choose their preferred stack
4. **Test with multiple models** — different models handle prompts differently
5. **Pick the right default model** — use faster models for simple tools, reasoning models for complex ones

## Available Models (Oxlo Catalog)

| Model | Best For |
|---|---|
| `llama-3.3-70b` | General purpose, fast |
| `deepseek-r1-0528` | Complex reasoning, code |
| `qwen-3-coder-30b` | Code generation |
| `kimi-k2.5` | Creative, design tasks |
| `gemini-2.5-flash` | Fast, structured output |
