"""
Oxtools AI PR Review Agent
Posts inline code review comments on pull requests, similar to Cursor Bugbot.
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


def get_pr_files(repo: str, pr_number: int) -> list:
    """Get the list of changed files with their patch data."""
    return github_api(f"/repos/{repo}/pulls/{pr_number}/files")


def sanitize_diff(diff: str) -> str:
    """Remove potential secrets from diff before sending to LLM."""
    patterns = [
        r'(?i)(api[_-]?key|secret|password|token|credential)\s*[=:]\s*["\'`]?[A-Za-z0-9+/=_\-]{8,}["\'`]?',
        r'(?i)(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}',
        r'sk-[A-Za-z0-9]{20,}',
        r'ghp_[A-Za-z0-9]{36}',
    ]
    sanitized = diff
    for pattern in patterns:
        sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized)
    return sanitized


def truncate_diff(diff: str, max_chars: int = 80000) -> str:
    """Truncate diff to fit within token limits."""
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars] + "\n\n... [DIFF TRUNCATED - too large for review] ..."


def call_kimi(prompt: str, system_prompt: str) -> str:
    """Call Kimi K2.6 via Azure Foundry OpenAI-compatible API."""
    endpoint = get_env("AZURE_AI_ENDPOINT")
    api_key = get_env("AZURE_AI_KEY")

    if not endpoint or not api_key:
        return ""

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
        "temperature": 0.2,
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
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"::error::API error {e.code}: {error_body}")
        return ""
    except Exception as e:
        print(f"::error::API exception: {e}")
        return ""


def parse_diff_line_map(diff: str) -> dict:
    """Parse unified diff to map file paths to their diff line positions.
    Returns {filename: {new_line_number: diff_position}}
    """
    file_map = {}
    current_file = None
    position = 0
    new_line = 0

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            # Extract filename: diff --git a/path b/path
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
                file_map[current_file] = {}
                position = 0
                new_line = 0
        elif line.startswith("@@"):
            # Parse hunk header: @@ -old,count +new,count @@
            match = re.search(r"\+(\d+)", line)
            if match:
                new_line = int(match.group(1)) - 1
            position += 1
        elif current_file and position > 0:
            position += 1
            if line.startswith("+"):
                new_line += 1
                file_map[current_file][new_line] = position
            elif line.startswith("-"):
                pass  # Deleted lines don't get new line numbers
            else:
                new_line += 1
                file_map[current_file][new_line] = position

    return file_map


def post_inline_review(repo: str, pr_number: int, commit_sha: str,
                       summary: str, inline_comments: list) -> None:
    """Post a proper GitHub PR review with inline comments."""
    # Build review comments array
    comments = []
    for c in inline_comments:
        comment = {
            "path": c["path"],
            "body": f"**{c.get('severity', 'Note')}**: {c['body']}",
        }
        if c.get("line"):
            comment["line"] = c["line"]
            comment["side"] = "RIGHT"
        elif c.get("position"):
            comment["position"] = c["position"]
        else:
            continue
        comments.append(comment)

    review_body = f"## OxBot Review\n\n{summary}"
    if not comments:
        review_body += "\n\n_No inline issues found._"

    review_data = {
        "commit_id": commit_sha,
        "body": review_body,
        "event": "COMMENT",
        "comments": comments,
    }

    github_api(
        f"/repos/{repo}/pulls/{pr_number}/reviews",
        method="POST",
        data=review_data,
    )


SYSTEM_PROMPT = """You are OxBot, the code reviewer for the Oxtools open-source project.
You review pull requests and provide inline feedback on specific lines of code.

## Repository Structure
- `app/` - Next.js frontend (TypeScript, React, TailwindCSS)
- `services/python-tools/` - Python tool runner
- `projects/` - Community-contributed tool projects
- `.github/` - CI/CD workflows

## Your Review Focus
1. Security: No leaked secrets, no dangerous patterns (eval, exec, SQL injection)
2. Bugs: Logic errors, edge cases, null/undefined risks
3. Performance: Unnecessary re-renders, N+1 patterns, memory leaks
4. Best Practices: Error handling, type safety, code duplication

## CRITICAL: Output Format
You MUST respond with valid JSON only. No markdown, no explanation outside JSON.

{
  "summary": "2-3 sentence overall summary of the PR",
  "verdict": "LGTM | NEEDS_CHANGES | CRITICAL",
  "inline_comments": [
    {
      "path": "relative/path/to/file.ts",
      "line": 42,
      "severity": "Bug | Security | Performance | Suggestion",
      "body": "Clear, concise explanation of the issue and how to fix it."
    }
  ]
}

Rules:
- Only comment on genuinely important issues. Do NOT nitpick formatting or style.
- Each inline comment must reference a real file path and line number from the diff.
- The line number must be a line that was ADDED (prefixed with + in the diff).
- Keep comments actionable and specific. Explain WHY and suggest a fix.
- Maximum 10 inline comments. Focus on the most impactful issues.
- If the PR looks good, return an empty inline_comments array with verdict "LGTM".
- Do NOT comment on files under .github/ unless there are security issues."""


def build_review_prompt(pr_info: dict, diff: str) -> str:
    title = pr_info.get("title", "")
    body = pr_info.get("body", "") or ""
    author = pr_info.get("user", {}).get("login", "unknown")
    base = pr_info.get("base", {}).get("ref", "")
    head = pr_info.get("head", {}).get("ref", "")
    changed_files = pr_info.get("changed_files", 0)
    additions = pr_info.get("additions", 0)
    deletions = pr_info.get("deletions", 0)

    return f"""Review this pull request and respond with JSON only.

Title: {title}
Author: @{author}
Branch: {head} -> {base}
Stats: {changed_files} files changed, +{additions} -{deletions}

PR Description:
{body[:2000] if body else "No description provided."}

Diff:
```diff
{diff}
```"""


def main():
    event_path = get_env("GITHUB_EVENT_PATH")
    repo = get_env("GITHUB_REPOSITORY")

    if not event_path or not repo:
        print("::error::Missing required GitHub context")
        sys.exit(1)

    with open(event_path) as f:
        event = json.load(f)

    pr_data = event.get("pull_request", {})
    pr_number = pr_data.get("number")
    if not pr_number:
        print("::warning::No PR number found in event")
        sys.exit(0)

    commit_sha = pr_data.get("head", {}).get("sha", "")
    print(f"OxBot: reviewing PR #{pr_number} (commit {commit_sha[:7]})...")

    # Get PR details and diff
    pr_info = github_api(f"/repos/{repo}/pulls/{pr_number}")
    raw_diff = get_pr_diff(repo, pr_number)
    if not raw_diff:
        print("::warning::Empty diff, skipping review")
        sys.exit(0)

    # Build line position map for inline comments
    line_map = parse_diff_line_map(raw_diff)

    # Sanitize and truncate
    safe_diff = sanitize_diff(raw_diff)
    final_diff = truncate_diff(safe_diff)

    # Call LLM
    prompt = build_review_prompt(pr_info, final_diff)
    response = call_kimi(prompt, SYSTEM_PROMPT)

    if not response:
        # Fallback: post simple comment if API fails
        github_api(
            f"/repos/{repo}/issues/{pr_number}/comments",
            method="POST",
            data={"body": "## OxBot Review\n\nReview unavailable: API credentials not configured.\n\n---\n<sub>Automated code review by OxBot</sub>"},
        )
        print("OxBot: posted fallback comment (no API credentials)")
        return

    # Parse JSON response
    try:
        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        review = json.loads(cleaned)
    except json.JSONDecodeError:
        # If LLM didn't return valid JSON, post as general comment
        comment = f"## OxBot Review\n\n{response}\n\n---\n<sub>Automated code review by OxBot</sub>"
        github_api(
            f"/repos/{repo}/issues/{pr_number}/comments",
            method="POST",
            data={"body": comment},
        )
        print("OxBot: posted general comment (non-JSON response)")
        return

    # Process inline comments - resolve line numbers to diff positions
    inline_comments = []
    for c in review.get("inline_comments", []):
        path = c.get("path", "")
        line = c.get("line", 0)

        # Try to find the diff position for this line
        if path in line_map and line in line_map[path]:
            c["position"] = line_map[path][line]
            inline_comments.append(c)
        elif path in line_map:
            # Line not in diff, try closest line
            available_lines = sorted(line_map[path].keys())
            closest = min(available_lines, key=lambda x: abs(x - line), default=None)
            if closest and abs(closest - line) <= 5:
                c["line"] = closest
                c["position"] = line_map[path][closest]
                inline_comments.append(c)
            else:
                # Can't map to diff, skip this comment
                print(f"OxBot: skipping comment for {path}:{line} (not in diff)")
        else:
            print(f"OxBot: skipping comment for {path} (file not in diff)")

    # Build summary
    summary = review.get("summary", "No summary provided.")
    verdict = review.get("verdict", "COMMENT")
    verdict_display = {
        "LGTM": "Verdict: LGTM",
        "NEEDS_CHANGES": "Verdict: Needs Changes",
        "CRITICAL": "Verdict: Critical Issues Found",
    }.get(verdict, f"Verdict: {verdict}")

    full_summary = f"{summary}\n\n**{verdict_display}** | {len(inline_comments)} inline comment(s)\n\n---\n<sub>Automated code review by OxBot</sub>"

    # Post the review with inline comments
    post_inline_review(repo, pr_number, commit_sha, full_summary, inline_comments)
    print(f"OxBot: review posted on PR #{pr_number} with {len(inline_comments)} inline comments")


if __name__ == "__main__":
    main()
