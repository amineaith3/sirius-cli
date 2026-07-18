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


def test_cli_init_mutual_exclusion():
    result = runner.invoke(
        app, ["init", "test_app", "--csv", "dummy.csv", "--json", "dummy.json"]
    )
    assert result.exit_code == 1
    assert "Error: You must provide exactly one input option" in result.output


def test_cli_init_json(tmp_project_dir, tmp_path):
    import json

    json_path = tmp_path / "items.json"
    json_data = [
        {"id": 1, "name": "item1", "price": 9.99},
        {"id": 2, "name": "item2", "price": 19.99},
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    project_path = os.path.join(tmp_project_dir, "test_app_json_cli")

    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--json",
            str(json_path),
            "--no-seed",
        ],
    )
    assert result.exit_code == 0
    assert "Scaffolding project in" in result.output
    assert os.path.isdir(project_path)


def test_cli_update_json(tmp_project_dir, tmp_path):
    import json

    # Init first
    json_path = tmp_path / "items.json"
    json_data = [
        {"id": 1, "name": "item1", "price": 9.99},
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    project_path = os.path.join(tmp_project_dir, "test_app_update_json_cli")

    result = runner.invoke(
        app,
        [
            "init",
            project_path,
            "--json",
            str(json_path),
            "--no-seed",
        ],
    )
    assert result.exit_code == 0

    # Create new json for update
    update_json_path = tmp_path / "items_updated.json"
    update_json_data = [
        {"id": 1, "name": "item1", "price": 9.99, "description": "some text"},
    ]
    with open(update_json_path, "w", encoding="utf-8") as f:
        json.dump(update_json_data, f)

    result_update = runner.invoke(
        app,
        [
            "update",
            project_path,
            "--json",
            str(update_json_path),
        ],
    )
    assert result_update.exit_code == 0
    assert "Updating project in" in result_update.output


def test_seed_database_from_csvs(tmp_path):
    from sirius_cli.cli import seed_database_from_csvs
    import sqlite3
    import pandas as pd
    import json

    # 1. Create a dummy sqlite db that mimics a project db
    project_dir = tmp_path / "my_project"
    backend_dir = project_dir / "backend"
    backend_dir.mkdir(parents=True)
    db_path = backend_dir / "app.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    # Create tables
    cursor.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT);"
    )
    cursor.execute("CREATE TABLE roles (id INTEGER PRIMARY KEY, role_name TEXT);")
    conn.commit()
    conn.close()

    # 2. Create CSV, Excel, and JSON files to seed
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("id,name,email\n1,Alice,alice@example.com\n", encoding="utf-8")

    # Create Excel file using pandas
    excel_file = tmp_path / "roles.xlsx"
    df = pd.DataFrame(
        [{"id": 10, "role_name": "admin"}, {"id": 11, "role_name": "user"}]
    )
    df.to_excel(str(excel_file), index=False)

    # Create JSON file
    json_file = tmp_path / "users.json"
    json_data = [
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    # 3. Call seed_database_from_csvs
    seed_paths = [str(csv_file), str(excel_file), str(json_file)]
    seed_database_from_csvs(str(project_dir), seed_paths)

    # 4. Verify sqlite database contents
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users ORDER BY id;")
    users = cursor.fetchall()
    assert len(users) == 3
    assert users[0] == (1, "Alice", "alice@example.com")
    assert users[1] == (2, "Bob", "bob@example.com")
    assert users[2] == (3, "Charlie", "charlie@example.com")

    cursor.execute("SELECT * FROM roles ORDER BY id;")
    roles = cursor.fetchall()
    assert len(roles) == 2
    assert roles[0] == (10, "admin")
    assert roles[1] == (11, "user")

    conn.close()
