import os
import re

from openai import AsyncOpenAI

OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
SYNTHESIS_MODEL = "deepseek-r1-0528"
FALLBACK_MODEL = "kimi-k2.6"

client = AsyncOpenAI(api_key=OXLO_API_KEY, base_url=OXLO_BASE_URL)

SYSTEM_PROMPT = """\
You are an expert document analyst producing an executive briefing.
Given section summaries and extracted data points, output the following sections
IN THIS EXACT ORDER using markdown headers:

## Executive Summary
(3-5 sentences, high-level overview)

## Key Findings
(bullet list of the most important factual findings)

## Action Items
(bullet list; if none are present in the document, write "None identified.")

## Risk Factors
(bullet list; if none are present, write "None identified.")

## Extracted Data
(markdown table with columns: Type | Value | Context)

Rules:
- Never hallucinate figures. Use only data from the provided summaries and entities.
- Preserve exact numbers, dates, and amounts.
- Be concise and professional.
- Start your response DIRECTLY with "## Executive Summary" — no preamble, no intro sentence.
- Do NOT include any reasoning, chain-of-thought, or <think> blocks. Output only the final report.
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
        "EXTRACTED ENTITIES:\n"
        f"{entity_block}\n"
    )

    model = _pick_model(summaries_text, entity_block)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content or ""
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
    return cleaned
