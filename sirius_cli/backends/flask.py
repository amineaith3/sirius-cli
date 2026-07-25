import os
import csv
import re
import sqlite3
import subprocess
import sys
import typer
from pathlib import Path
from typing import Dict, Any, List, Optional
from sirius_cli.backends.base import BackendStrategy

# Regex pattern for valid SQL identifiers (alphanumeric + underscore, must start with letter or _)
_VALID_SQL_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _quote_ident(name: str) -> str:
    """Double-quote a SQL identifier after validating it contains only safe characters.
    This prevents SQL injection through table or column names."""
    if not _VALID_SQL_IDENT.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


def _find_flask() -> Optional[str]:
    """Locate the flask executable, preferring the one in the current Python environment."""
    import shutil

    flask_path = shutil.which("flask")
    if flask_path:
        return flask_path
    return None


def _run_flask_db(args: list, cwd: str, env: Optional[dict] = None) -> None:
    """Run a flask db command safely without shell=True."""
    flask_path = _find_flask()
    if flask_path:
        cmd = [flask_path, "db"] + args
    else:
        cmd = [sys.executable, "-m", "flask", "db"] + args
    subprocess.run(cmd, cwd=cwd, check=True, env=env, stdout=subprocess.DEVNULL)


class FlaskBackendStrategy(BackendStrategy):
    """
    Flask backend generation strategy.
    Uses Flask-SQLAlchemy for ORM and Flask-Migrate (Alembic) for migrations.
    """

    @property
    def name(self) -> str:
        return "flask"

    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        from sirius_cli.generator import get_env, render_template

        env = get_env()
        backend_path = os.path.join(project_path, "backend")

        backend_templates = {
            "backends/flask/database.py.jinja2": "database.py",
            "backends/flask/models.py.jinja2": "models.py",
            "backends/flask/schemas.py.jinja2": "schemas.py",
            "backends/flask/main.py.jinja2": "main.py",
            "backends/flask/requirements.txt.jinja2": "requirements.txt",
            "backends/flask/Dockerfile.jinja2": "Dockerfile",
        }

        if context.get("auth"):
            backend_templates["backends/flask/auth.py.jinja2"] = "auth.py"

        for t_path, dest_name in backend_templates.items():
            render_template(
                env, t_path, os.path.join(backend_path, dest_name), **context
            )

        # Write init file to make backend a python package
        with open(os.path.join(backend_path, "__init__.py"), "w") as f:
            f.write("# backend package\n")

    def post_init_setup(self, project_path: str, context: Dict[str, Any]) -> None:
        typer.echo("Initializing Flask-Migrate migration system...")
        try:
            env = os.environ.copy()
            env["FLASK_APP"] = "backend.main"
            env["PYTHONPATH"] = project_path + os.pathsep + env.get("PYTHONPATH", "")

            # flask db init — creates the migrations/ directory
            _run_flask_db(["init"], cwd=project_path, env=env)

            # flask db migrate — autogenerate the initial migration
            typer.echo("Autogenerating migration scripts...")
            _run_flask_db(
                ["migrate", "-m", "Initial migration"],
                cwd=project_path,
                env=env,
            )

            # flask db upgrade — apply the migration
            typer.echo("Running database migrations...")
            _run_flask_db(["upgrade"], cwd=project_path, env=env)

            typer.secho(
                "[OK] Flask-Migrate migration system initialized successfully!",
                fg=typer.colors.GREEN,
            )
        except Exception as e:
            typer.secho(
                f"[WARNING] Flask-Migrate initialization failed: {e}",
                fg=typer.colors.YELLOW,
            )
            typer.echo(
                "You can configure database credentials and run migrations manually later."
            )

    def post_update_setup(
        self, project_path: str, context: Dict[str, Any], message: str
    ) -> None:
        typer.echo("Generating Flask-Migrate migration...")
        env = os.environ.copy()
        env["FLASK_APP"] = "backend.main"
        env["PYTHONPATH"] = project_path + os.pathsep + env.get("PYTHONPATH", "")
        try:
            _run_flask_db(["migrate", "-m", message], cwd=project_path, env=env)
            typer.echo("Running database migrations...")
            _run_flask_db(["upgrade"], cwd=project_path, env=env)
            typer.secho(
                "[OK] Database schema updated successfully!", fg=typer.colors.GREEN
            )
        except Exception as e:
            typer.secho(
                f"[WARNING] Flask-Migrate migration failed: {e}",
                fg=typer.colors.YELLOW,
            )
            typer.echo(
                "You can configure database credentials and run migrations manually later."
            )

    def seed_data(self, project_path: str, seed_files: List[str]) -> None:
        # NOTE: SQLite-only for now. PG/MySQL support is tracked in Issue #20.
        db_path = os.path.join(project_path, "backend", "app.db")
        if not os.path.exists(db_path):
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for path in seed_files:
            if not os.path.exists(path):
                continue

            ext = Path(path).suffix.lower()
            if ext in (".xlsx", ".xls"):
                try:
                    import pandas as pd

                    df = pd.read_excel(path)
                    all_rows = df.to_dict(orient="records")
                    fieldnames = list(df.columns)
                except Exception:
                    continue
            elif ext == ".json":
                try:
                    import json as _json
                    from sirius_cli.parser import (
                        _extract_raw_json_tables,
                        sanitize_table_name,
                        sanitize_column_name,
                    )

                    with open(path, "r", encoding="utf-8") as f:
                        jdata = _json.load(f)
                    default_table = sanitize_table_name(path)
                    jtables = _extract_raw_json_tables(jdata, default_table)
                    for t_name, t_rows in jtables.items():
                        if not t_rows:
                            continue
                        cols = list(t_rows[0].keys())
                        san_table = sanitize_table_name(t_name)
                        san_cols = [sanitize_column_name(c) for c in cols]

                        rows = []
                        for row in t_rows:
                            mapped_row: Dict[str, Any] = {}
                            for k, v in row.items():
                                sanitized_k = sanitize_column_name(str(k))
                                if v == "" or v is None:
                                    mapped_row[sanitized_k] = None
                                elif str(v).lower() == "true":
                                    mapped_row[sanitized_k] = 1
                                elif str(v).lower() == "false":
                                    mapped_row[sanitized_k] = 0
                                else:
                                    mapped_row[sanitized_k] = v
                            rows.append(mapped_row)

                        quoted_table = _quote_ident(san_table)
                        cursor.execute(f"PRAGMA table_info({quoted_table});")
                        existing_cols = {info[1] for info in cursor.fetchall()}

                        valid_cols = [c for c in san_cols if c in existing_cols]
                        if not valid_cols:
                            continue

                        placeholders = ", ".join(["?"] * len(valid_cols))
                        quoted_cols = ", ".join([_quote_ident(c) for c in valid_cols])
                        query = (
                            f"INSERT OR IGNORE INTO {quoted_table} "
                            f"({quoted_cols}) VALUES ({placeholders});"
                        )

                        data_to_insert = []
                        for row in rows:
                            row_tuple = tuple(row.get(c) for c in valid_cols)
                            data_to_insert.append(row_tuple)

                        cursor.executemany(query, data_to_insert)
                    continue
                except Exception:
                    continue
            else:
                from sirius_cli.parser import (  # noqa: PLC0415
                    sanitize_column_name,
                    sanitize_table_name,
                )

                encodings_to_try = ["utf-8", "utf-16", "cp1252"]
                fieldnames = []
                all_rows = []
                for enc in encodings_to_try:
                    try:
                        with open(path, "r", encoding=enc) as f:
                            reader = csv.DictReader(f)
                            if reader.fieldnames:
                                fieldnames = list(reader.fieldnames)
                                all_rows = list(reader)
                        break
                    except UnicodeDecodeError:
                        continue

                if not fieldnames:
                    continue

                table_name = sanitize_table_name(path)
                cols = [sanitize_column_name(c) for c in fieldnames]

                rows = []
                for row in all_rows:
                    mapped_csv_row: Dict[str, Any] = {}
                    for k, v in row.items():
                        sanitized_k = sanitize_column_name(str(k))
                        if v == "" or v is None:
                            mapped_csv_row[sanitized_k] = None
                        elif str(v).lower() == "true":
                            mapped_csv_row[sanitized_k] = 1
                        elif str(v).lower() == "false":
                            mapped_csv_row[sanitized_k] = 0
                        else:
                            mapped_csv_row[sanitized_k] = v
                    rows.append(mapped_csv_row)

                if not rows:
                    continue

                quoted_table = _quote_ident(table_name)
                cursor.execute(f"PRAGMA table_info({quoted_table});")
                existing_cols = {info[1] for info in cursor.fetchall()}

                valid_cols = [c for c in cols if c in existing_cols]
                if not valid_cols:
                    continue

                placeholders = ", ".join(["?"] * len(valid_cols))
                quoted_cols = ", ".join([_quote_ident(c) for c in valid_cols])
                query = (
                    f"INSERT OR IGNORE INTO {quoted_table} "
                    f"({quoted_cols}) VALUES ({placeholders});"
                )

                data_to_insert = []
                for row in rows:
                    row_tuple = tuple(row.get(c) for c in valid_cols)
                    data_to_insert.append(row_tuple)

                cursor.executemany(query, data_to_insert)

        conn.commit()
        conn.close()
