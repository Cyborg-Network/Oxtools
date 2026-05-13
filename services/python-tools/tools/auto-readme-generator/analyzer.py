import json
import re

from llm_client import call_oxlo_chat

ANALYZER_MODEL = "deepseek-v3.2"


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*", "", text)
        text = re.sub(r"```$", "", text.strip())
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


async def analyze_project(name: str, description: str, tech_stack: str) -> dict:
    system_prompt = (
        "You are a project analyzer. "
        "Respond ONLY with a JSON object. No markdown, no explanation."
    )
    user_prompt = (
        f"Project: {name}\n"
        f"Description: {description}\n"
        f"Tech stack: {tech_stack}\n\n"
        "Return JSON with keys: language, package_manager, framework, "
        "entry_point, project_type (library|cli|web-api|web-app|other)."
    )

    raw = await call_oxlo_chat(
        ANALYZER_MODEL,
        system_prompt,
        user_prompt,
        max_tokens=512,
        temperature=0.2,
    )

    cleaned = _extract_json(raw)
    return json.loads(cleaned)
