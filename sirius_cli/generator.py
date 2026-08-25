import os
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sirius_cli.backends.base import BackendStrategy
from sirius_cli.frontends.base import FrontendStrategy
from sirius_cli.frontends.react import ReactFrontendStrategy

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def get_env():
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(
            enabled_extensions=("html", "xml"),
            default_for_string=False,
        ),
    )


def render_template(env, template_name, dest_path, **kwargs):
    template = env.get_template(template_name)
    content = template.render(**kwargs)

    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_project(
    project_path: str,
    schemas: dict,
    backend_strategy: BackendStrategy,
    frontend_strategy: Optional[FrontendStrategy] = None,
    project_name: str = "app",
    theme: str = "blue",
    port: int = 8000,
    api_url: str = "http://localhost:8000",
    db_type: str = "sqlite",
    auth: bool = False,
    admin_user: str = "admin",
    admin_pass: str = "admin",  # nosec B107
):
    """Generates complete backend and frontend files structure based on inferred schemas and theme."""
    if frontend_strategy is None:
        frontend_strategy = ReactFrontendStrategy()
    env = get_env()
    backend_labels = {"fastapi": "FastAPI", "flask": "Flask", "django": "Django"}
    frontend_labels = {"react": "React SPA", "vue": "Vue SPA", "svelte": "SvelteKit"}
    backend_name = getattr(backend_strategy, "name", "fastapi")
    frontend_name = getattr(frontend_strategy, "name", "react")
    backend_label = backend_labels.get(backend_name, backend_name.capitalize())
    frontend_label = frontend_labels.get(frontend_name, frontend_name.capitalize())

    # Shared template context — all templates receive all variables
    ctx = dict(
        schemas=schemas,
        project_name=project_name,
        theme=theme,
        port=port,
        api_url=api_url,
        db_type=db_type,
        auth=auth,
        admin_user=admin_user,
        admin_pass=admin_pass,
        backend_name=backend_name,
        frontend_name=frontend_name,
        backend_label=backend_label,
        frontend_label=frontend_label,
    )

    # 1. Root docker-compose configuration
    render_template(
        env,
        "docker-compose.yml.jinja2",
        os.path.join(project_path, "docker-compose.yml"),
        **ctx,
    )

    # 2. Generate Backend-specific files using Strategy
    backend_strategy.generate_files(project_path, ctx)

    # Generate .env.example for production documentation
    _generate_env_example(project_path, db_type, auth, port)

    # 3. Generate Frontend-specific files using Strategy
    frontend_strategy.generate_files(project_path, ctx)


def _generate_env_example(project_path: str, db_type: str, auth: bool, port: int):
    """Generates a .env.example file documenting required environment variables."""
    lines = [
        "# ===================================================================",
        "# Environment Variables -- copy this file to .env and fill in values",
        "# ===================================================================",
        "",
        "# Backend server port",
        f"PORT={port}",
        "",
    ]

    if db_type == "pg":
        lines += [
            "# PostgreSQL connection string",
            "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app",
            "",
        ]
    elif db_type == "mysql":
        lines += [
            "# MySQL connection string",
            "DATABASE_URL=mysql+pymysql://root:root@localhost:3306/app",
            "",
        ]

    if auth:
        lines += [
            "# JWT Secret Key -- MUST be changed in production",
            '# Generate one with: python -c "import secrets; print(secrets.token_hex(32))"',
            "SECRET_KEY=change-me-in-production",
            "",
        ]

    lines += [
        "# Frontend API URL",
        f"VITE_API_URL=http://localhost:{port}",
        "",
    ]

    env_example_path = os.path.join(project_path, ".env.example")
    os.makedirs(project_path, exist_ok=True)
    with open(env_example_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
