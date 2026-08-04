"""
Tests for pluggable FrontendStrategy via the CLI --frontend flag.
"""

import os
import pytest
from typer.testing import CliRunner
from sirius_cli.cli import app
from sirius_cli.frontends import get_frontend_strategy
from sirius_cli.frontends.react import ReactFrontendStrategy

runner = CliRunner()


# --- Shared config fixture -----------------------------------------------


@pytest.fixture
def base_config_json(tmp_path):
    """Minimal JSON config used across all frontend tests."""
    import json

    config_path = tmp_path / "frontend_schema.json"
    config_data = {
        "project_name": "frontend_test_proj",
        "theme": "indigo",
        "entities": {
            "tasks": {
                "columns": [
                    {"name": "id", "type": "Integer", "is_pk": True},
                    {"name": "title", "type": "String"},
                    {"name": "done", "type": "Boolean"},
                ]
            }
        },
    }
    config_path.write_text(json.dumps(config_data))
    return str(config_path)


# --- Tests ---------------------------------------------------------------


def test_react_frontend_files_generated(tmp_project_dir, base_config_json):
    """--frontend=react must scaffold all required frontend source files, including components."""
    project_path = os.path.join(tmp_project_dir, "react_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            base_config_json,
            "--frontend",
            "react",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    frontend_dir = os.path.join(project_path, "frontend")
    expected_files = [
        "index.html",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "tailwind.config.js",
        "postcss.config.js",
        "Dockerfile",
        ".env",
        "src/main.tsx",
        "src/index.css",
        "src/App.tsx",
        "src/Dashboard.tsx",
        "src/components/SiriusTable.tsx",
        "src/components/SiriusPagination.tsx",
        "src/components/SiriusBadge.tsx",
        "src/components/SiriusDropdown.tsx",
        "src/components/SiriusError.tsx",
        "src/components/SiriusToast.tsx",
        "src/pages/TasksCrud.tsx",
    ]

    for expected_file in expected_files:
        path = os.path.join(frontend_dir, expected_file)
        assert os.path.exists(path), f"Expected {expected_file} to exist in frontend/"


def test_default_frontend_is_react(tmp_project_dir, base_config_json):
    """If --frontend is omitted, the system must default to generating the React frontend."""
    project_path = os.path.join(tmp_project_dir, "default_frontend_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            base_config_json,
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    # App.tsx is React-specific and should exist
    app_tsx = os.path.join(project_path, "frontend", "src", "App.tsx")
    assert os.path.exists(app_tsx), "Expected React App.tsx to exist by default"


def test_invalid_frontend_strategy_rejected(tmp_project_dir, base_config_json):
    """Passing an unsupported frontend framework must trigger a clean CLI error."""
    project_path = os.path.join(tmp_project_dir, "invalid_frontend_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            base_config_json,
            "--frontend",
            "svelte",
            "--no-seed",
        ],
    )
    assert result.exit_code != 0
    assert "Error: Unsupported frontend 'svelte'" in result.output


def test_vue_frontend_files_generated(tmp_project_dir, base_config_json):
    """--frontend=vue must scaffold all required frontend source files, including components."""
    project_path = os.path.join(tmp_project_dir, "vue_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            base_config_json,
            "--frontend",
            "vue",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    frontend_dir = os.path.join(project_path, "frontend")
    expected_files = [
        "index.html",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "tailwind.config.js",
        "postcss.config.js",
        "Dockerfile",
        ".env",
        "src/main.ts",
        "src/index.css",
        "src/App.vue",
        "src/Dashboard.vue",
        "src/stores/auth.ts",
        "src/components/SiriusTable.vue",
        "src/components/SiriusPagination.vue",
        "src/components/SiriusBadge.vue",
        "src/components/SiriusDropdown.vue",
        "src/components/SiriusError.vue",
        "src/components/SiriusToast.vue",
        "src/pages/TasksCrud.vue",
    ]

    for expected_file in expected_files:
        path = os.path.join(frontend_dir, expected_file)
        assert os.path.exists(path), f"Expected {expected_file} to exist in frontend/"


def test_frontend_strategy_registry():
    """Verify registry get_frontend_strategy factory matches name strings to classes."""
    from sirius_cli.frontends.vue import VueFrontendStrategy

    strategy = get_frontend_strategy("react")
    assert isinstance(strategy, ReactFrontendStrategy)
    assert strategy.name == "react"

    strategy_vue = get_frontend_strategy("vue")
    assert isinstance(strategy_vue, VueFrontendStrategy)
    assert strategy_vue.name == "vue"

    with pytest.raises(ValueError) as exc:
        get_frontend_strategy("angular")
    assert "Unsupported frontend engine: 'angular'" in str(exc.value)
