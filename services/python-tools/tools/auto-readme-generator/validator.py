import re
from typing import Optional

SHIELD_URL_PATTERN = re.compile(r"https?://[^\s\)\]]+")
VALID_SHIELD_PREFIX = "https://img.shields.io/"
FENCE_OPEN = re.compile(r"^`{3}(\w*)$")

INSTALL_COMMANDS = {
    "npm": ["npm install", "npm ci"],
    "yarn": ["yarn install", "yarn add"],
    "pnpm": ["pnpm install", "pnpm add"],
    "pip": ["pip install"],
    "pipenv": ["pipenv install"],
    "poetry": ["poetry install"],
}


def _has_section(content: str, section: str) -> bool:
    pattern = re.compile(
        rf"^#{{1,6}}\s+{re.escape(section)}\s*#*\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    return bool(pattern.search(content))


def _find_fence_issues(content: str) -> list:
    issues = []
    in_block = False

    for line in content.splitlines():
        match = FENCE_OPEN.match(line.strip())
        if match is None:
            continue

        fence_lang = match.group(1)
        if not in_block:
            if not fence_lang:
                issues.append({"type": "no_lang_fence", "detail": "code block missing language"})
            in_block = True
        else:
            in_block = False

    if in_block:
        issues.append({"type": "unclosed_fence", "detail": "code block not closed"})

    return issues


def _extract_code_blocks(content: str) -> list:
    blocks = []
    in_block = False
    current = []

    for line in content.splitlines():
        match = FENCE_OPEN.match(line.strip())
        if match is not None:
            if in_block:
                blocks.append("\n".join(current))
                current = []
                in_block = False
            else:
                in_block = True
            continue

        if in_block:
            current.append(line)

    return blocks


def _has_install_command(content: str, package_manager: str) -> bool:
    options = INSTALL_COMMANDS.get(package_manager.lower(), [])
    if not options:
        return False

    code_blocks = _extract_code_blocks(content)
    for block in code_blocks:
        if any(cmd in block for cmd in options):
            return True

    for cmd in options:
        pattern = re.compile(rf"(?m)^[\t >`]*{re.escape(cmd)}\b")
        if pattern.search(content):
            return True

    return False


def validate_readme(content: str, section_plan: list, metadata: Optional[dict] = None) -> list:
    issues = []

    for section in section_plan:
        if not _has_section(content, section):
            issues.append({"type": "missing_section", "detail": section})

    for url in SHIELD_URL_PATTERN.findall(content):
        if "shields.io" in url and not url.startswith(VALID_SHIELD_PREFIX):
            issues.append({"type": "bad_badge", "detail": url})

    issues.extend(_find_fence_issues(content))

    if metadata:
        package_manager = metadata.get("package_manager", "").lower()
        if package_manager and package_manager in INSTALL_COMMANDS:
            if not _has_install_command(content, package_manager):
                issues.append({
                    "type": "install_command_mismatch",
                    "detail": f"missing install command for {package_manager}",
                })

    return issues
