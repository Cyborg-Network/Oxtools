"""
Log Analyzer Tool — Oxtools Backend
=====================================
Analyzes system logs, identifies root causes, error patterns,
and recommends fixes. Called by the VS Code Log Analyzer extension.

Runner contract:
  - run(data) must be a regular async coroutine (not an async generator).
  - For streaming, return an async generator object from inside run().
  - For a one-shot result, return a plain dict {"result": "..."}.
"""

import os
import json

MANIFEST = {
    "id": "log-analyzer",
    "name": "System Log Analyzer",
    "description": "Analyze server/app logs for root causes, error patterns, and recommended fixes.",
    "author": "Oxtools",
    "version": "1.0.0",
}

SYSTEM_PROMPT = (
    "You are a senior DevOps/SRE engineer analyzing system logs. Provide:\n\n"
    "1. **Severity Assessment** - Critical / Warning / Info — how urgent is this?\n"
    "2. **Error Summary** - List each unique error type with occurrence count\n"
    "3. **Root Cause Analysis** - What is most likely causing these errors?\n"
    "4. **Timeline** - When did the issue start? Is it escalating or stable?\n"
    "5. **Pattern Detection** - Are errors correlated? Time-based patterns? Cascading failures?\n"
    "6. **Recommended Fixes** - Specific, actionable steps to resolve each issue\n"
    "7. **Prevention** - Configuration or monitoring changes to prevent recurrence\n\n"
    "Format as structured markdown. Use tables for error summaries. "
    "Highlight critical items with ⚠️."
)


async def run(data: dict):
    """
    Entry point called by runner.py as:  result = await run(data)

    Returns either:
      - An async generator  (runner will stream it)
      - A dict              (runner will return as JSON)
    """
    logs    = data.get("logs", "").strip()
    context = data.get("context", "").strip()
    model   = data.get("model", "deepseek-r1-0528")

    if not logs:
        return {"result": "⚠️ No logs provided to analyze."}

    api_key  = os.getenv("OXLO_API_KEY", "")
    base_url = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")

    if not api_key:
        return {
            "result": (
                "⚠️ OXLO_API_KEY is not set in the environment.\n\n"
                "Please add it to your `.env` file and restart the container."
            )
        }

    user_prompt = ""
    if context:
        user_prompt += f"**CONTEXT:** {context}\n\n"
    user_prompt += (
        f"**SYSTEM LOGS:**\n```\n{logs}\n```\n\n"
        "Analyze these logs and identify all issues."
    )

    # Return a streaming async generator — the runner handles it correctly
    return _stream(api_key, base_url, model, user_prompt)


async def _stream(api_key: str, base_url: str, model: str, user_prompt: str):
    """
    Async generator that streams OpenAI-compatible SSE chunks.
    Returned (not yielded from) by run() so the runner can await run()
    and then iterate over the result with `async for`.
    """
    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        obj   = json.loads(chunk)
                        delta = obj["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue

    except Exception as exc:
        yield json.dumps({"result": f"⚠️ Analysis failed: {exc}"}) + "\n"
