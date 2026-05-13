from validator import validate_readme


def test_detects_missing_section():
    issues = validate_readme("# Title\n# Usage\n", ["Title", "Usage", "License"])
    assert any(item["type"] == "missing_section" for item in issues)


def test_detects_bad_badge():
    content = "![b](http://shields.io/badge/foo-bar)\n# Title\n# License\n"
    issues = validate_readme(content, ["Title", "License"])
    assert any(item["type"] == "bad_badge" for item in issues)


def test_detects_fence_without_language():
    content = "# Title\n# License\n```\nsome code\n```\n"
    issues = validate_readme(content, ["Title", "License"])
    assert any(item["type"] == "no_lang_fence" for item in issues)


def test_detects_missing_install_command_for_npm():
    content = "# Title\n# Installation\n# Usage\n"
    issues = validate_readme(content, ["Title", "Installation", "Usage"], {"package_manager": "npm"})
    assert any(item["type"] == "install_command_mismatch" for item in issues)


def test_passes_valid_readme():
    content = (
        "# Title\n"
        "![build](https://img.shields.io/badge/build-passing-green)\n"
        "# License\n"
        "```python\nprint('hi')\n```\n"
        "npm install\n"
    )
    assert validate_readme(content, ["Title", "License"], {"package_manager": "npm"}) == []
