from planner import plan_sections


def test_web_api_has_api_reference():
    plan = plan_sections({"project_type": "web-api"})
    assert "API Reference" in plan


def test_cli_has_installation():
    plan = plan_sections({"project_type": "cli"})
    assert "Installation" in plan


def test_unknown_type_falls_back_to_other():
    plan = plan_sections({"project_type": "xyz"})
    assert "Usage" in plan
