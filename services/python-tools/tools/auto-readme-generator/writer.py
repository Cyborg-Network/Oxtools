from llm_client import call_oxlo_chat

WRITER_MODEL = "llama-3.3-70b"


async def write_readme(metadata: dict, section_plan: list) -> str:
    package_manager = (metadata or {}).get("package_manager", "unknown")
    language = (metadata or {}).get("language", "unknown")
    framework = (metadata or {}).get("framework", "unknown")
    entry_point = (metadata or {}).get("entry_point", "unknown")

    system_prompt = (
        "You are a technical writer. Generate a complete README.md in markdown. "
        "Include ALL of these sections in order: "
        + ", ".join(section_plan)
        + ". "
        f"Package manager: {package_manager}. "
        f"Language: {language}. "
        f"Framework: {framework}. "
        f"Entry point: {entry_point}. "
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
