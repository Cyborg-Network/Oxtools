SECTION_PLANS = {
    "web-api": [
        "Title",
        "Badges",
        "Description",
        "Features",
        "Quick Start",
        "Usage",
        "API Reference",
        "Config",
        "Contributing",
        "License",
    ],
    "cli": [
        "Title",
        "Badges",
        "Description",
        "Features",
        "Installation",
        "Usage",
        "Config",
        "Contributing",
        "License",
    ],
    "library": [
        "Title",
        "Badges",
        "Description",
        "Installation",
        "Usage",
        "API Reference",
        "Contributing",
        "License",
    ],
    "web-app": [
        "Title",
        "Badges",
        "Description",
        "Features",
        "Quick Start",
        "Usage",
        "Config",
        "Contributing",
        "License",
    ],
    "other": [
        "Title",
        "Description",
        "Installation",
        "Usage",
        "Contributing",
        "License",
    ],
}


def plan_sections(metadata: dict) -> list:
    project_type = (metadata or {}).get("project_type", "other")
    return SECTION_PLANS.get(project_type, SECTION_PLANS["other"])
