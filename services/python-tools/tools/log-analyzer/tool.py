
import json
import os
from typing import AsyncGenerator

from core.pipeline import Pipeline
from core.llm_client import OxloClient
from core.report import assemble_report

MANIFEST = {
    "id": "log-analyzer",
    "name": "System Log Analyzer",
    "description": "Analyze server/app logs for root causes, error patterns, and recommended fixes.",
    "author": "Oxtools",
    "version": "1.0.0",
}


async def _stream(
    logs: str,
    context: str,
    model: str,
    api_key: str,
    report_mode: str = "detailed",
) -> AsyncGenerator[str, None]:
    try:
        pipeline = Pipeline()
        result = pipeline.run(raw_text=logs, user_query=context)

        client = OxloClient(api_key=api_key)

        rca = await client.analyze_with_model(
            payload_json=json.dumps(result.compressed),
            user_query=context,
            model=model,
            report_type=report_mode,
            raw_log_excerpt=result.raw_log_excerpt,
        )

        final_markdown = assemble_report(result, rca, report_mode)

        yield "---\n\n"
        yield final_markdown

    except Exception as exc:
        yield f"\n\n⚠️ **Pipeline Error:** {exc}\n"


async def run(data: dict):
    """
    Entry point called by the runner as:  result = await run(data)

    Returns either:
      - An async generator  (runner will stream it)
      - A dict              (runner will return as JSON)
    """
    logs    = data.get("logs", "").strip()
    context = data.get("context", "").strip()
    model   = data.get("model", "deepseek-r1-0528")

    # Normalise report_mode — .get() only uses the default for *missing* keys,
    # not for None values (which a select sends when nothing is explicitly chosen).
    _raw_mode   = (data.get("report_mode") or "").strip()
    report_mode = "fix_only" if _raw_mode == "fix_only" else "detailed"

    if not logs:
        return {"result": "⚠️ No logs provided to analyze."}

    api_key = os.getenv("OXLO_API_KEY", "")

    if not api_key:
        return {
            "result": (
                "⚠️ OXLO_API_KEY is not set in the environment.\n\n"
                "Please add it to your `.env` file and restart the container."
            )
        }

    return _stream(logs, context, model, api_key, report_mode)