# How Sirius-CLI Works

This document explains the internal mechanics of Sirius-CLI, helping developers understand how input data (CSV, Excel, SQLite, or JSON) is automatically transformed into a fully-functional, containerized React + FastAPI application.

## 1. Data Ingestion & Inference
Depending on your input format, Sirius-CLI takes a different approach to understand your data:

- **CSV & Excel**: Sirius-CLI reads the files using `pandas`. It infers SQL data types based on column content (e.g., recognizing numeric IDs, floats, strings, or booleans). It then uses intelligent naming heuristics to infer relationships. For instance, if an `orders` file has a column named `customer_id`, the CLI automatically resolves this as a foreign key pointing to the `customers` table.
- **SQLite Database (`.db`)**: It connects to your existing database and uses SQLAlchemy's Inspector to read the exact schema, column types, and explicitly defined foreign key constraints, guaranteeing 100% accuracy.
- **JSON Configuration**: It parses your explicit schema definitions and theme configurations directly.

## 2. Scaffolding the Backend (FastAPI + SQLAlchemy)
Once the schema and relationships are normalized into an internal graph, the CLI utilizes **Jinja2 templates** (located in `sirius_cli/templates/backend/`) to render the backend:

- **Database Models (`models.py`)**: Generates SQLAlchemy declarative base classes. It intelligently maps primary keys, foreign keys, and sets up `relationship()` directives so the ORM can seamlessly join related tables.
- **Pydantic Validation (`schemas.py`)**: Generates Pydantic v2 schemas used for strict request validation and response serialization.
- **API Routing (`main.py`)**: Generates full RESTful endpoints (GET, POST, PUT, DELETE) complete with pagination, global text searching (`?search=`), and column sorting (`?order_by=`).

## 3. Database Migrations (Alembic)
Instead of forcing you to use `Base.metadata.create_all()` (which makes future updates difficult), Sirius-CLI sets up a professional database lifecycle:
- It initializes an Alembic environment inside your generated project.
- It configures `alembic/env.py` to import your generated `backend.models` as a Python package.
- It programmatically executes `alembic revision --autogenerate -m "Initial migration"` and `alembic upgrade head` under the hood. 

This ensures your generated project has a trackable migration history from day one. When you use the `sirius-init update` command, it simply generates a new migration file for the added columns/tables without destroying your existing database.

## 4. Scaffolding the Frontend (React + Vite + Tailwind)
The frontend relies on **Vite, React 18, TypeScript, and Tailwind CSS**.

- **CRUD Pages**: The engine loops over every table in your schema, generating dedicated DataGrid views and forms.
- **Dynamic Relational Dropdowns**: If a table has a foreign key (like `hotel_id`), the generated React form automatically calls the `/hotels` endpoint and renders a dropdown `<select>` allowing users to pick the relationship intuitively (instead of typing raw IDs).
- **Dashboard**: A comprehensive dashboard is generated using `recharts` to provide instant graphical insights based on your dataset sizes.

## 5. Dockerization & Execution Environment
Finally, `sirius-init` emits a `docker-compose.yml` and two `Dockerfile`s configured for production:
- **Backend Dockerfile**: Maps the root directory and runs `uvicorn backend.main:app`, strictly treating the generated backend as a Python module to ensure Alembic and relative imports work perfectly.
- **Frontend Dockerfile**: Sets up a Node environment to serve the Vite build and injects the dynamic `VITE_API_URL` environment variables so the frontend can talk to the backend instantly.
