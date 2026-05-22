import re
from typing import Tuple

CHUNK_MAX_CHARS = 12_000  # about 3,000 tokens


def preprocess(text: str) -> Tuple[list, dict]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _strip_repeated_headers_footers(normalized)
    cleaned = _clean(normalized)
    structure = _detect_structure(cleaned)
    chunks = _chunk(cleaned)
    return chunks, structure


def _clean(text: str) -> str:
    text = text.replace("\f", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_repeated_headers_footers(text: str) -> str:
    pages = text.split("\f")
    if len(pages) <= 1:
        lines = [line for line in text.splitlines() if not _is_page_number_line(line)]
        return "\n".join(lines)

    header_counts: dict[str, int] = {}
    footer_counts: dict[str, int] = {}
    page_lines: list[list[str]] = []

    for page in pages:
        lines = [line for line in page.splitlines() if line.strip()]
        header_lines = lines[:2]
        footer_lines = lines[-2:] if len(lines) >= 2 else lines

        for line in header_lines:
            header_counts[line] = header_counts.get(line, 0) + 1
        for line in footer_lines:
            footer_counts[line] = footer_counts.get(line, 0) + 1

        page_lines.append(page.splitlines())

    header_repeats = {
        line for line, count in header_counts.items() if count >= 2 and len(line) <= 80
    }
    footer_repeats = {
        line for line, count in footer_counts.items() if count >= 2 and len(line) <= 80
    }

    cleaned_pages = []
    for lines in page_lines:
        cleaned_page_lines = []
        for line in lines:
            if _is_page_number_line(line):
                continue
            if line in header_repeats or line in footer_repeats:
                continue
            cleaned_page_lines.append(line)
        cleaned_pages.append("\n".join(cleaned_page_lines))

    return "\n\n".join(cleaned_pages)


def _is_page_number_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(
        re.match(r"^(page\s*)?\d+(\s*(/|of)\s*\d+)?$", stripped, re.IGNORECASE)
    )


def _detect_structure(text: str) -> dict:
    lines = text.splitlines()
    headings = []
    numbered_sections = []
    bullets = []
    tables = []

    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if _is_heading(line):
            headings.append({"line": line, "index": index})
        if re.match(r"^\d+(\.\d+)*\s+.+", line):
            numbered_sections.append({"line": line, "index": index})
        if re.match(r"^(\*|-|\d+\)|\d+\.)\s+.+", line):
            bullets.append({"line": line, "index": index})
        if _looks_like_table_row(line):
            tables.append({"line": line, "index": index})

    return {
        "headings": headings,
        "numbered_sections": numbered_sections,
        "bullets": bullets,
        "tables": tables,
        "counts": {
            "headings": len(headings),
            "numbered_sections": len(numbered_sections),
            "bullets": len(bullets),
            "tables": len(tables),
        },
    }


def _is_heading(line: str) -> bool:
    if line.endswith(":"):
        return True
    letters = re.sub(r"[^A-Za-z]", "", line)
    if letters and line == line.upper() and len(line) <= 120:
        return True
    return False


def _looks_like_table_row(line: str) -> bool:
    if "|" in line:
        return True
    return bool(re.search(r"\S+\s{2,}\S+", line))


def _chunk(text: str) -> list:
    if len(text) <= CHUNK_MAX_CHARS:
        return [text]

    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for para in paragraphs:
        if not para.strip():
            continue

        if len(para) > CHUNK_MAX_CHARS:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                if not sentence:
                    continue
                if len(sentence) > CHUNK_MAX_CHARS:
                    for i in range(0, len(sentence), CHUNK_MAX_CHARS):
                        piece = sentence[i : i + CHUNK_MAX_CHARS]
                        if current and len(current) + len(piece) + 2 > CHUNK_MAX_CHARS:
                            flush()
                        if current:
                            current += "\n\n" + piece
                        else:
                            current = piece
                else:
                    if current and len(current) + len(sentence) + 1 > CHUNK_MAX_CHARS:
                        flush()
                    current = sentence if not current else current + " " + sentence
            continue

        if current and len(current) + len(para) + 2 > CHUNK_MAX_CHARS:
            flush()
        current = para if not current else current + "\n\n" + para

    flush()
    return chunks
