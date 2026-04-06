<div align="center">
  <img src="./assets/oxlo-logo.png" alt="Oxlo.ai Logo" width="250" />
  <br><br>
  <img src="./assets/oxlo-banner.png" alt="Build AI. Pay LESS. Ship FASTER." width="600" />
  <br><br>

  <p>
    <a href="https://oxlo.ai"><img src="https://img.shields.io/badge/Powered%20By-Oxlo%20API-0052FF.svg" alt="Powered By: Oxlo API"></a>
    <a href="./CONTRIBUTING.md"><img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg" alt="Contributions: Welcome"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache 2.0"></a>
  </p>
</div>

---

**Oxtools** is the official community hub for open-source tools built on the [Oxlo.ai](https://oxlo.ai) API. If you've built something with Oxlo — an agent, a workflow, a utility — this is the right place to share it.

[Oxlo.ai](https://oxlo.ai) is a developer-first AI inference platform. It gives engineers access to large language models at meaningfully lower compute costs than mainstream alternatives.

## What lives here?

Every project in this repo is an independent, runnable tool submitted by a developer in the Oxlo community. Projects are organized under the `projects/` directory and are expected to work out of the box using Docker.

Common project types include:

- **Agents & Assistants** — tools that use LLMs to handle tasks autonomously
- **Data pipelines** — PDF parsers, document extractors, summarizers
- **Developer utilities** — API wrappers, boilerplates, middleware

## Repository layout

```
Oxtools/
├── .github/                  # PR templates and repo governance
├── assets/                   # Logos and banners
├── docs/                     # API references and additional documentation
├── projects/                 # All community-submitted tools live here
│   ├── template-project/     # Start here — copy this for your submission
│   │   ├── src/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── oxlo-manifest.json
│   │   ├── .env.example
│   │   └── README.md
│   └── [your-project-name]/
└── CONTRIBUTING.md           # Rules, structure requirements, and PR process
```

## Getting started as a contributor

1. Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) — it covers the rules, required files, and the PR process.
2. Copy `projects/template-project/` into a new folder under `projects/`.
3. Build your tool. Fill in the `oxlo-manifest.json` and write your own `README.md`.
4. Open a Pull Request against `main`.

There are no language or framework restrictions. Python, Node.js, Go, Rust — anything works, as long as it runs inside Docker and uses the Oxlo API.

## Standards at a glance

| Requirement | Details |
|---|---|
| Location | Your project must live in `projects/[your-project-name]/` |
| Docker | Must include a working `Dockerfile` and `docker-compose.yml` |
| Manifest | Must include `oxlo-manifest.json` |
| Secrets | No hardcoded API keys — use `.env.example` |
| Docs | Must include a `README.md` with local setup instructions |

## License

[Apache 2.0](./LICENSE)