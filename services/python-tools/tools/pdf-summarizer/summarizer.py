import asyncio
import os
from typing import Optional

from openai import AsyncOpenAI

OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
SUMMARIZER_MODEL = os.getenv("PDF_SUMMARIZER_MODEL", "deepseek-v3.2")

client = AsyncOpenAI(api_key=OXLO_API_KEY, base_url=OXLO_BASE_URL)

SYSTEM_PROMPT = (
    "You are a precise document analyst. Summarize the provided section "
    "with clear, factual points. Include key numbers, dates, and action items "
    "mentioned in the text. Focus on facts; do not add interpretation."
)


async def _summarize_one(chunk: str, index: int, focus: Optional[str] = None) -> str:
    focus_line = f"\nFocus area: {focus}\n" if focus else ""
    user_prompt = f"Section {index + 1}:\n{focus_line}{chunk}"

    response = await client.chat.completions.create(
        model=SUMMARIZER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


async def summarize_chunks(chunks: list, focus: str = "") -> list:
    tasks = [_summarize_one(chunk, index, focus) for index, chunk in enumerate(chunks)]
    return await asyncio.gather(*tasks)
