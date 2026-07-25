"""
Tests for FlaskBackendStrategy via the CLI --backend=flask flag.
All tests use the Typer test runner with --no-seed to avoid hitting
a real database and to keep tests fast and hermetic.
"""

import os
import pytest
from typer.testing import CliRunner
from sirius_cli.cli import app

runner = CliRunner()


# ─── Shared config fixture ────────────────────────────────────────────────────


@pytest.fixture
def flask_config_json(tmp_path):
    """Minimal JSON config used across all Flask tests."""
    import json

    config_path = tmp_path / "flask_schema.json"
    config_data = {
        "project_name": "flask_test_proj",
        "theme": "blue",
        "entities": {
            "products": {
                "columns": [
                    {"name": "id", "type": "Integer", "is_pk": True},
                    {"name": "name", "type": "String"},
                    {"name": "price", "type": "Float"},
                    {"name": "in_stock", "type": "Boolean"},
                ]
            }
        },
    }
    config_path.write_text(json.dumps(config_data))
    return str(config_path)


# ─── Core file generation ─────────────────────────────────────────────────────


def test_flask_backend_files_generated(tmp_project_dir, flask_config_json):
    """--backend=flask must scaffold all required backend source files."""
    project_path = os.path.join(tmp_project_dir, "flask_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    backend_dir = os.path.join(project_path, "backend")
    for expected_file in [
        "main.py",
        "database.py",
        "models.py",
        "schemas.py",
        "requirements.txt",
        "Dockerfile",
        "__init__.py",
    ]:
        assert os.path.exists(
            os.path.join(backend_dir, expected_file)
        ), f"Expected {expected_file} to exist in backend/"


def test_flask_backend_is_not_fastapi(tmp_project_dir, flask_config_json):
    """Generated main.py must reference Flask, not FastAPI."""
    project_path = os.path.join(tmp_project_dir, "flask_not_fastapi")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    main_py = os.path.join(project_path, "backend", "main.py")
    with open(main_py, "r") as f:
        content = f.read()

    assert "Flask" in content, "main.py should import Flask"
    assert "FastAPI" not in content, "main.py should not reference FastAPI"


# ─── Auth ─────────────────────────────────────────────────────────────────────


def test_flask_backend_auth_files(tmp_project_dir, flask_config_json):
    """--backend=flask --auth must generate auth.py and include JWT deps in requirements."""
    project_path = os.path.join(tmp_project_dir, "flask_auth_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--auth",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    backend_dir = os.path.join(project_path, "backend")
    assert os.path.exists(
        os.path.join(backend_dir, "auth.py")
    ), "auth.py must be generated when --auth is passed"

    req_path = os.path.join(backend_dir, "requirements.txt")
    with open(req_path, "r") as f:
        req_content = f.read()

    assert "flask-jwt-extended" in req_content
    assert "passlib" in req_content
    assert "bcrypt" in req_content

    # The generated admin password should appear in CLI output
    assert "[AUTH] Auto-generated admin password:" in result.output


# ─── Database drivers ─────────────────────────────────────────────────────────


def test_flask_backend_pg(tmp_project_dir, flask_config_json):
    """--pg with Flask backend must write psycopg2-binary to requirements.txt."""
    project_path = os.path.join(tmp_project_dir, "flask_pg_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--pg",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        content = f.read()

    assert "psycopg2-binary" in content


def test_flask_backend_mysql(tmp_project_dir, flask_config_json):
    """--mysql with Flask backend must write pymysql to requirements.txt."""
    project_path = os.path.join(tmp_project_dir, "flask_mysql_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--mysql",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        content = f.read()

    assert "pymysql" in content


# ─── Misc flags ───────────────────────────────────────────────────────────────


def test_flask_backend_no_seed(tmp_project_dir, flask_config_json):
    """--no-seed must be respected and logged for Flask backend."""
    project_path = os.path.join(tmp_project_dir, "flask_no_seed_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "[SKIP] Database seeding skipped (--no-seed)." in result.output


def test_flask_dockerfile_uses_gunicorn(tmp_project_dir, flask_config_json):
    """Flask Dockerfile should use gunicorn, not uvicorn."""
    project_path = os.path.join(tmp_project_dir, "flask_docker_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            flask_config_json,
            "--backend",
            "flask",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    dockerfile = os.path.join(project_path, "backend", "Dockerfile")
    with open(dockerfile, "r") as f:
        content = f.read()

    assert "gunicorn" in content
    assert "uvicorn" not in content
