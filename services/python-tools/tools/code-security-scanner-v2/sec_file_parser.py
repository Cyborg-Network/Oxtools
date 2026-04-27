"""
Code Security Scanner V2 — Multi-File Parser
==============================================
Handles splitting multi-file input, extracting ZIP archives,
and organizing files for cross-file analysis.
"""

import base64
import io
import os
import re
import zipfile
import logging
from dataclasses import dataclass

from sec_config import MAX_FILES, MAX_SINGLE_FILE_BYTES, CONFIG_FILENAMES, CONFIG_EXTENSIONS

logger = logging.getLogger("security-scanner")


@dataclass
class ParsedFile:
    """A single file extracted from multi-file input."""
    path: str           # e.g. "src/auth.py" or "utils.py"
    filename: str       # e.g. "auth.py"
    content: str
    language: str       # Inferred from extension
    is_config: bool     # True for settings.py, .env, requirements.txt, etc.
    size_bytes: int


def infer_language(filename: str) -> str:
    """Infer programming language from filename extension."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".go": "go", ".java": "java", ".c": "c", ".cpp": "c",
        ".rb": "ruby", ".php": "php", ".rs": "rust",
        ".jsx": "javascript", ".tsx": "typescript", ".mjs": "javascript",
    }
    _, ext = os.path.splitext(filename.lower())
    return ext_map.get(ext, "unknown")


def is_config_file(filepath: str) -> bool:
    """Check if a file is a configuration/dependency file."""
    basename = os.path.basename(filepath).lower()
    if basename in CONFIG_FILENAMES:
        return True
    _, ext = os.path.splitext(basename)
    if ext in CONFIG_EXTENSIONS:
        return True
    return False


def parse_multi_file_input(code: str = "", files_data: str = "") -> list[ParsedFile]:
    """
    Parse input into individual files.
    
    Supports three input modes:
    1. Single code paste (backward compatible) → one file
    2. Multi-file paste with --- FILE: path --- markers → multiple files
    3. ZIP archive (base64 with __ZIP__: prefix) → extracted files
    """
    # Priority: files_data > code
    raw = files_data.strip() if files_data.strip() else code.strip()
    
    if not raw:
        return []
    
    # Mode 3: ZIP archive
    if raw.startswith("__ZIP__:"):
        return _extract_zip(raw[8:])
    
    # Mode 2: Multi-file with markers
    if "--- FILE:" in raw:
        return _parse_file_markers(raw)
    
    # Mode 1: Single code paste
    return [ParsedFile(
        path="input.py",
        filename="input.py",
        content=raw,
        language="python",
        is_config=False,
        size_bytes=len(raw.encode("utf-8")),
    )]


def _extract_zip(base64_data: str) -> list[ParsedFile]:
    """Extract files from a base64-encoded ZIP archive."""
    files = []
    try:
        zip_bytes = base64.b64decode(base64_data)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            for info in zf.infolist():
                # Skip directories, hidden files, __pycache__, node_modules
                if info.is_dir():
                    continue
                basename = os.path.basename(info.filename)
                if basename.startswith(".") or "__pycache__" in info.filename:
                    continue
                if "node_modules" in info.filename or ".git/" in info.filename:
                    continue
                if info.file_size > MAX_SINGLE_FILE_BYTES:
                    logger.warning(f"[ZIP] Skipping {info.filename}: too large ({info.file_size} bytes)")
                    continue
                if len(files) >= MAX_FILES:
                    logger.warning(f"[ZIP] Max file limit ({MAX_FILES}) reached, stopping extraction")
                    break
                
                try:
                    content = zf.read(info.filename).decode("utf-8", errors="replace")
                    files.append(ParsedFile(
                        path=info.filename,
                        filename=basename,
                        content=content,
                        language=infer_language(basename),
                        is_config=is_config_file(info.filename),
                        size_bytes=info.file_size,
                    ))
                except Exception as e:
                    logger.warning(f"[ZIP] Failed to read {info.filename}: {e}")
    except Exception as e:
        logger.error(f"[ZIP] Failed to extract archive: {e}")
    
    logger.info(f"[Parser] Extracted {len(files)} files from ZIP")
    return files


def _parse_file_markers(raw: str) -> list[ParsedFile]:
    """Parse multi-file input separated by --- FILE: path --- markers."""
    files = []
    pattern = re.compile(r"--- FILE:\s*(.+?)\s*---\n?", re.MULTILINE)
    
    parts = pattern.split(raw)
    # parts = [before_first_marker, path1, content1, path2, content2, ...]
    
    i = 1  # Skip any content before the first marker
    while i < len(parts) - 1:
        filepath = parts[i].strip()
        content = parts[i + 1].strip()
        basename = os.path.basename(filepath)
        
        if content and content != "[Binary file — skipped]":
            files.append(ParsedFile(
                path=filepath,
                filename=basename,
                content=content,
                language=infer_language(basename),
                is_config=is_config_file(filepath),
                size_bytes=len(content.encode("utf-8")),
            ))
        i += 2
    
    logger.info(f"[Parser] Parsed {len(files)} files from markers")
    return files
