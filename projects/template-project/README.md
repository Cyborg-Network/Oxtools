# [Your Project Name]

> Powered by [Oxlo.ai](https://oxlo.ai)

Replace this paragraph with a 2–3 sentence description of your tool. Explain what problem it solves and how it interacts with the Oxlo API. Be specific — "summarizes PDFs using the Oxlo inference API" is better than "an AI-powered document tool."

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An active Oxlo API key — get one at [oxlo.ai/dashboard](https://oxlo.ai/dashboard)

## Local setup

**1. Clone the repo and navigate to your project:**
```bash
git clone https://github.com/Cyborg-Network/Oxtools.git
cd Oxtools/projects/your-project-name
```

**2. Create your environment file:**
```bash
cp .env.example .env
```
Open `.env` and paste your `OXLO_API_KEY`.

**3. Start the container:**
```bash
docker compose up --build
```

The application will be available at `http://localhost:3000` (or whichever port you configured).

**4. Stop the container:**
```bash
docker compose down
```

## Demo

[Insert a link to a Loom or YouTube recording of the tool running here]

## Tech stack

List the language(s) and frameworks used in this project.