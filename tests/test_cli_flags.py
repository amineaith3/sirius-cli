import os
import json
import pytest
from typer.testing import CliRunner
from sirius_cli.cli import app

runner = CliRunner()


@pytest.fixture
def sample_config_json(tmp_path):
    config_path = tmp_path / "schema.json"
    config_data = {
        "project_name": "test_proj",
        "theme": "rose",
        "entities": {
            "users": {
                "columns": [
                    {"name": "id", "type": "Integer", "is_pk": True},
                    {"name": "name", "type": "String"},
                ]
            }
        },
    }
    config_path.write_text(json.dumps(config_data))
    return str(config_path)


def test_flag_csv_and_no_seed(tmp_project_dir, sample_csv_file):
    project_path = os.path.join(tmp_project_dir, "app_csv")
    result = runner.invoke(
        app, ["init", project_path, "--csv", sample_csv_file, "--no-seed"]
    )
    assert result.exit_code == 0
    assert "[SKIP] Database seeding skipped (--no-seed)." in result.output
    assert os.path.exists(os.path.join(project_path, "backend", "main.py"))


def test_flag_config(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_config")
    result = runner.invoke(app, ["init", project_path, "--config", sample_config_json])
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(project_path, "backend", "schemas.py"))


def test_flag_db(tmp_project_dir, sample_sqlite_db):
    project_path = os.path.join(tmp_project_dir, "app_db")
    result = runner.invoke(
        app, ["init", project_path, "--db", sample_sqlite_db, "--no-seed"]
    )
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(project_path, "backend", "models.py"))


def test_flag_pg(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_pg")
    result = runner.invoke(
        app, ["init", project_path, "--config", sample_config_json, "--pg"]
    )
    assert result.exit_code == 0

    # Verify postgres driver in requirements
    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        assert "psycopg2-binary" in f.read()


def test_flag_mysql(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_mysql")
    result = runner.invoke(
        app, ["init", project_path, "--config", sample_config_json, "--mysql"]
    )
    assert result.exit_code == 0

    # Verify mysql driver in requirements
    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        assert "pymysql" in f.read()


def test_flag_auth(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_auth")
    result = runner.invoke(
        app, ["init", project_path, "--config", sample_config_json, "--auth"]
    )
    assert result.exit_code == 0

    # Verify auth dependencies and generated admin password
    req_path = os.path.join(project_path, "backend", "requirements.txt")
    with open(req_path, "r") as f:
        req_content = f.read()
        assert "passlib" in req_content
        assert "bcrypt" in req_content
        assert "python-jose" in req_content

    assert "[AUTH] Auto-generated admin password:" in result.output


def test_flag_admin_creds(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_admin")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            sample_config_json,
            "--auth",
            "--admin-user",
            "superadmin",
            "--admin-pass",
            "secret123",
        ],
    )
    assert result.exit_code == 0
    # Output should not say auto-generated if we provided it
    assert "[AUTH] Auto-generated admin password:" not in result.output


def test_flag_port(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_port")
    result = runner.invoke(
        app, ["init", project_path, "--config", sample_config_json, "--port", "9999"]
    )
    assert result.exit_code == 0

    dc_path = os.path.join(project_path, "docker-compose.yml")
    with open(dc_path, "r") as f:
        assert "9999:9999" in f.read()


def test_flag_api_url(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_api")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            sample_config_json,
            "--api-url",
            "https://api.myprod.com",
        ],
    )
    assert result.exit_code == 0

    env_path = os.path.join(project_path, "frontend", ".env")
    with open(env_path, "r") as f:
        assert "VITE_API_URL=https://api.myprod.com" in f.read()


def test_flag_theme(tmp_project_dir, sample_config_json):
    project_path = os.path.join(tmp_project_dir, "app_theme")
    result = runner.invoke(
        app,
        ["init", project_path, "--config", sample_config_json, "--theme", "emerald"],
    )
    assert result.exit_code == 0

    tailwind_path = os.path.join(project_path, "frontend", "tailwind.config.js")
    with open(tailwind_path, "r") as f:
        assert "emerald" in f.read()


def test_flag_conflicting_inputs(tmp_project_dir, sample_config_json, sample_csv_file):
    project_path = os.path.join(tmp_project_dir, "app_conflict")
    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--config",
            sample_config_json,
            "--csv",
            sample_csv_file,
        ],
    )
    # Expect error because of multiple input sources
    assert result.exit_code == 1
    assert "Error: You must provide exactly one input option" in result.output
