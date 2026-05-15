import json

from llm_client import call_oxlo_chat

WRITER_MODEL = "llama-3.3-70b"

ALLOWED_SECTIONS = {
    "Title",
    "Badges",
    "Description",
    "Features",
    "Quick Start",
    "Usage",
    "API Reference",
    "Config",
    "Contributing",
    "License",
    "Installation",
}

DEFAULT_SECTIONS = ["Title", "Description", "Installation", "Usage", "License"]


def _sanitize(value: str, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


def _sanitize_section_plan(section_plan: list) -> list:
    if not isinstance(section_plan, list) or not section_plan:
        return []
    cleaned = []
    seen = set()
    for section in section_plan:
        if not isinstance(section, str):
            continue
        section = section.strip()
        if section in ALLOWED_SECTIONS and section not in seen:
            cleaned.append(section)
            seen.add(section)
    return cleaned


async def write_readme(metadata: dict, section_plan: list) -> str:
    section_plan = _sanitize_section_plan(section_plan)
    if not section_plan:
        section_plan = DEFAULT_SECTIONS
    package_manager = _sanitize((metadata or {}).get("package_manager", "unknown"))
    language = _sanitize((metadata or {}).get("language", "unknown"))
    framework = _sanitize((metadata or {}).get("framework", "unknown"))
    entry_point = _sanitize((metadata or {}).get("entry_point", "unknown"))

    metadata_block = json.dumps(
        {
            "package_manager": package_manager,
            "language": language,
            "framework": framework,
            "entry_point": entry_point,
        },
        ensure_ascii=False,
    )

    system_prompt = (
        "You are a technical writer. Generate a complete README.md in markdown.\n"
        "Include ALL of these sections in order: "
        + ", ".join(section_plan)
        + ".\n"
        f"<project_metadata>{metadata_block}</project_metadata>\n"
        "Use the metadata above to pick correct install commands and examples. "
        "All shields.io badge URLs must start with https://img.shields.io/. "
        "All code blocks must have a language identifier (```python, ```bash, etc.). "
        "Return only the README markdown."
    )

    user_prompt = (
        "Write the README now. Use the metadata above to pick correct install "
        "commands and examples. Ensure sections are present and properly titled."
    )

    return await call_oxlo_chat(
        WRITER_MODEL,
        system_prompt,
        user_prompt,
        max_tokens=4096,
        temperature=0.3,
    )
