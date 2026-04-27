"""
Oxtools AI PR Review Agent
Uses Kimi K2.6 via Azure Foundry (OpenAI-compatible API) to review pull requests.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.error


def get_env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        print(f"::warning::Missing environment variable: {key}")
    return val


def github_api(path: str, method: str = "GET", data: dict | None = None) -> dict:
    token = get_env("GITHUB_TOKEN")
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"::error::GitHub API error {e.code}: {e.read().decode()}")
        sys.exit(1)


def get_pr_diff(repo: str, pr_number: int) -> str:
    token = get_env("GITHUB_TOKEN")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        print(f"::error::Failed to fetch diff: {e.code}")
        return ""


def sanitize_diff(diff: str) -> str:
    """Remove potential secrets from diff before sending to LLM."""
    patterns = [
        r'(?i)(api[_-]?key|secret|password|token|credential)\s*[=:]\s*["\']?[A-Za-z0-9+/=_\-]{8,}["\']?',
        r'(?i)(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}',  # AWS keys
        r'sk-[A-Za-z0-9]{20,}',  # OpenAI keys
        r'ghp_[A-Za-z0-9]{36}',  # GitHub PATs
    ]
    sanitized = diff
    for pattern in patterns:
        sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized)
    return sanitized


def truncate_diff(diff: str, max_chars: int = 60000) -> str:
    """Truncate diff to fit within token limits."""
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n... [DIFF TRUNCATED - too large for review] ..."


def call_kimi(prompt: str, system_prompt: str) -> str:
    """Call Kimi K2.6 via Azure Foundry OpenAI-compatible API."""
    endpoint = get_env("AZURE_AI_ENDPOINT")
    api_key = get_env("AZURE_AI_KEY")

    if not endpoint or not api_key:
        return "⚠️ AI review unavailable: Azure AI credentials not configured."

    # Ensure endpoint ends with /openai/v1 for OpenAI compatibility
    base_url = endpoint.rstrip("/")
    if not base_url.endswith("/openai/v1"):
        base_url = base_url + "/openai/v1"

    url = f"{base_url}/chat/completions"

    payload = {
        "model": "Kimi-K2.6",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 16384,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"::error::Kimi API error {e.code}: {error_body}")
        return f"⚠️ AI review failed (HTTP {e.code}). The team will review manually."
    except Exception as e:
        print(f"::error::Kimi API exception: {e}")
        return f"⚠️ AI review failed: {e}"


def post_review_comment(repo: str, pr_number: int, body: str) -> None:
    """Post a comment on the PR."""
    github_api(
        f"/repos/{repo}/issues/{pr_number}/comments",
        method="POST",
        data={"body": body},
    )


SYSTEM_PROMPT = """You are OxBot, the official AI code reviewer for the Oxtools open-source project.
Oxtools is a collection of developer tools powered by the Oxlo.ai inference API.

Your job is to review pull requests thoroughly and provide actionable feedback.
You are helpful, constructive, and security-conscious.

## Repository Structure
- `app/` — Next.js frontend (TypeScript, React, TailwindCSS)
- `services/python-tools/` — Python tool runner and individual tools
- `projects/` — Community-contributed tool projects
- `tests/` — Benchmark and test suites
- `.github/` — CI/CD workflows and templates

## Review Checklist (for contributor PRs under projects/)
1. **Structure**: Project in own directory under `projects/[name]/`
2. **Required Files**: Dockerfile, docker-compose.yml, oxlo-manifest.json, .env.example, README.md
3. **Security**: No hardcoded API keys, secrets, or credentials anywhere
4. **Oxlo API**: At least one functional call using OXLO_API_KEY env var
5. **Code Quality**: Clean code, proper error handling, no obvious bugs

## Review Checklist (for all PRs)
1. **Security**: No secrets leaked, no dangerous patterns (eval, exec without sanitization)
2. **Logic**: Code logic is correct and handles edge cases
3. **Performance**: No obvious performance issues (N+1 queries, memory leaks)
4. **Style**: Follows existing code conventions
5. **Breaking Changes**: Flag any breaking changes clearly

## Output Format
Structure your review as:
1. **Summary** — What does this PR do? (2-3 sentences)
2. **Security** — Any security concerns? (✅ or ⚠️ with details)
3. **Code Quality** — Logic issues, bugs, or improvements
4. **Suggestions** — Specific actionable improvements (with file:line references)
5. **Verdict** — One of: ✅ LGTM, ⚠️ NEEDS CHANGES, 🚨 CRITICAL ISSUES

Be concise. Use bullet points. Reference specific files and line numbers."""


def build_review_prompt(pr_info: dict, diff: str) -> str:
    title = pr_info.get("title", "")
    body = pr_info.get("body", "") or ""
    author = pr_info.get("user", {}).get("login", "unknown")
    base = pr_info.get("base", {}).get("ref", "")
    head = pr_info.get("head", {}).get("ref", "")
    changed_files = pr_info.get("changed_files", 0)
    additions = pr_info.get("additions", 0)
    deletions = pr_info.get("deletions", 0)

    return f"""## Pull Request Review Request

**Title:** {title}
**Author:** @{author}
**Branch:** {head} → {base}
**Stats:** {changed_files} files changed, +{additions} -{ deletions}

### PR Description
{body[:2000] if body else "No description provided."}

### Diff
```diff
{diff}
```

Please review this pull request following your checklist and provide your structured review."""


def main():
    event_path = get_env("GITHUB_EVENT_PATH")
    repo = get_env("GITHUB_REPOSITORY")

    if not event_path or not repo:
        print("::error::Missing required GitHub context")
        sys.exit(1)

    with open(event_path) as f:
        event = json.load(f)

    pr_number = event.get("pull_request", {}).get("number")
    if not pr_number:
        print("::warning::No PR number found in event")
        sys.exit(0)

    print(f"OxBot: reviewing PR #{pr_number}...")

    # Get PR details
    pr_info = github_api(f"/repos/{repo}/pulls/{pr_number}")

    # Get diff
    raw_diff = get_pr_diff(repo, pr_number)
    if not raw_diff:
        print("::warning::Empty diff, skipping review")
        sys.exit(0)

    # Sanitize and truncate
    safe_diff = sanitize_diff(raw_diff)
    final_diff = truncate_diff(safe_diff)

    # Build prompt and call LLM
    prompt = build_review_prompt(pr_info, final_diff)
    review = call_kimi(prompt, SYSTEM_PROMPT)

    # Format the comment
    comment = f"""## OxBot Review

{review}

---
<sub>Automated code review by OxBot</sub>
"""

    # Post comment
    post_review_comment(repo, pr_number, comment)
    print(f"OxBot: review posted on PR #{pr_number}")


if __name__ == "__main__":
    main()
