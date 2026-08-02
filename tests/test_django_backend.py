"""
Tests for DjangoBackendStrategy via the CLI --backend=django flag.
All tests use the Typer test runner with --no-seed to avoid hitting
a real database and to keep tests fast and hermetic.
"""

import os
import pytest
from typer.testing import CliRunner
from sirius_cli.cli import app

runner = CliRunner()


# --- Shared config fixture -----------------------------------------------


@pytest.fixture
def django_config_json(tmp_path):
    """Minimal JSON config used across all Django tests."""
    import json

    config_path = tmp_path / "django_schema.json"
    config_data = {
        "project_name": "django_test_proj",
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


# --- Core file generation ------------------------------------------------


def test_django_backend_files_generated(tmp_project_dir, django_config_json):
    """--backend=django must scaffold all required backend source files."""
    project_path = os.path.join(tmp_project_dir, "django_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    backend_dir = os.path.join(project_path, "backend")
    for expected_file in [
        "settings.py",
        "urls.py",
        "models.py",
        "serializers.py",
        "views.py",
        "requirements.txt",
        "Dockerfile",
        "wsgi.py",
        "__init__.py",
    ]:
        assert os.path.exists(
            os.path.join(backend_dir, expected_file)
        ), f"Expected {expected_file} to exist in backend/"

    # manage.py lives at project root
    assert os.path.exists(
        os.path.join(project_path, "manage.py")
    ), "manage.py must exist at project root"


def test_django_backend_is_not_fastapi(tmp_project_dir, django_config_json):
    """Generated models.py must use Django ORM, not SQLAlchemy."""
    project_path = os.path.join(tmp_project_dir, "django_not_fastapi")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    models_py = os.path.join(project_path, "backend", "models.py")
    with open(models_py, "r") as f:
        content = f.read()

    assert "django.db" in content, "models.py should import from django.db"
    assert "SQLAlchemy" not in content, "models.py should not reference SQLAlchemy"
    assert "FastAPI" not in content, "models.py should not reference FastAPI"


# --- Auth ----------------------------------------------------------------


def test_django_backend_auth_files(tmp_project_dir, django_config_json):
    """--backend=django --auth must generate auth.py and include JWT deps in requirements."""
    project_path = os.path.join(tmp_project_dir, "django_auth_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
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

    assert "djangorestframework-simplejwt" in req_content

    # The generated admin password should appear in CLI output
    assert "[AUTH] Auto-generated admin password:" in result.output


# --- Database drivers ----------------------------------------------------


def test_django_backend_pg(tmp_project_dir, django_config_json):
    """--pg with Django backend must write psycopg2-binary to requirements.txt."""
    project_path = os.path.join(tmp_project_dir, "django_pg_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
            "--pg",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        content = f.read()

    assert "psycopg2-binary" in content


def test_django_backend_mysql(tmp_project_dir, django_config_json):
    """--mysql with Django backend must write pymysql to requirements.txt."""
    project_path = os.path.join(tmp_project_dir, "django_mysql_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
            "--mysql",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        content = f.read()

    assert "pymysql" in content


# --- Misc flags ----------------------------------------------------------


def test_django_backend_no_seed(tmp_project_dir, django_config_json):
    """--no-seed must be respected and logged for Django backend."""
    project_path = os.path.join(tmp_project_dir, "django_no_seed_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "[SKIP] Database seeding skipped (--no-seed)." in result.output


def test_django_dockerfile_uses_gunicorn(tmp_project_dir, django_config_json):
    """Django Dockerfile should use gunicorn, not uvicorn."""
    project_path = os.path.join(tmp_project_dir, "django_docker_app")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            django_config_json,
            "--backend",
            "django",
            "--no-seed",
        ],
    )
    assert result.exit_code == 0, result.output

    dockerfile = os.path.join(project_path, "backend", "Dockerfile")
    with open(dockerfile, "r") as f:
        content = f.read()

    assert "gunicorn" in content
    assert "uvicorn" not in content
