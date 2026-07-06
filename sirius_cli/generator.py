import os
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

def get_env():
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def render_template(env, template_name, dest_path, **kwargs):
    template = env.get_template(template_name)
    content = template.render(**kwargs)
    
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

def generate_project(
    project_path: str, schemas: dict, theme: str = "blue", 
    port: int = 8000, api_url: str = "http://localhost:8000", db_type: str = "sqlite",
    auth: bool = False, admin_user: str = "admin", admin_pass: str = "admin"
):
    """Generates complete FastAPI and React frontend files structure based on inferred schemas and theme."""
    env = get_env()
    
    # 1. Root docker-compose configuration
    render_template(
        env,
        "docker-compose.yml.jinja2",
        os.path.join(project_path, "docker-compose.yml"),
        schemas=schemas,
        theme=theme,
        port=port,
        api_url=api_url,
        db_type=db_type,
        auth=auth,
        admin_user=admin_user,
        admin_pass=admin_pass
    )
    
    # 2. Backend FastAPI application files
    backend_path = os.path.join(project_path, "backend")
    
    backend_templates = {
        "backend/database.py.jinja2": "database.py",
        "backend/models.py.jinja2": "models.py",
        "backend/schemas.py.jinja2": "schemas.py",
        "backend/main.py.jinja2": "main.py",
        "backend/requirements.txt.jinja2": "requirements.txt",
        "backend/Dockerfile.jinja2": "Dockerfile"
    }
    
    if auth:
        backend_templates["backend/auth.py.jinja2"] = "auth.py"
        
    for t_path, dest_name in backend_templates.items():
        render_template(
            env,
            t_path,
            os.path.join(backend_path, dest_name),
            schemas=schemas,
            theme=theme,
            port=port,
            api_url=api_url,
            db_type=db_type,
            auth=auth,
            admin_user=admin_user,
            admin_pass=admin_pass
        )
        
    # Write init file to make backend a python package
    with open(os.path.join(backend_path, "__init__.py"), "w") as f:
        f.write("# backend package\n")
        
    # 3. Frontend React configurator files
    frontend_path = os.path.join(project_path, "frontend")
    
    frontend_templates = {
        "frontend/index.html.jinja2": "index.html",
        "frontend/package.json.jinja2": "package.json",
        "frontend/tsconfig.json.jinja2": "tsconfig.json",
        "frontend/vite.config.ts.jinja2": "vite.config.ts",
        "frontend/tailwind.config.js.jinja2": "tailwind.config.js",
        "frontend/postcss.config.js.jinja2": "postcss.config.js",
        "frontend/Dockerfile.jinja2": "Dockerfile",
        "frontend/.env.jinja2": ".env",
        "frontend/src/main.tsx.jinja2": "src/main.tsx",
        "frontend/src/index.css.jinja2": "src/index.css",
        "frontend/src/App.tsx.jinja2": "src/App.tsx",
        "frontend/src/Dashboard.tsx.jinja2": "src/Dashboard.tsx"
    }
    
    if auth:
        frontend_templates["frontend/src/Login.tsx.jinja2"] = "src/pages/Login.tsx"
        
    for t_path, dest_name in frontend_templates.items():
        render_template(
            env,
            t_path,
            os.path.join(frontend_path, dest_name),
            schemas=schemas,
            theme=theme,
            port=port,
            api_url=api_url,
            db_type=db_type,
            auth=auth,
            admin_user=admin_user,
            admin_pass=admin_pass
        )
        
    # 4. Generate dynamic CRUD view pages for each table
    for table_name, columns in schemas.items():
        pascal_name = table_name.replace('_', ' ').title().replace(' ', '')
        dest_crud_path = os.path.join(frontend_path, "src", "pages", f"{pascal_name}Crud.tsx")
        render_template(
            env,
            "frontend/src/TableCrud.tsx.jinja2",
            dest_crud_path,
            table_name=table_name,
            columns=columns,
            theme=theme,
            port=port,
            api_url=api_url,
            db_type=db_type,
            auth=auth,
            admin_user=admin_user,
            admin_pass=admin_pass
        )

def render_alembic_files(backend_path: str, schemas: dict):
    """Helper to render Alembic migration template files after init command is run."""
    env = get_env()
    # Render env.py config
    render_template(
        env,
        "backend/alembic/env.py.jinja2",
        os.path.join(backend_path, "alembic", "env.py"),
        schemas=schemas
    )
    # Render script.py.mako template
    render_template(
        env,
        "backend/alembic/script.py.mako.jinja2",
        os.path.join(backend_path, "alembic", "script.py.mako"),
        schemas=schemas
    )
