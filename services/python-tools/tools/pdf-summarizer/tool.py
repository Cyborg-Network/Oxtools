"""
PDF Summarizer - Tool Entry Point
"""

import os

from extractor import extract_entities
from preprocessor import preprocess
from summarizer import summarize_chunks
from synthesis import synthesize


MANIFEST = {
    "id": "pdf-summarizer",
    "name": "PDF / Document Summarizer",
    "description": "Summarize long documents into a structured executive report",
    "author": "Franci-343",
    "version": "1.0.0",
    "requires": ["openai"],
}


async def run(data: dict):
    """
    Execute the PDF summarization pipeline with streaming updates.
    """
    if not os.getenv("OXLO_API_KEY"):
        return {"error": "OXLO_API_KEY not configured. Set it in .env"}

    document_text = (
        data.get("documentText")
        or data.get("document_text")
        or data.get("text")
        or data.get("document")
        or ""
    )
    if not str(document_text).strip():
        return {"error": "Document text is required."}

    focus = str(data.get("focus", "")).strip()

    async def stream():
        yield "[preprocess] Cleaning and chunking document...\n"
        chunks, structure = preprocess(str(document_text))
        if not chunks:
            yield "[error] No usable content after preprocessing.\n"
            return

        yield f"[preprocess] Prepared {len(chunks)} chunks\n"

        yield "[entities] Extracting entities...\n"
        clean_text = "\n\n".join(chunks)
        entities = extract_entities(clean_text)
        yield f"[entities] Extracted {len(entities)} entities\n"

        yield "[summarize] Summarizing sections...\n"
        chunk_summaries = await summarize_chunks(chunks, focus=focus)
        yield f"[summarize] Completed {len(chunk_summaries)} sections\n"

        yield "[synthesis] Building final report...\n"
        final_output = await synthesize(chunk_summaries, entities, structure)
        yield "\n---RESULT---\n"
        yield final_output

    return stream()
