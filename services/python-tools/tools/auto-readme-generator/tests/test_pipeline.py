import asyncio

import analyzer
import refiner
import tool
import writer
from validator import validate_readme


async def _collect_stream(data: dict) -> str:
    stream = await tool.run(data)
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return "".join(chunks)


def _readme_web_api() -> str:
    return (
        "# Title\n"
        "## Badges\n"
        "![build](https://img.shields.io/badge/build-passing-green)\n"
        "## Description\n"
        "API service for auth.\n"
        "## Features\n"
        "- Login\n"
        "## Quick Start\n"
        "```bash\n"
        "pip install example\n"
        "```\n"
        "## Usage\n"
        "```bash\n"
        "python -m example\n"
        "```\n"
        "## API Reference\n"
        "See docs.\n"
        "## Config\n"
        "ENV vars.\n"
        "## Contributing\n"
        "PRs welcome.\n"
        "## License\n"
        "MIT\n"
    )


def _readme_other() -> str:
    return (
        "# Title\n"
        "## Description\n"
        "Simple tool.\n"
        "## Installation\n"
        "```bash\n"
        "pip install example\n"
        "```\n"
        "## Usage\n"
        "```bash\n"
        "example --help\n"
        "```\n"
        "## Contributing\n"
        "PRs welcome.\n"
        "## License\n"
        "MIT\n"
    )


def test_pipeline_happy_path(monkeypatch):
    async def fake_call_oxlo_chat(model, system_prompt, user_prompt, max_tokens=2048, temperature=0.3):
        if "project analyzer" in system_prompt.lower():
            return (
                "{"
                "\"language\": \"python\","
                "\"package_manager\": \"pip\","
                "\"framework\": \"fastapi\","
                "\"entry_point\": \"main.py\","
                "\"project_type\": \"web-api\""
                "}"
            )
        return _readme_web_api()

    monkeypatch.setattr(analyzer, "call_oxlo_chat", fake_call_oxlo_chat)
    monkeypatch.setattr(writer, "call_oxlo_chat", fake_call_oxlo_chat)
    monkeypatch.setattr(refiner, "call_oxlo_chat", fake_call_oxlo_chat)

    output = asyncio.run(
        _collect_stream(
            {
                "projectName": "fastapi-auth",
                "projectDescription": "Auth API with FastAPI",
                "techStack": "Python, FastAPI",
            }
        )
    )

    assert "---RESULT---" in output
    assert "[ERROR]" not in output


def test_pipeline_handles_malformed_analyzer_response(monkeypatch):
    async def fake_call_oxlo_chat(model, system_prompt, user_prompt, max_tokens=2048, temperature=0.3):
        if "project analyzer" in system_prompt.lower():
            return "not json"
        return _readme_other()

    monkeypatch.setattr(analyzer, "call_oxlo_chat", fake_call_oxlo_chat)
    monkeypatch.setattr(writer, "call_oxlo_chat", fake_call_oxlo_chat)
    monkeypatch.setattr(refiner, "call_oxlo_chat", fake_call_oxlo_chat)

    output = asyncio.run(
        _collect_stream(
            {
                "projectName": "unknown",
                "projectDescription": "Test",
                "techStack": "",
            }
        )
    )

    assert "---RESULT---" in output
    assert "[ERROR] Analyzer failed" not in output


def test_refiner_max_retries_returns_content():
    async def always_bad(model, system_prompt, user_prompt, max_tokens=2048, temperature=0.3):
        return "# Title\n```python\nprint('hi')\n"

    content = "# Title\n```python\nprint('hi')\n"
    metadata = {"package_manager": "npm"}
    section_plan = ["Title"]
    issues = validate_readme(content, section_plan, metadata)

    result = asyncio.run(
        refiner.refine_readme(
            content,
            issues,
            metadata,
            section_plan,
            call_model=always_bad,
        )
    )

    assert result
    assert validate_readme(result, section_plan, metadata)
