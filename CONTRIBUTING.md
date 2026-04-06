# Contributing to Oxtools

Thanks for your interest in contributing. This document explains the requirements every submission must meet and the process for getting your PR merged.

Read this in full before you open a Pull Request. Submissions that are missing required files will be closed with a checklist of what needs to be fixed.

---

## 1. Folder structure

Oxtools is a monorepo. Every project lives in its own isolated directory under `projects/`.

```
Oxtools/
└── projects/
    └── your-project-name/
        ├── src/                  # Your application source code
        ├── Dockerfile            # Required
        ├── docker-compose.yml    # Required
        ├── oxlo-manifest.json    # Required
        ├── .env.example          # Required
        └── README.md             # Required
```

**Rules:**
- One project per directory — do not nest multiple tools in the same folder.
- Name your directory after what the tool does, not after yourself (e.g., `pdf-summarizer`, not `johns-cool-bot`).
- Do not place any project files in the root of the repository.

The fastest way to get started is to copy `projects/template-project/` and rename it.

---

## 2. Required files

Every submission must include the following five files. PRs missing any of them will not be reviewed.

### `Dockerfile`

Your project must be containerized. The `Dockerfile` must produce a working image — maintainers will run `docker build` as part of the review.

Use `projects/template-project/Dockerfile` as your starting point. Comment your `Dockerfile` to explain any non-obvious setup steps.

### `docker-compose.yml`

Include a `docker-compose.yml` so reviewers can run your tool with a single command (`docker compose up`). Mount the `.env` file and map the appropriate port.

### `oxlo-manifest.json`

This file holds metadata about your tool. Copy the schema from `projects/template-project/oxlo-manifest.json` and fill it in:

```json
{
  "name": "your-tool-name",
  "description": "One sentence describing what this tool does.",
  "author": "your-github-handle",
  "tech_stack": ["python", "fastapi"],
  "port_number": 8000,
  "oxlo_api_used": true
}
```

All fields are required. `tech_stack` is an array — list the language and any major frameworks.

### `.env.example`

List every environment variable your project needs, with empty values. This file is committed to the repo so other developers know what to configure.

```bash
OXLO_API_KEY=
PORT=8000
```

Your actual `.env` file must never be committed. Verify that `.env` is in your project's `.gitignore` (or the root `.gitignore` already covers it).

### `README.md`

Write a project-level `README.md` inside your project directory. It must cover:

1. **What it does** — a plain 2–3 sentence description of the tool and how it uses the Oxlo API.
2. **Prerequisites** — any software a developer needs before running the tool locally.
3. **Local setup** — exact, copy-pasteable commands (clone, configure `.env`, run with Docker).
4. **Demo** — a link to a Loom or YouTube recording of the tool working.

---

## 3. Security rules

**No hardcoded API keys or secrets — ever.**

- Use environment variables for all credentials.
- Check your diff before pushing. Tools like `git diff --stat` and `git grep -i "api_key"` can catch accidental leaks.
- If you realize you have committed a secret, rotate the key immediately and rewrite the Git history before opening a PR.

Submissions with hardcoded secrets will be closed without review.

---

## 4. Submission process

We use a standard Fork & Pull Request workflow. Direct pushes to `main` are not permitted.

```
1. Fork the Cyborg-Network/Oxtools repository on GitHub.
2. Clone your fork locally.
3. Create a feature branch:
      git checkout -b feat/your-project-name
4. Build your project inside projects/your-project-name/.
5. Commit with a clear message:
      git commit -m "feat: add pdf-summarizer tool"
6. Push to your fork:
      git push origin feat/your-project-name
7. Open a Pull Request against main on Cyborg-Network/Oxtools.
```

---

## 5. Review process

When you open a PR, GitHub will automatically load the Pull Request template. Fill it out completely — including a demo link.

A maintainer will review your submission and check:

1. **Does it build?** — `docker build` and `docker compose up` must succeed.
2. **Does the Oxlo API integration work?** — The tool must demonstrably call the API.
3. **Are there any secrets in the diff?** — Automated and manual checks both run.
4. **Is the README accurate?** — The setup instructions will be followed exactly.

If changes are needed, the reviewer will leave comments on the PR. Push fixes to the same branch and the PR will update automatically.

Once the review is clear, your PR will be merged and your tool becomes part of the Oxtools ecosystem.