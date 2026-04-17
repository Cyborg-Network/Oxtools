# Contributing to Oxtools

Thanks for your interest in contributing! This document explains how to add tools, the requirements every submission must meet, and the PR process.

Read this in full before you open a Pull Request.

---

## 1. Repository Structure

Oxtools is a monorepo with two main components:

```
Oxtools/
├── app/                          # Next.js 16 dashboard (frontend)
│   └── src/lib/tools/            # Tool definitions live here
├── services/
│   └── python-tools/             # Unified Python Tool Runner (Tier 2)
│       └── tools/                # Python tool implementations live here
├── docs/                         # Contributing guides
└── CONTRIBUTING.md               # This file
```

**There are two types of tools:**

| Type | Where it lives | When to use |
|---|---|---|
| **Tier 1 (Frontend)** | `app/src/lib/tools/my-tool.ts` | Pure LLM prompt - no custom backend needed |
| **Tier 2 (Python)** | `services/python-tools/tools/my-tool/` | Needs custom logic, libraries, or multi-step agents |

---

## 2. Choosing the right tier

**Use Tier 1** if your tool:
- Sends a prompt to an LLM and returns the response
- Doesn't need special libraries (Playwright, BeautifulSoup, etc.)
- Can be defined entirely as system + user prompt engineering

**Use Tier 2** if your tool:
- Needs Python libraries (computer vision, web scraping, etc.)
- Runs multi-step agent workflows (LangGraph, etc.)
- Requires file processing beyond text (images, PDFs, etc.)

---

## 3. Step-by-step guides

Detailed guides with code examples:

- **Tier 1 (Frontend):** [`docs/adding-a-frontend-tool.md`](./docs/adding-a-frontend-tool.md)
- **Tier 2 (Python):** [`docs/adding-a-python-tool.md`](./docs/adding-a-python-tool.md)

---

## 4. Naming conventions

- **Tool ID:** kebab-case, descriptive (`pdf-summarizer`, not `johns-cool-bot`)
- **File names:** Match the tool ID (`pdf-summarizer.ts` or `pdf-summarizer/tool.py`)
- **Branch names:** `feat/tool-name` (e.g., `feat/pdf-summarizer`)

---

## 5. Security rules

**No hardcoded API keys or secrets - ever.**

- Use environment variables for all credentials.
- Check your diff before pushing: `git diff --stat` and `git grep -i "api_key"`.
- If you accidentally commit a secret, rotate the key immediately and rewrite the Git history.
- Add any new required env vars to `.env.example`.

Submissions with hardcoded secrets will be closed without review.

---

## 6. Submission process

We use a standard Fork & Pull Request workflow.

```
1. Fork the Cyborg-Network/Oxtools repository on GitHub.
2. Clone your fork locally.
3. Create a feature branch:
      git checkout -b feat/your-tool-name
4. Add your tool following the appropriate guide (Tier 1 or Tier 2).
5. Test locally - make sure it builds and runs.
6. Commit with a clear message:
      git commit -m "feat: add pdf-summarizer tool"
7. Push to your fork:
      git push origin feat/your-tool-name
8. Open a Pull Request against main on Cyborg-Network/Oxtools.
```

---

## 7. PR checklist

Before opening your PR, verify:

- [ ] Tool works locally (`npm run dev` for Tier 1, `docker compose up` for Tier 2)
- [ ] Tool ID matches across frontend definition and backend manifest (Tier 2)
- [ ] Tool is registered in `app/src/lib/tools/registry.ts`
- [ ] No hardcoded API keys or secrets in the diff
- [ ] `.env.example` updated if new env vars are needed
- [ ] Tool has a clear name, description, and appropriate category

---

## 8. Review process

A maintainer will review your submission and check:

1. **Does it work?** - The tool must produce correct results.
2. **Is it well-prompted?** - System prompts should be specific and well-structured.
3. **Are there secrets in the diff?** - Automated and manual checks both run.
4. **Does it fit?** - The tool should be genuinely useful to developers.

If changes are needed, the reviewer will leave comments. Push fixes to the same branch.

Once approved, your PR will be merged and your tool goes live in Oxtools!