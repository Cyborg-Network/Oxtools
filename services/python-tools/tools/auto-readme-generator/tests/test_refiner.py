import pytest

from refiner import refine_readme
from validator import validate_readme


async def _fake_call_model(model, system, user, max_tokens, temperature):
    return (
        "# Title\n"
        "![build](https://img.shields.io/badge/build-passing-green)\n"
        "# License\n"
        "```python\nprint('hi')\n```\n"
        "npm install\n"
    )


@pytest.mark.asyncio
async def test_refiner_resolves_issues():
    content = "# Title\n# License\n```\nraw code\n```\n"
    metadata = {"package_manager": "npm"}
    section_plan = ["Title", "License"]
    issues = validate_readme(content, section_plan, metadata)

    result = await refine_readme(
        content,
        issues,
        metadata,
        section_plan,
        call_model=_fake_call_model,
    )

    assert validate_readme(result, section_plan, metadata) == []
