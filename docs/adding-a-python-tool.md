# Adding a Python Tool to Oxtools

## Overview

Python tools run in the **Unified Python Tool Runner** — a single Docker container
that auto-discovers tools from directories. Each tool gets its own directory with
full freedom to organize files however they want.

```
services/python-tools/
├── runner.py              ← Auto-discovers all tools (don't touch)
├── Dockerfile             ← One container for ALL tools
├── requirements.txt       ← Base runner deps
└── tools/
    ├── _template/         ← Copy this to start a new tool
    │   ├── tool.py
    │   └── requirements.txt
    ├── deep-research/     ← Example: multi-file tool
    │   ├── tool.py        ← Entry point (MANIFEST + run)
    │   ├── agents.py      ← Agent logic
    │   ├── prompts.py     ← Prompt templates
    │   ├── config.py      ← Configuration
    │   └── requirements.txt
    └── your-tool/         ← Your new tool goes here!
        ├── tool.py        ← Entry point (required)
        ├── helpers.py     ← Your helper modules
        ├── data/          ← Your data files
        └── requirements.txt
```

## Quick Start (5 minutes)

### 1. Copy the template

```bash
cp -r services/python-tools/tools/_template services/python-tools/tools/my-tool
```

### 2. Edit `tool.py`

Every tool needs exactly **2 things** in `tool.py`:

```python
# services/python-tools/tools/my-tool/tool.py

# 1. MANIFEST — describes your tool
MANIFEST = {
    "id": "my-tool",                    # URL-safe ID
    "name": "My Tool Name",
    "description": "One-line description",
    "author": "Your Name",
    "version": "1.0.0",
}

# 2. run() — executes your tool
async def run(data: dict) -> dict:
    query = data.get("query", "")
    # Your logic here...
    return {"result": f"Processed: {query}"}
```

### 3. Add helper files (optional)

You can add **any files** to your tool directory. Import them normally:

```python
# tool.py
from helpers import process_data       # → my-tool/helpers.py
from utils.parser import parse         # → my-tool/utils/parser.py
from config import API_KEY             # → my-tool/config.py
```

### 4. Add dependencies

List your pip packages in `requirements.txt`:

```
# services/python-tools/tools/my-tool/requirements.txt
openai==1.30.0
beautifulsoup4==4.12.0
```

Auto-installed when Docker builds.

### 5. Register in Next.js frontend

```typescript
// app/src/lib/tools/my-tool.ts
import type { ToolDefinition } from "@/types";

export const myTool: ToolDefinition = {
  id: "my-tool",             // Must match MANIFEST.id
  name: "My Tool Name",
  description: "What it does",
  category: "developer",     // developer | data | documentation | design | devops | content
  icon: "Wrench",            // Lucide icon name
  status: "active",
  tier: "tier2",             // Routes to the Python runner

  defaultModel: "llama-3.3-70b",
  requiredFields: ["query"],
  buildSystemPrompt: () => "",
  buildUserPrompt: ({ query }) => query,

  inputs: [
    {
      key: "query",
      label: "Input",
      type: "textarea",
      placeholder: "Enter your input...",
      rows: 4,
    },
  ],
};
```

Then add to `app/src/lib/tools/registry.ts`:

```typescript
import { myTool } from "./my-tool";
export const tools: ToolDefinition[] = [/* ...existing */, myTool];
```

### 6. Test locally

```bash
# Start the runner
docker compose -f docker-compose.dev.yml up --build

# Start Next.js
cd app && npm run dev

# Test your tool directly
curl -X POST http://localhost:9080/api/tools/my-tool \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'

# Or through the Next.js proxy
curl -X POST http://localhost:3001/api/tools/my-tool \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

## Streaming (for long-running tools)

For tools that take time (AI agents, research, etc.), return an async generator:

```python
async def run(data: dict):
    yield "[step-1] Planning...\n"
    # ... do work ...
    yield "[step-2] Searching...\n"
    # ... do work ...
    yield "\n---RESULT---\n"
    yield "Final output here"
```

## Environment Variables

Available to all tools via `os.getenv()`:

| Variable | Description |
|----------|-------------|
| `OXLO_API_KEY` | API key for Oxlo.ai models |
| `OXLO_BASE_URL` | Oxlo API base URL |
| `TAVILY_API_KEY` | (Optional) For web search |

## Architecture

```
User → Next.js (port 3001)
         ├── Tier 1 tools → Oxlo API (direct LLM call)
         └── Tier 2 tools → Python Runner (port 9080)
                              ├── /api/tools/deep-research  → deep-research/tool.py
                              ├── /api/tools/my-tool         → my-tool/tool.py
                              └── auto-discovers all tools/*/tool.py
```

**Key benefit**: ONE Docker container, ONE port, unlimited tools.
Each tool is a clean, self-contained directory.
