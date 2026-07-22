import os
import secrets
import typer
from typing import List, Optional
import importlib.metadata
from sirius_cli.parser import (
    parse_csv_files,
    parse_sqlite_db,
    parse_config_file,
    parse_excel_files,
    parse_json_files,
)
from sirius_cli.generator import generate_project
from sirius_cli.preview import run_preview
from sirius_cli.fetcher import fetch_remote_file
from sirius_cli.backends import get_backend_strategy

app = typer.Typer(
    help="Sirius-CLI: A rapid prototyping backend and frontend code generator."
)


def version_callback(value: bool):
    if value:
        try:
            version = importlib.metadata.version("sirius-cli")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
        typer.echo(f"Sirius-CLI version: {version}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=version_callback,
        is_eager=True,
    )
):
    pass


@app.command()
def init(
    project_name: Optional[str] = typer.Argument(
        None, help="The name of the project directory to create"
    ),
    csv: Optional[List[str]] = typer.Option(
        None, "--csv", help="Paths to input CSV files (can declare multiple times)"
    ),
    excel: Optional[List[str]] = typer.Option(
        None,
        "--excel",
        help="Paths to input Excel (.xlsx/.xls) files (can declare multiple times)",
    ),
    json: Optional[List[str]] = typer.Option(
        None,
        "--json",
        help="Paths to input JSON data files (can declare multiple times)",
    ),
    db: Optional[str] = typer.Option(
        None, "--db", help="Path to input SQLite database file"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to JSON configuration file"
    ),
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help="Color theme for the frontend (e.g. blue, indigo, emerald, amber, rose, sky, violet)",
    ),
    out: str = typer.Option(".", "--out", "-o", help="Target output directory"),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Backend server port (used in docker-compose and .env)",
    ),
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        help="Override the frontend VITE_API_URL (default: http://localhost:<port>)",
    ),
    no_seed: bool = typer.Option(
        False, "--no-seed", help="Skip seeding the database from CSV/Excel files"
    ),
    pg: bool = typer.Option(False, "--pg", help="Use PostgreSQL instead of SQLite"),
    mysql: bool = typer.Option(False, "--mysql", help="Use MySQL instead of SQLite"),
    auth: bool = typer.Option(
        False, "--auth", help="Generate JWT authentication logic"
    ),
    admin_user: str = typer.Option(
        "admin", "--admin-user", help="Default admin username if --auth is used"
    ),
    admin_pass: Optional[str] = typer.Option(
        None,
        "--admin-pass",
        help="Admin password if --auth is used (auto-generated if not provided)",
    ),
    from_url: Optional[List[str]] = typer.Option(
        None,
        "--from-url",
        help="URL(s) of a public CSV/JSON/Excel file to fetch and scaffold from (repeatable)",
    ),
    backend: str = typer.Option(
        "fastapi",
        "--backend",
        help="Backend framework to generate (fastapi, flask, django)",
    ),
):
    """Initializes a new FastAPI backend and React frontend stack from data files or configuration."""
    if backend not in ("fastapi", "flask", "django"):
        typer.secho(
            f"Error: Unsupported backend '{backend}'. Supported options: fastapi, flask, django.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if backend in ("flask", "django"):
        typer.secho(
            f"Error: Backend '{backend}' is not supported yet. Coming in a future release!",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    backend_strategy = get_backend_strategy(backend)

    # Ensure one and only one source parameter is provided
    inputs = [
        bool(csv),
        bool(excel),
        bool(json),
        bool(db),
        bool(config),
        bool(from_url),
    ]
    if sum(inputs) != 1:
        typer.secho(
            "Error: You must provide exactly one input option: --csv, --excel, --json, --db, --config, or --from-url.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Resolve remote URLs into local cached files
    if from_url:
        typer.echo("Fetching remote file(s)...")
        try:
            fetched_paths = [str(fetch_remote_file(u)) for u in from_url]
        except Exception as e:
            typer.secho(
                f"Error fetching remote file: {e}", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(code=1)
        # Classify by extension and route to the correct parser
        from pathlib import Path as _Path

        csv_like = [p for p in fetched_paths if _Path(p).suffix.lower() == ".csv"]
        excel_like = [
            p for p in fetched_paths if _Path(p).suffix.lower() in (".xlsx", ".xls")
        ]
        json_like = [p for p in fetched_paths if _Path(p).suffix.lower() == ".json"]
        if csv_like:
            csv = csv_like
        elif excel_like:
            excel = excel_like
        elif json_like:
            import json as _json

            try:
                with open(json_like[0], "r", encoding="utf-8") as jf:
                    jdata = _json.load(jf)
                if isinstance(jdata, dict) and "entities" in jdata:
                    config = json_like[0]
                else:
                    json = json_like
            except Exception:
                config = json_like[0]

    # If --auth is used and no password provided, generate a secure random one
    if auth and not admin_pass:
        admin_pass = secrets.token_urlsafe(16)
        typer.secho(
            f"\n[AUTH] Auto-generated admin password: {admin_pass}",
            fg=typer.colors.BRIGHT_YELLOW,
            bold=True,
        )
        typer.secho(
            "   Save this password -- it will not be shown again.\n",
            fg=typer.colors.YELLOW,
        )
    elif not auth:
        admin_pass = admin_pass or "admin"

    # Resolve API URL
    resolved_api_url = api_url or f"http://localhost:{port}"

    db_type = "sqlite"
    if pg:
        db_type = "pg"
    elif mysql:
        db_type = "mysql"

    typer.echo("Analyzing schema structure...")
    try:
        if csv:
            schemas = parse_csv_files(csv)
            resolved_theme = theme or "blue"
            if not project_name:
                typer.secho(
                    "Error: Project name argument is required when using --csv.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
        elif excel:
            schemas = parse_excel_files(excel)
            resolved_theme = theme or "blue"
            if not project_name:
                typer.secho(
                    "Error: Project name argument is required when using --excel.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
        elif json:
            schemas = parse_json_files(json)
            resolved_theme = theme or "blue"
            if not project_name:
                typer.secho(
                    "Error: Project name argument is required when using --json.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
        elif db:
            schemas = parse_sqlite_db(db)
            resolved_theme = theme or "blue"
            if not project_name:
                typer.secho(
                    "Error: Project name argument is required when using --db.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
        elif config:  # config
            schemas, cfg_project_name, cfg_theme = parse_config_file(config)
            resolved_theme = theme or cfg_theme
            project_name = project_name or cfg_project_name
            if not project_name:
                typer.secho(
                    "Error: Project name must be provided as an argument or defined in the configuration file.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error parsing schemas: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    assert project_name is not None
    assert admin_pass is not None

    dest_dir = os.path.abspath(os.path.join(out, project_name))
    typer.echo(
        f"Scaffolding project in: {dest_dir} (Theme: {resolved_theme}, Port: {port}, DB: {db_type})"
    )

    try:
        generate_project(
            dest_dir,
            schemas,
            backend_strategy,
            project_name=project_name,
            theme=resolved_theme,
            port=port,
            api_url=resolved_api_url,
            db_type=db_type,
            auth=auth,
            admin_user=admin_user,
            admin_pass=admin_pass,
        )
    except Exception as e:
        typer.secho(f"Error generating files: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    ctx = dict(
        schemas=schemas,
        project_name=project_name,
        theme=resolved_theme,
        port=port,
        api_url=resolved_api_url,
        db_type=db_type,
        auth=auth,
        admin_user=admin_user,
        admin_pass=admin_pass,
    )
    backend_strategy.post_init_setup(dest_dir, ctx)

    # Seed initial data if building from CSVs, Excel, or JSON files
    seed_paths = list(csv or []) + list(excel or []) + list(json or [])
    if seed_paths and not no_seed:
        if db_type == "sqlite":
            typer.echo("Seeding initial data from source files...")
            try:
                backend_strategy.seed_data(dest_dir, seed_paths)
                typer.secho("[OK] Database seeded successfully!", fg=typer.colors.GREEN)
            except Exception as se:
                typer.secho(
                    f"[WARNING] Database seeding failed: {se}",
                    fg=typer.colors.YELLOW,
                )
        else:
            typer.secho(
                "[SKIP] CSV/Excel seeding is only supported for SQLite at scaffold time. Skipping.",
                fg=typer.colors.YELLOW,
            )
    elif no_seed:
        typer.secho(
            "[SKIP] Database seeding skipped (--no-seed).", fg=typer.colors.YELLOW
        )

    typer.secho(
        f"\n[SUCCESS] Project '{project_name}' has been created.",
        fg=typer.colors.GREEN,
        bold=True,
    )
    typer.echo("To run the stack with docker compose:")
    typer.secho(
        f"  cd {project_name} && docker compose up --build", fg=typer.colors.CYAN
    )
    typer.echo("To start individual servers locally:")
    typer.secho(
        f"  Backend:  cd {project_name} && pip install -r backend/requirements.txt && uvicorn backend.main:app --reload --port {port}",
        fg=typer.colors.CYAN,
    )
    typer.secho(
        f"  Frontend: cd {project_name}/frontend && npm install && npm run dev",
        fg=typer.colors.CYAN,
    )
    typer.secho(f"  API URL:  {resolved_api_url}", fg=typer.colors.CYAN)


@app.command()
def update(
    project_path: str = typer.Argument(..., help="Path to existing project directory"),
    csv: Optional[List[str]] = typer.Option(
        None, "--csv", help="Paths to input CSV files"
    ),
    excel: Optional[List[str]] = typer.Option(
        None, "--excel", help="Paths to input Excel files"
    ),
    json: Optional[List[str]] = typer.Option(
        None, "--json", help="Paths to input JSON data files"
    ),
    db: Optional[str] = typer.Option(None, "--db", help="Path to input SQLite db"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to JSON config"
    ),
    message: str = typer.Option(
        "Auto-update schema", "-m", help="Alembic migration message"
    ),
    theme: str = typer.Option(
        "blue", "--theme", "-t", help="Color theme for the frontend (defaults to blue)"
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Backend server port (used in docker-compose and .env)",
    ),
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        help="Override the frontend VITE_API_URL (default: http://localhost:<port>)",
    ),
    pg: bool = typer.Option(False, "--pg", help="Use PostgreSQL instead of SQLite"),
    mysql: bool = typer.Option(False, "--mysql", help="Use MySQL instead of SQLite"),
    auth: bool = typer.Option(
        False, "--auth", help="Generate JWT authentication logic"
    ),
    admin_user: str = typer.Option(
        "admin", "--admin-user", help="Default admin username if --auth is used"
    ),
    admin_pass: Optional[str] = typer.Option(
        None,
        "--admin-pass",
        help="Admin password if --auth is used (auto-generated if not provided)",
    ),
    from_url: Optional[List[str]] = typer.Option(
        None,
        "--from-url",
        help="URL(s) of a public CSV/JSON/Excel file to fetch and scaffold from (repeatable)",
    ),
    backend: str = typer.Option(
        "fastapi",
        "--backend",
        help="Backend framework to generate (fastapi, flask, django)",
    ),
):
    """Updates an existing project with new columns/tables."""
    if backend not in ("fastapi", "flask", "django"):
        typer.secho(
            f"Error: Unsupported backend '{backend}'. Supported options: fastapi, flask, django.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if backend in ("flask", "django"):
        typer.secho(
            f"Error: Backend '{backend}' is not supported yet. Coming in a future release!",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    backend_strategy = get_backend_strategy(backend)

    if not os.path.exists(project_path):
        typer.secho(
            f"Error: Project path '{project_path}' does not exist.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    inputs = [
        bool(csv),
        bool(excel),
        bool(json),
        bool(db),
        bool(config),
        bool(from_url),
    ]
    if sum(inputs) != 1:
        typer.secho(
            "Error: You must provide exactly one input option: --csv, --excel, --json, --db, --config, or --from-url.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Resolve remote URLs into local cached files
    if from_url:
        typer.echo("Fetching remote file(s)...")
        try:
            fetched_paths = [str(fetch_remote_file(u)) for u in from_url]
        except Exception as e:
            typer.secho(
                f"Error fetching remote file: {e}", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(code=1)
        from pathlib import Path as _Path

        csv_like = [p for p in fetched_paths if _Path(p).suffix.lower() == ".csv"]
        excel_like = [
            p for p in fetched_paths if _Path(p).suffix.lower() in (".xlsx", ".xls")
        ]
        json_like = [p for p in fetched_paths if _Path(p).suffix.lower() == ".json"]
        if csv_like:
            csv = csv_like
        elif excel_like:
            excel = excel_like
        elif json_like:
            import json as _json

            try:
                with open(json_like[0], "r", encoding="utf-8") as jf:
                    jdata = _json.load(jf)
                if isinstance(jdata, dict) and "entities" in jdata:
                    config = json_like[0]
                else:
                    json = json_like
            except Exception:
                config = json_like[0]

    # If --auth is used and no password provided, generate a secure random one
    if auth and not admin_pass:
        admin_pass = secrets.token_urlsafe(16)
        typer.secho(
            f"\n[AUTH] Auto-generated admin password: {admin_pass}",
            fg=typer.colors.BRIGHT_YELLOW,
            bold=True,
        )
        typer.secho(
            "   Save this password -- it will not be shown again.\n",
            fg=typer.colors.YELLOW,
        )
    elif not auth:
        admin_pass = admin_pass or "admin"

    resolved_api_url = api_url or f"http://localhost:{port}"

    db_type = "sqlite"
    if pg:
        db_type = "pg"
    elif mysql:
        db_type = "mysql"

    typer.echo("Analyzing new schema structure...")
    try:
        if csv:
            schemas = parse_csv_files(csv)
        elif excel:
            schemas = parse_excel_files(excel)
        elif json:
            schemas = parse_json_files(json)
        elif db:
            schemas = parse_sqlite_db(db)
        elif config:  # config
            schemas, _, _ = parse_config_file(config)
    except Exception as e:
        typer.secho(f"Error parsing schemas: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Extract project name from path for template context
    project_name = os.path.basename(os.path.abspath(project_path))

    typer.echo(f"Updating project in: {project_path}")
    assert admin_pass is not None
    try:
        generate_project(
            project_path,
            schemas,
            backend_strategy,
            project_name=project_name,
            theme=theme,
            port=port,
            api_url=resolved_api_url,
            db_type=db_type,
            auth=auth,
            admin_user=admin_user,
            admin_pass=admin_pass,
        )
    except Exception as e:
        typer.secho(f"Error generating files: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    ctx = dict(
        schemas=schemas,
        project_name=project_name,
        theme=theme,
        port=port,
        api_url=resolved_api_url,
        db_type=db_type,
        auth=auth,
        admin_user=admin_user,
        admin_pass=admin_pass,
    )
    backend_strategy.post_update_setup(project_path, ctx, message)

    typer.secho(
        f"\n[SUCCESS] Project '{project_path}' has been updated.",
        fg=typer.colors.GREEN,
        bold=True,
    )


@app.command()
def preview(
    csv: Optional[List[str]] = typer.Option(
        None, "--csv", help="Paths to input CSV files"
    ),
    excel: Optional[List[str]] = typer.Option(
        None, "--excel", help="Paths to input Excel files"
    ),
    json: Optional[List[str]] = typer.Option(
        None, "--json", help="Paths to input JSON data files"
    ),
    db: Optional[str] = typer.Option(None, "--db", help="Path to input SQLite db"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to JSON config"
    ),
    port: int = typer.Option(8765, "--port", "-p", help="Port for the preview server"),
    from_url: Optional[List[str]] = typer.Option(
        None,
        "--from-url",
        help="URL(s) of a public CSV/JSON/Excel file to fetch and preview from (repeatable)",
    ),
):
    """Instantly preview a generated UI based on schema sources without creating files."""
    inputs = [
        bool(csv),
        bool(excel),
        bool(json),
        bool(db),
        bool(config),
        bool(from_url),
    ]
    if sum(inputs) != 1:
        typer.secho(
            "Error: You must provide exactly one input option: --csv, --excel, --json, --db, --config, or --from-url.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Resolve remote URLs into local cached files
    if from_url:
        typer.echo("Fetching remote file(s)...")
        try:
            fetched_paths = [str(fetch_remote_file(u)) for u in from_url]
        except Exception as e:
            typer.secho(
                f"Error fetching remote file: {e}", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(code=1)
        from pathlib import Path as _Path

        csv_like = [p for p in fetched_paths if _Path(p).suffix.lower() == ".csv"]
        excel_like = [
            p for p in fetched_paths if _Path(p).suffix.lower() in (".xlsx", ".xls")
        ]
        json_like = [p for p in fetched_paths if _Path(p).suffix.lower() == ".json"]
        if csv_like:
            csv = csv_like
        elif excel_like:
            excel = excel_like
        elif json_like:
            import json as _json

            try:
                with open(json_like[0], "r", encoding="utf-8") as jf:
                    jdata = _json.load(jf)
                if isinstance(jdata, dict) and "entities" in jdata:
                    config = json_like[0]
                else:
                    json = json_like
            except Exception:
                config = json_like[0]

    typer.echo("Parsing schemas for preview...")
    try:
        if csv:
            schemas = parse_csv_files(csv)
        elif excel:
            schemas = parse_excel_files(excel)
        elif json:
            schemas = parse_json_files(json)
        elif db:
            schemas = parse_sqlite_db(db)
        elif config:  # config
            schemas, _, _ = parse_config_file(config)
    except Exception as e:
        typer.secho(f"Error parsing schemas: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo("Starting preview server...")
    run_preview(
        schemas,
        port=port,
        db_path=db,
        csv_paths=csv,
        excel_paths=excel,
        json_paths=json,
    )


if __name__ == "__main__":
    app()
