import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from llm_client import call_oxlo_chat

ANALYZER_MODEL = "deepseek-v3.2"

DEFAULT_METADATA = {
    "language": "unknown",
    "package_manager": "unknown",
    "framework": "unknown",
    "entry_point": "unknown",
    "project_type": "other",
}


class ProjectMetadata(BaseModel):
    language: str = "unknown"
    package_manager: str = "unknown"
    framework: str = "unknown"
    entry_point: str = "unknown"
    project_type: Literal["library", "cli", "web-api", "web-app", "other"] = "other"


def _sanitize(value: str, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*", "", text)
        text = re.sub(r"```$", "", text.strip())
    return text


def _parse_json(text: str) -> dict:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    return item
    except json.JSONDecodeError:
        pass

    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    return item

    return DEFAULT_METADATA.copy()


async def analyze_project(name: str, description: str, tech_stack: str) -> dict:
    safe_name = _sanitize(name)
    safe_description = _sanitize(description, max_len=2000)
    safe_tech_stack = _sanitize(tech_stack)

    system_prompt = (
        "You are a project analyzer. "
        "Respond ONLY with a JSON object. No markdown, no explanation."
    )
    project_data = json.dumps(
        {
            "name": safe_name,
            "description": safe_description,
            "tech_stack": safe_tech_stack,
        },
        ensure_ascii=False,
    )
    user_prompt = (
        f"Project data (JSON):\n{project_data}\n\n"
        "Return JSON with keys: language, package_manager, framework, "
        "entry_point, project_type (library|cli|web-api|web-app|other)."
    )

    try:
        raw = await call_oxlo_chat(
            ANALYZER_MODEL,
            system_prompt,
            user_prompt,
            max_tokens=512,
            temperature=0.2,
        )

        cleaned = _extract_json(raw)
        parsed = _parse_json(cleaned)
        return ProjectMetadata(**parsed).model_dump()
    except ValidationError:
        return DEFAULT_METADATA.copy()
    except Exception:
        return DEFAULT_METADATA.copy()
