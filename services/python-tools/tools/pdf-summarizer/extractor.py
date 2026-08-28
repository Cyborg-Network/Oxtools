import re
from typing import List

PATTERNS = {
    "monetary": r"[\$€£¥]\s?\d[\d,]*(?:\.\d+)?(?:\s?[KMBkmb](?:illion)?)?",
    "date": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4})\b",
    "percentage": r"\b\d+(?:\.\d+)?%\b",
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "url": r"\bhttps?://[^\s)]+",
    "large_number": r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b",
}

CONTEXT_WINDOW = 80


def extract_entities(text: str) -> List[dict]:
    results: List[dict] = []
    seen = set()

    for entity_type, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(0).strip()
            key = (entity_type, value, match.start())
            if key in seen:
                continue
            seen.add(key)
            context = _get_context(text, match.start(), match.end())
            results.append(
                {"type": entity_type, "value": value, "context": context}
            )

    try:
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            nlp = None

        if nlp:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ not in {
                    "PERSON",
                    "ORG",
                    "GPE",
                    "PRODUCT",
                    "EVENT",
                    "WORK_OF_ART",
                }:
                    continue
                value = ent.text.strip()
                key = ("proper_noun", value, ent.start_char)
                if key in seen:
                    continue
                seen.add(key)
                context = _get_context(text, ent.start_char, ent.end_char)
                results.append(
                    {"type": "proper_noun", "value": value, "context": context}
                )
    except Exception:
        pass

    return results


def _get_context(text: str, start: int, end: int) -> str:
    left = max(0, start - CONTEXT_WINDOW)
    right = min(len(text), end + CONTEXT_WINDOW)
    context = text[left:right]
    context = re.sub(r"\s+", " ", context)
    return context.strip()
