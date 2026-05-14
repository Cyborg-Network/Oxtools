from typing import Callable, Optional

from llm_client import call_oxlo_chat
from validator import validate_readme

REFINER_MODEL = "llama-3.3-70b"


def _sanitize(value: str, max_len: int = 12000) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


async def refine_readme(
    content: str,
    issues: list,
    metadata: dict,
    section_plan: list,
    call_model: Optional[Callable[[str, str, str, int, float], str]] = None,
) -> str:
    call_model = call_model or call_oxlo_chat

    for attempt in range(2):
        issue_summary = "\n".join(
            f"- [{item['type']}] {item['detail']}" for item in issues
        )
        safe_issue_summary = _sanitize(issue_summary, max_len=2000)
        safe_content = _sanitize(content, max_len=20000)
        system_prompt = (
            "You are a technical writer. Fix the README to resolve the listed issues. "
            "Return the full corrected README only."
        )
        user_prompt = (
            f"Issues to fix:\n{safe_issue_summary}\n\n"
            f"README:\n{safe_content}\n\n"
            "Ensure all required sections are present, badges use https://img.shields.io/, "
            "and code fences include a language tag."
        )

        content = await call_model(
            REFINER_MODEL,
            system_prompt,
            user_prompt,
            4096,
            0.2,
        )

        issues = validate_readme(content, section_plan, metadata)
        if not issues:
            break

    return content
