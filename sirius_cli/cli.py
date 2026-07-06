import os
import csv
import sqlite3
import subprocess
import typer
from pathlib import Path
from typing import List, Optional
from sirius_cli.parser import parse_csv_files, parse_sqlite_db, parse_config_file, parse_excel_files, sanitize_table_name, sanitize_column_name
from sirius_cli.generator import generate_project, render_alembic_files

app = typer.Typer(help="Sirius-CLI: A rapid prototyping backend and frontend code generator.")

def seed_database_from_csvs(project_path: str, csv_paths: list):
    """Seeds the generated SQLite database with the row entries from the source CSVs."""
    db_path = os.path.join(project_path, "backend", "app.db")
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for path in csv_paths:
        if not os.path.exists(path):
            continue

        # Normalise xlsx → in-memory CSV rows via pandas
        ext = Path(path).suffix.lower()
        if ext in (".xlsx", ".xls"):
            try:
                import pandas as pd
                df = pd.read_excel(path)
                all_rows = df.to_dict(orient="records")
                fieldnames = list(df.columns)
            except Exception:
                continue
        else:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                fieldnames = list(reader.fieldnames)
                all_rows = list(reader)
            
        table_name = sanitize_table_name(path)
        cols = [sanitize_column_name(c) for c in fieldnames]
        
        rows = []
        for row in all_rows:
            mapped_row = {}
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
            
        if not rows:
            continue
            
        # Verify columns exist in target table
        cursor.execute(f"PRAGMA table_info({table_name});")
        existing_cols = {info[1] for info in cursor.fetchall()}
        
        valid_cols = [c for c in cols if c in existing_cols]
        if not valid_cols:
            continue
            
        placeholders = ", ".join(["?"] * len(valid_cols))
        col_names_str = ", ".join(valid_cols)
        query = f"INSERT OR IGNORE INTO {table_name} ({col_names_str}) VALUES ({placeholders});"
        
        data_to_insert = []
        for row in rows:
            row_tuple = tuple(row.get(c) for c in valid_cols)
            data_to_insert.append(row_tuple)
            
        cursor.executemany(query, data_to_insert)
        
    conn.commit()
    conn.close()

@app.command()
def init(
    project_name: Optional[str] = typer.Argument(None, help="The name of the project directory to create"),
    csv: Optional[List[str]] = typer.Option(None, "--csv", help="Paths to input CSV files (can declare multiple times)"),
    excel: Optional[List[str]] = typer.Option(None, "--excel", help="Paths to input Excel (.xlsx/.xls) files (can declare multiple times)"),
    db: Optional[str] = typer.Option(None, "--db", help="Path to input SQLite database file"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to JSON configuration file"),
    theme: Optional[str] = typer.Option(None, "--theme", "-t", help="Color theme for the frontend (e.g. blue, indigo, emerald, amber, rose, sky, violet)"),
    out: str = typer.Option(".", "--out", "-o", help="Target output directory"),
    port: int = typer.Option(8000, "--port", "-p", help="Backend server port (used in docker-compose and .env)"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Override the frontend VITE_API_URL (default: http://localhost:<port>)"),
    no_seed: bool = typer.Option(False, "--no-seed", help="Skip seeding the database from CSV/Excel files"),
    pg: bool = typer.Option(False, "--pg", help="Use PostgreSQL instead of SQLite"),
    mysql: bool = typer.Option(False, "--mysql", help="Use MySQL instead of SQLite")
):
    """Initializes a new FastAPI backend and React frontend stack from data files or configuration."""
    # Ensure one and only one source parameter is provided
    inputs = [bool(csv), bool(excel), bool(db), bool(config)]
    if sum(inputs) != 1:
        typer.secho("Error: You must provide exactly one input option: --csv, --excel, --db, or --config.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

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
                typer.secho("Error: Project name argument is required when using --csv.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
        elif excel:
            schemas = parse_excel_files(excel)
            resolved_theme = theme or "blue"
            if not project_name:
                typer.secho("Error: Project name argument is required when using --excel.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
        elif db:
            schemas = parse_sqlite_db(db)
            resolved_theme = theme or "blue"
            if not project_name:
                typer.secho("Error: Project name argument is required when using --db.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
        else:  # config
            schemas, cfg_project_name, cfg_theme = parse_config_file(config)
            resolved_theme = theme or cfg_theme
            project_name = project_name or cfg_project_name
            if not project_name:
                typer.secho("Error: Project name must be provided as an argument or defined in the configuration file.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error parsing schemas: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
        
    dest_dir = os.path.abspath(os.path.join(out, project_name))
    typer.echo(f"Scaffolding project in: {dest_dir} (Theme: {resolved_theme}, Port: {port}, DB: {db_type})")
    
    try:
        generate_project(dest_dir, schemas, theme=resolved_theme, port=port, api_url=resolved_api_url, db_type=db_type)
    except Exception as e:
        typer.secho(f"Error generating files: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
        
    backend_path = os.path.join(dest_dir, "backend")
    
    typer.echo("Initializing Alembic migration system...")
    try:
        # Run alembic init
        subprocess.run(
            "alembic init alembic",
            cwd=backend_path,
            check=True,
            shell=True,
            stdout=subprocess.DEVNULL
        )
        
        # Write custom alembic migration runner templates
        render_alembic_files(backend_path, schemas)
        
        # Modify alembic.ini target database config
        alembic_ini = os.path.join(backend_path, "alembic.ini")
        if os.path.exists(alembic_ini):
            with open(alembic_ini, "r") as f:
                content = f.read()
            if db_type == 'sqlite':
                content = content.replace(
                    "sqlalchemy.url = driver://user:pass@localhost/dbname",
                    "sqlalchemy.url = sqlite:///./app.db"
                )
            elif db_type == 'pg':
                content = content.replace(
                    "sqlalchemy.url = driver://user:pass@localhost/dbname",
                    "sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/app"
                )
            elif db_type == 'mysql':
                content = content.replace(
                    "sqlalchemy.url = driver://user:pass@localhost/dbname",
                    "sqlalchemy.url = mysql+pymysql://root:root@localhost:3306/app"
                )
            with open(alembic_ini, "w") as f:
                f.write(content)
                
        # Generate initial autogenerated migration script
        typer.echo("Autogenerating migration scripts...")
        env = os.environ.copy()
        env["PYTHONPATH"] = dest_dir + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run(
            "alembic revision --autogenerate -m \"Initial migration\"",
            cwd=backend_path,
            check=True,
            shell=True,
            env=env,
            stdout=subprocess.DEVNULL
        )
        
        # Apply initial migration structure to SQLite db
        typer.echo("Running database migrations...")
        subprocess.run(
            "alembic upgrade head",
            cwd=backend_path,
            check=True,
            shell=True,
            env=env,
            stdout=subprocess.DEVNULL
        )
        
        typer.secho("[OK] Alembic migration system initialized successfully!", fg=typer.colors.GREEN)
        
        # Seed initial data if building from CSVs or Excel files
        seed_paths = list(csv or []) + list(excel or [])
        if seed_paths and not no_seed:
            if db_type == "sqlite":
                typer.echo("Seeding initial data from source files...")
                try:
                    seed_database_from_csvs(dest_dir, seed_paths)
                    typer.secho("[OK] Database seeded successfully!", fg=typer.colors.GREEN)
                except Exception as se:
                    typer.secho(f"[WARNING] Database seeding failed: {se}", fg=typer.colors.YELLOW)
            else:
                typer.secho(f"[SKIP] CSV/Excel seeding is only supported for SQLite at scaffold time. Skipping.", fg=typer.colors.YELLOW)
        elif no_seed:
            typer.secho("[SKIP] Database seeding skipped (--no-seed).", fg=typer.colors.YELLOW)
                
    except Exception as e:
        typer.secho(f"[WARNING] Autogenerated Alembic migration failed: {e}", fg=typer.colors.YELLOW)
        typer.echo("You can configure database credentials and run migrations manually later.")
        
    typer.secho(f"\n[SUCCESS] Project '{project_name}' has been created.", fg=typer.colors.GREEN, bold=True)
    typer.echo("To run the stack with docker compose:")
    typer.secho(f"  cd {project_name} && docker compose up --build", fg=typer.colors.CYAN)
    typer.echo("To start individual servers locally:")
    typer.secho(f"  Backend:  cd {project_name}/backend && pip install -r requirements.txt && uvicorn backend.main:app --reload --port {port}", fg=typer.colors.CYAN)
    typer.secho(f"  Frontend: cd {project_name}/frontend && npm install && npm run dev", fg=typer.colors.CYAN)
    typer.secho(f"  API URL:  {resolved_api_url}", fg=typer.colors.CYAN)

@app.command()
def update(
    project_path: str = typer.Argument(..., help="Path to existing project directory"),
    csv: Optional[List[str]] = typer.Option(None, "--csv", help="Paths to input CSV files"),
    excel: Optional[List[str]] = typer.Option(None, "--excel", help="Paths to input Excel files"),
    db: Optional[str] = typer.Option(None, "--db", help="Path to input SQLite db"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to JSON config"),
    message: str = typer.Option("Auto-update schema", "-m", help="Alembic migration message"),
    theme: Optional[str] = typer.Option("blue", "--theme", "-t", help="Color theme for the frontend (defaults to blue)"),
    port: int = typer.Option(8000, "--port", "-p", help="Backend server port (used in docker-compose and .env)"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Override the frontend VITE_API_URL (default: http://localhost:<port>)"),
    pg: bool = typer.Option(False, "--pg", help="Use PostgreSQL instead of SQLite"),
    mysql: bool = typer.Option(False, "--mysql", help="Use MySQL instead of SQLite")
):
    """Updates an existing project with new columns/tables."""
    if not os.path.exists(project_path):
        typer.secho(f"Error: Project path '{project_path}' does not exist.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    inputs = [bool(csv), bool(excel), bool(db), bool(config)]
    if sum(inputs) != 1:
        typer.secho("Error: You must provide exactly one input option: --csv, --excel, --db, or --config.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

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
        elif db:
            schemas = parse_sqlite_db(db)
        else:  # config
            schemas, _, _ = parse_config_file(config)
    except Exception as e:
        typer.secho(f"Error parsing schemas: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Updating project in: {project_path}")
    try:
        generate_project(project_path, schemas, theme=theme, port=port, api_url=resolved_api_url, db_type=db_type)
    except Exception as e:
        typer.secho(f"Error generating files: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    backend_path = os.path.join(project_path, "backend")

    typer.echo("Generating Alembic migration...")
    env = os.environ.copy()
    env["PYTHONPATH"] = project_path + os.pathsep + env.get("PYTHONPATH", "")
    try:
        subprocess.run(
            f"alembic revision --autogenerate -m \"{message}\"",
            cwd=backend_path,
            check=True,
            shell=True,
            env=env,
            stdout=subprocess.DEVNULL
        )
        
        typer.echo("Running database migrations...")
        subprocess.run(
            "alembic upgrade head",
            cwd=backend_path,
            check=True,
            shell=True,
            env=env,
            stdout=subprocess.DEVNULL
        )
        typer.secho("[OK] Database schema updated successfully!", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"[WARNING] Autogenerated Alembic migration failed: {e}", fg=typer.colors.YELLOW)
        typer.echo("You can configure database credentials and run migrations manually later.")

    typer.secho(f"\n[SUCCESS] Project '{project_path}' has been updated.", fg=typer.colors.GREEN, bold=True)

if __name__ == "__main__":
    app()
