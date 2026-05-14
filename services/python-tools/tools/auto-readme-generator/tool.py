"""
Auto README Generator — Tool Entry Point
=========================================
Multi-agent pipeline: analyze, plan, write, validate, refine.
"""

from analyzer import analyze_project
from planner import plan_sections
from writer import write_readme
from validator import validate_readme
from refiner import refine_readme


MANIFEST = {
    "id": "auto-readme-generator",
    "name": "Auto README Generator",
    "description": "Multi-agent pipeline that generates structured, validated READMEs.",
    "author": "Franco Ayala",
    "version": "1.0.0",
}


async def run(data: dict):
    project_name = data.get("projectName") or "Unnamed Project"
    description = data.get("projectDescription") or ""
    tech_stack = data.get("techStack") or ""

    async def stream():
        if not description.strip():
            yield "[ERROR] Project description is required.\n"
            return

        yield "[1/5] Analyzing project metadata...\n"
        try:
            metadata = await analyze_project(project_name, description, tech_stack)
        except Exception as exc:
            yield f"[ERROR] Analyzer failed: {exc}\n"
            return

        yield "[2/5] Planning required sections...\n"
        section_plan = plan_sections(metadata)

        yield "[3/5] Writing README...\n"
        try:
            readme_content = await write_readme(metadata, section_plan)
        except Exception as exc:
            yield f"[ERROR] Writer failed: {exc}\n"
            return

        yield "[4/5] Validating sections and badges...\n"
        issues = validate_readme(readme_content, section_plan, metadata)

        if issues:
            yield f"[5/5] Found {len(issues)} issue(s), refining...\n"
            try:
                readme_content = await refine_readme(
                    readme_content,
                    issues,
                    metadata,
                    section_plan,
                )
                issues = validate_readme(readme_content, section_plan, metadata)
            except Exception as exc:
                yield f"[WARN] Refiner failed, returning best effort: {exc}\n"
        else:
            yield "[5/5] Validation passed.\n"

        if issues:
            yield f"[WARN] Validation still has {len(issues)} issue(s).\n"

        yield "\n---RESULT---\n"
        yield readme_content

    return stream()
