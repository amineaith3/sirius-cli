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


def _quote_ident(name: str, db_type: str = "sqlite") -> str:
    """Quote a SQL identifier after validating it contains only safe characters.
    This prevents SQL injection through table or column names."""
    if not _VALID_SQL_IDENT.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    if db_type == "mysql":
        return f"`{name}`"
    return f'"{name}"'


def _find_alembic() -> Optional[str]:
    """Locate the alembic executable, preferring the one in the current Python environment."""
    import shutil

    alembic_path = shutil.which("alembic")
    if alembic_path:
        return alembic_path
    return None


def _run_alembic(args: list, cwd: str, env: Optional[dict] = None):
    """Run an alembic command safely without shell=True."""
    alembic_path = _find_alembic()
    if alembic_path:
        cmd = [alembic_path] + args
    else:
        cmd = [sys.executable, "-m", "alembic"] + args
    subprocess.run(cmd, cwd=cwd, check=True, env=env, stdout=subprocess.DEVNULL)


def _get_existing_columns(cursor, table_name: str, db_type: str) -> set:
    if db_type == "sqlite":
        quoted = _quote_ident(table_name, db_type)
        cursor.execute(f"PRAGMA table_info({quoted});")
        return {info[1] for info in cursor.fetchall()}
    elif db_type == "pg":
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            (table_name,),
        )
        return {row[0] for row in cursor.fetchall()}
    elif db_type == "mysql":
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = DATABASE();",
            (table_name,),
        )
        return {row[0] for row in cursor.fetchall()}
    return set()


def _build_insert_query(table_name: str, valid_cols: List[str], db_type: str) -> str:
    quoted_table = _quote_ident(table_name, db_type)
    quoted_cols = ", ".join([_quote_ident(c, db_type) for c in valid_cols])
    if db_type == "sqlite":
        placeholders = ", ".join(["?"] * len(valid_cols))
        return f"INSERT OR IGNORE INTO {quoted_table} ({quoted_cols}) VALUES ({placeholders});"
    elif db_type == "mysql":
        placeholders = ", ".join(["%s"] * len(valid_cols))
        return f"INSERT IGNORE INTO {quoted_table} ({quoted_cols}) VALUES ({placeholders});"
    elif db_type == "pg":
        placeholders = ", ".join(["%s"] * len(valid_cols))
        return f"INSERT INTO {quoted_table} ({quoted_cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
    else:
        raise ValueError(f"Unsupported db_type: {db_type}")


class FastAPIBackendStrategy(BackendStrategy):
    """
    FastAPI backend generation strategy. Uses SQLAlchemy and Alembic.
    """

    @property
    def name(self) -> str:
        return "fastapi"

    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        from sirius_cli.generator import get_env, render_template

        env = get_env()
        backend_path = os.path.join(project_path, "backend")

        backend_templates = {
            "backends/fastapi/database.py.jinja2": "database.py",
            "backends/fastapi/models.py.jinja2": "models.py",
            "backends/fastapi/schemas.py.jinja2": "schemas.py",
            "backends/fastapi/main.py.jinja2": "main.py",
            "backends/fastapi/requirements.txt.jinja2": "requirements.txt",
            "backends/fastapi/Dockerfile.jinja2": "Dockerfile",
        }

        if context.get("auth"):
            backend_templates["backends/fastapi/auth.py.jinja2"] = "auth.py"

        for t_path, dest_name in backend_templates.items():
            render_template(
                env, t_path, os.path.join(backend_path, dest_name), **context
            )

        # Write init file to make backend a python package
        with open(os.path.join(backend_path, "__init__.py"), "w") as f:
            f.write("# backend package\n")

    def _render_alembic_templates(self, backend_path: str, schemas: dict) -> None:
        from sirius_cli.generator import get_env, render_template

        env = get_env()
        # Render env.py config
        render_template(
            env,
            "backends/fastapi/alembic/env.py.jinja2",
            os.path.join(backend_path, "alembic", "env.py"),
            schemas=schemas,
        )
        # Render script.py.mako template
        render_template(
            env,
            "backends/fastapi/alembic/script.py.mako.jinja2",
            os.path.join(backend_path, "alembic", "script.py.mako"),
            schemas=schemas,
        )

    def post_init_setup(self, project_path: str, context: Dict[str, Any]) -> None:
        backend_path = os.path.join(project_path, "backend")
        db_type = context.get("db_type", "sqlite")
        schemas = context.get("schemas", {})

        typer.echo("Initializing Alembic migration system...")
        try:
            # Run alembic init (no shell=True)
            _run_alembic(["init", "alembic"], cwd=backend_path)

            # Write custom alembic migration runner templates
            self._render_alembic_templates(backend_path, schemas)

            # Modify alembic.ini target database config
            alembic_ini = os.path.join(backend_path, "alembic.ini")
            if os.path.exists(alembic_ini):
                with open(alembic_ini, "r") as f:
                    content = f.read()
                if db_type == "sqlite":
                    content = content.replace(
                        "sqlalchemy.url = driver://user:pass@localhost/dbname",
                        "sqlalchemy.url = sqlite:///./app.db",
                    )
                elif db_type == "pg":
                    content = content.replace(
                        "sqlalchemy.url = driver://user:pass@localhost/dbname",
                        "sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/app",
                    )
                elif db_type == "mysql":
                    content = content.replace(
                        "sqlalchemy.url = driver://user:pass@localhost/dbname",
                        "sqlalchemy.url = mysql+pymysql://root:root@localhost:3306/app",
                    )
                with open(alembic_ini, "w") as f:
                    f.write(content)

            # Generate initial autogenerated migration script
            typer.echo("Autogenerating migration scripts...")
            env = os.environ.copy()
            env["PYTHONPATH"] = project_path + os.pathsep + env.get("PYTHONPATH", "")
            _run_alembic(
                ["revision", "--autogenerate", "-m", "Initial migration"],
                cwd=backend_path,
                env=env,
            )

            # Apply initial migration structure to SQLite db
            typer.echo("Running database migrations...")
            _run_alembic(["upgrade", "head"], cwd=backend_path, env=env)

            typer.secho(
                "[OK] Alembic migration system initialized successfully!",
                fg=typer.colors.GREEN,
            )
        except Exception as e:
            typer.secho(
                f"[WARNING] Autogenerated Alembic migration failed: {e}",
                fg=typer.colors.YELLOW,
            )
            typer.echo(
                "You can configure database credentials and run migrations manually later."
            )

    def post_update_setup(
        self, project_path: str, context: Dict[str, Any], message: str
    ) -> None:
        backend_path = os.path.join(project_path, "backend")
        typer.echo("Generating Alembic migration...")
        env = os.environ.copy()
        env["PYTHONPATH"] = project_path + os.pathsep + env.get("PYTHONPATH", "")
        try:
            _run_alembic(
                ["revision", "--autogenerate", "-m", message], cwd=backend_path, env=env
            )
            typer.echo("Running database migrations...")
            _run_alembic(["upgrade", "head"], cwd=backend_path, env=env)
            typer.secho(
                "[OK] Database schema updated successfully!", fg=typer.colors.GREEN
            )
        except Exception as e:
            typer.secho(
                f"[WARNING] Autogenerated Alembic migration failed: {e}",
                fg=typer.colors.YELLOW,
            )
            typer.echo(
                "You can configure database credentials and run migrations manually later."
            )

    def seed_data(
        self,
        project_path: str,
        seed_files: List[str],
        db_type: str = "sqlite",
        db_url: Optional[str] = None,
    ) -> None:
        conn = None
        if db_type == "sqlite":
            db_path = os.path.join(project_path, "backend", "app.db")
            if not os.path.exists(db_path):
                return
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
        elif db_type == "pg":
            try:
                import psycopg2
            except ImportError:
                typer.secho(
                    "[WARNING] psycopg2 is not installed. Skipping PostgreSQL seeding.",
                    fg=typer.colors.YELLOW,
                )
                typer.echo("You can install psycopg2 and run seeds manually later.")
                return

            url = db_url or os.environ.get("DATABASE_URL")
            if not url:
                typer.secho(
                    "[WARNING] DATABASE_URL env var is not set. Skipping PostgreSQL seeding.",
                    fg=typer.colors.YELLOW,
                )
                typer.echo("Please configure DATABASE_URL and run seeds manually.")
                return

            try:
                normalized_url = url
                if normalized_url.startswith("postgresql+psycopg2://"):
                    normalized_url = normalized_url.replace(
                        "postgresql+psycopg2://", "postgresql://"
                    )
                conn = psycopg2.connect(normalized_url)
                cursor = conn.cursor()
            except Exception as e:
                typer.secho(
                    f"[WARNING] Could not connect to PostgreSQL database: {e}",
                    fg=typer.colors.YELLOW,
                )
                typer.echo(
                    "Please configure your database credentials and run seeds manually."
                )
                return
        elif db_type == "mysql":
            try:
                import pymysql
            except ImportError:
                typer.secho(
                    "[WARNING] pymysql is not installed. Skipping MySQL seeding.",
                    fg=typer.colors.YELLOW,
                )
                typer.echo("You can install pymysql and run seeds manually later.")
                return

            url = db_url or os.environ.get("DATABASE_URL")
            if not url:
                typer.secho(
                    "[WARNING] DATABASE_URL env var is not set. Skipping MySQL seeding.",
                    fg=typer.colors.YELLOW,
                )
                typer.echo("Please configure DATABASE_URL and run seeds manually.")
                return

            try:
                from urllib.parse import urlparse, unquote

                normalized_url = url
                if normalized_url.startswith("mysql+pymysql://"):
                    normalized_url = normalized_url.replace(
                        "mysql+pymysql://", "mysql://"
                    )
                parsed = urlparse(normalized_url)
                username = unquote(parsed.username) if parsed.username else ""
                password = unquote(parsed.password) if parsed.password else ""
                database = parsed.path.lstrip("/")
                conn = pymysql.connect(
                    host=parsed.hostname or "localhost",
                    port=parsed.port or 3306,
                    user=username,
                    password=password,
                    database=database,
                    autocommit=True,
                )
                cursor = conn.cursor()
            except Exception as e:
                typer.secho(
                    f"[WARNING] Could not connect to MySQL database: {e}",
                    fg=typer.colors.YELLOW,
                )
                typer.echo(
                    "Please configure your database credentials and run seeds manually."
                )
                return
        else:
            return

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
                            mapped_json_row: Dict[str, Any] = {}
                            for k, v in row.items():
                                sanitized_k = sanitize_column_name(str(k))
                                if v == "" or v is None:
                                    mapped_json_row[sanitized_k] = None
                                elif str(v).lower() == "true":
                                    mapped_json_row[sanitized_k] = 1
                                elif str(v).lower() == "false":
                                    mapped_json_row[sanitized_k] = 0
                                else:
                                    mapped_json_row[sanitized_k] = v
                            rows.append(mapped_json_row)

                        existing_cols = _get_existing_columns(
                            cursor, san_table, db_type
                        )
                        valid_cols = [c for c in san_cols if c in existing_cols]
                        if not valid_cols:
                            continue

                        query = _build_insert_query(san_table, valid_cols, db_type)

                        data_to_insert = []
                        for row in rows:
                            row_tuple = tuple(row.get(c) for c in valid_cols)
                            data_to_insert.append(row_tuple)

                        cursor.executemany(query, data_to_insert)
                    continue
                except Exception:
                    continue
            else:
                from sirius_cli.parser import sanitize_table_name, sanitize_column_name

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

            existing_cols = _get_existing_columns(cursor, table_name, db_type)
            valid_cols = [c for c in cols if c in existing_cols]
            if not valid_cols:
                continue

            query = _build_insert_query(table_name, valid_cols, db_type)

            data_to_insert = []
            for row in rows:
                row_tuple = tuple(row.get(c) for c in valid_cols)
                data_to_insert.append(row_tuple)

            cursor.executemany(query, data_to_insert)

        if conn:
            conn.commit()
            conn.close()
