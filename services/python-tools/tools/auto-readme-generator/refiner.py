from typing import Callable, Optional

from llm_client import call_oxlo_chat
from validator import validate_readme

REFINER_MODEL = "llama-3.3-70b"


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
        system_prompt = (
            "You are a technical writer. Fix the README to resolve the listed issues. "
            "Return the full corrected README only."
        )
        user_prompt = (
            f"Issues to fix:\n{issue_summary}\n\n"
            f"README:\n{content}\n\n"
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
