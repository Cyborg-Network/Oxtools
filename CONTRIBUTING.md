# Contributing to the Oxtools Ecosystem

Welcome to **Oxtools**, the official integration hub for the **Cyborg Network**. We are thrilled to have you build alongside us.

To maintain the security, functionality, and professional grade of this repository, all contributors—whether you are a core engineer, an intern, or a hackathon participant—must adhere to the strict engineering protocols outlined in this document. 

Submissions that do not meet these baseline requirements will not pass the automated CI/CD checks and will be closed by the core maintainers pending revision.

---

## 🏗️ Phase 1: The Monorepo Architecture

Oxtools operates as a monorepo. This means multiple independent applications live within this single repository.

1. **Isolation:** Your entire project—including all source code, assets, and documentation—must be contained within a single, newly created directory inside the `projects/` folder.
2. **Naming:** Name your directory clearly based on its function (e.g., `projects/pdf-summarizer/` or `projects/defi-agent/`).

**❌ Incorrect:** Placing your files directly in the root of the repository.
**✅ Correct:** `Oxtools/projects/[your-project-name]/src/...`

---

## 🛡️ Phase 2: Mandatory Engineering Standards

Before you even open a Pull Request, your project directory must contain the following components:

### 1. Zero-Trust Security Protocol
Under no circumstances should API keys, private keys, or wallet seed phrases be committed to this repository.
* You **must** utilize environment variables for all sensitive data.
* You **must** include a `.env.example` file in your project directory that lists the required variables with blank values (e.g., `OXLO_API_KEY=`).
* Ensure `.env` is securely listed in your project's `.gitignore` file.

### 2. Project-Level Documentation
Your project folder must contain its own dedicated `README.md`. It must clearly explain:
* **Overview:** A 2-3 sentence summary of what the tool does and how it utilizes the Oxlo API.
* **Prerequisites:** Any required software (e.g., Node v18, Python 3.10).
* **Local Setup:** Exact, copy-pasteable terminal commands to install dependencies, set environment variables, and run the application locally.

### 3. Reproducibility & Dependencies
Core maintainers must be able to run your project locally to verify it. You must include strict dependency tracking files:
* **Node.js:** `package.json` (and `package-lock.json` or `yarn.lock`)
* **Python:** `requirements.txt` or `Pipfile`
* **Rust:** `Cargo.toml` and `Cargo.lock`

---

## 🚀 Phase 3: The Submission Pipeline

We operate on a strict **Fork & Pull Request** model. Direct pushes to the `main` branch are restricted.

### Step-by-Step Submission Workflow:
1. **Fork:** Click the "Fork" button in the top right of the `Oxtools` repository to create a copy under your personal GitHub account.
2. **Clone:** Clone your fork to your local machine.
3. **Branch:** Create a new branch for your feature. Use standard naming conventions:
   * `git checkout -b feat/your-project-name`
4. **Develop:** Build your application inside the `projects/` directory according to the standards above.
5. **Commit:** Write clean, descriptive commit messages.
6. **Push:** Push the branch to your personal fork on GitHub.
7. **Pull Request:** Open a PR against the `main` branch of the official `Cyborg-Network/Oxtools` repository.

---

## 🔎 Phase 4: The Audit Process

When you open a Pull Request, you will be prompted to fill out a mandatory W3F-style checklist. **You must provide a link to a live demo or a screen recording (Loom/YouTube) of your prototype in action.**

A Cyborg Network core engineer will audit your submission. We evaluate based on:
1. **Oxlo API Integration:** Is the API utilized securely and efficiently?
2. **Code Quality:** Is the codebase modular, legible, and properly formatted?
3. **Execution:** Does the code run perfectly following your exact `README.md` instructions?

If your PR requires changes, a maintainer will leave comments. Address them, push the fixes to your branch, and the PR will automatically update. 

Once your code passes the audit, it will be merged, and you will officially become an Oxtools Ecosystem contributor!