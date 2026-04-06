## Oxtools Submission

**Project name:** [Your project name]
**Contributor:** [@your-github-handle]
**Demo:** [Link to Loom or YouTube recording — required]

---

### What does this tool do?

Write 2–3 sentences describing the tool, the problem it solves, and how it uses the Oxlo API.

---

### Submission checklist

*Check every box before requesting a review. Unchecked items will result in the PR being sent back.*

**Structure**
- [ ] My project is in its own directory under `projects/[my-project-name]/`
- [ ] I have not placed any files directly in the repository root

**Required files**
- [ ] `Dockerfile` is present and `docker build .` succeeds
- [ ] `docker-compose.yml` is present and `docker compose up` starts the app
- [ ] `oxlo-manifest.json` is present and all fields are filled in
- [ ] `.env.example` lists every environment variable the project needs (with empty values)
- [ ] `README.md` is present with setup instructions a reviewer can follow exactly

**Security**
- [ ] No API keys, private keys, or secrets are hardcoded anywhere in the codebase
- [ ] My actual `.env` file is not included in this PR
- [ ] I have verified my diff with `git grep -i "api_key"` and found no leaks

**Oxlo API**
- [ ] The tool makes at least one functional call to the Oxlo API
- [ ] The API key is read from the `OXLO_API_KEY` environment variable

---

### For maintainers

- [ ] Security scan passed — no secrets in diff
- [ ] `docker build .` succeeded locally
- [ ] `docker compose up` ran successfully and app is reachable
- [ ] Oxlo API integration verified
- [ ] Approved for merge