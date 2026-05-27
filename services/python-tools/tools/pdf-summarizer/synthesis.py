import os
import re

from openai import AsyncOpenAI

OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
SYNTHESIS_MODEL = "deepseek-r1-0528"
FALLBACK_MODEL = "kimi-k2.6"

client = AsyncOpenAI(api_key=OXLO_API_KEY, base_url=OXLO_BASE_URL)

REQUIRED_HEADERS = (
    "## Executive Summary",
    "## Key Findings",
    "## Data & Numbers",
    "## Action Items",
    "## Notable Quotes",
    "## Risk Factors",
)

SYSTEM_PROMPT = """\
You are an executive assistant and expert document analyst. Summarize the provided document into a structured report.
Given section summaries and extracted data points, output the following sections IN THIS EXACT ORDER using markdown headers:

## Executive Summary
(2-3 sentence overview)

## Key Findings
(bulleted list of the most important points)

## Data & Numbers
(extract all specific numbers, dates, amounts, percentages; use a markdown table when helpful)

## Action Items
(any tasks, deadlines, or next steps mentioned; if none are present, write "None identified.")

## Notable Quotes
(direct quotes worth highlighting; if none are present, write "None identified.")

## Risk Factors
(any concerns or warnings mentioned; if none are present, write "None identified.")

Rules:
- Never hallucinate figures. Use only data from the provided summaries and entities.
- Preserve exact numbers, dates, and amounts.
- Be concise but comprehensive. Use markdown formatting.
- Start your response DIRECTLY with "## Executive Summary" - no preamble, no intro sentence.
- Do NOT include any reasoning, chain-of-thought, or <think> blocks. Output only the final report.
- Think briefly. Your <think> block must not exceed 300 words. Go directly to the report.
"""


def _build_entity_block(entities: list) -> str:
    header = "| Type | Value | Context |"
    divider = "| --- | --- | --- |"
    if not entities:
        return "\n".join([header, divider, "| None | None | None |"])

    lines = [header, divider]
    for entity in entities:
        value = str(entity.get("value", "")).replace("|", "\\|")
        context = str(entity.get("context", "")).replace("|", "\\|")
        entity_type = str(entity.get("type", "")).replace("|", "\\|")
        lines.append(f"| {entity_type} | {value} | {context} |")
    return "\n".join(lines)


def _format_structure(structure: dict) -> str:
    if not structure:
        return "None"

    headings = [item.get("line", "") for item in structure.get("headings", [])][:12]
    numbered = [
        item.get("line", "") for item in structure.get("numbered_sections", [])
    ][:12]
    counts = structure.get("counts", {})

    parts = []
    if headings:
        parts.append("Headings: " + "; ".join(headings))
    if numbered:
        parts.append("Numbered sections: " + "; ".join(numbered))

    parts.append(f"Bullet lines: {counts.get('bullets', 0)}")
    parts.append(f"Table-like lines: {counts.get('tables', 0)}")

    return "\n".join(parts) if parts else "None"


def _pick_model(summaries_text: str, entity_block: str) -> str:
    combined_length = len(summaries_text) + len(entity_block)
    if combined_length > 60_000:
        return FALLBACK_MODEL
    return SYNTHESIS_MODEL


def _strip_think(raw: str) -> str:
    """
    Remove model reasoning blocks from the final response.
    Handles both well-formed and malformed <think> content.
    """
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()

    if "<think>" in cleaned.lower():
        match = re.search(r"(^|\n)(##\s)", cleaned)
        if match:
            cleaned = cleaned[match.start():].strip()
        else:
            cleaned = re.sub(r"<think>[\s\S]*", "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned


def _section_score(text: str) -> int:
    return sum(1 for header in REQUIRED_HEADERS if header in text)


async def _create_completion(model: str, user_content: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=8192,
    )

    raw = response.choices[0].message.content or ""
    return _strip_think(raw)


async def synthesize(chunk_summaries: list, entities: list, structure: dict) -> str:
    summaries_text = "\n\n".join(
        f"### Section {index + 1}\n{summary}"
        for index, summary in enumerate(chunk_summaries)
    )
    entity_block = _build_entity_block(entities)
    structure_hint = _format_structure(structure)

    user_content = (
        "SECTION SUMMARIES:\n"
        f"{summaries_text}\n\n"
        "STRUCTURE HINTS:\n"
        f"{structure_hint}\n\n"
        "EXTRACTED ENTITIES (Type | Value | Context):\n"
        f"{entity_block}\n"
    )

    model = _pick_model(summaries_text, entity_block)
    report = await _create_completion(model, user_content)
    if _section_score(report) < len(REQUIRED_HEADERS):
        fallback_report = await _create_completion(FALLBACK_MODEL, user_content)
        if _section_score(fallback_report) > _section_score(report) or (
            _section_score(fallback_report) == _section_score(report)
            and len(fallback_report) > len(report)
        ):
            report = fallback_report

    return report
