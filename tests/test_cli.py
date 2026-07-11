import os
from typer.testing import CliRunner
from sirius_cli.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Sirius-CLI version" in result.output


def test_cli_init_missing_args():
    # Calling init without --csv, --excel, --db, or --config should fail
    result = runner.invoke(app, ["init", "test_app"])
    assert result.exit_code == 1
    assert "Error: You must provide exactly one input option" in result.output


def test_cli_init_csv(tmp_project_dir, sample_csv_file):
    # Mock alembic and seed out of the equation for CLI runner test to avoid needing db drivers
    # Typer runner captures output, but since we are writing files to a tmp path, we should cd there

    # We use a mocked project path inside our temporary directory
    project_path = os.path.join(tmp_project_dir, "test_app_cli")

    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--csv",
            sample_csv_file,
            "--no-seed",  # skip DB seeding
        ],
    )

    # Note: Alembic will likely fail in the CLI runner if the python env isn't fully set up,
    # but the cli should catch the exception and print a warning rather than crash with exit 1.
    # The generation process should still succeed up to alembic.

    assert result.exit_code == 0
    assert "Scaffolding project in" in result.output
    assert "Project" in result.output
    assert "has been created" in result.output

    # Verify the structure was built
    assert os.path.isdir(project_path)
    assert os.path.isdir(os.path.join(project_path, "backend"))
    assert os.path.isdir(os.path.join(project_path, "frontend"))
