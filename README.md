# Sirius-CLI

A rapid prototyping CLI tool designed to take multiple CSV files, Excel spreadsheets, a SQLite database, or a JSON configuration file as inputs, automatically infer their structural schemas and relationships, and generate:
- A production-grade, container-ready **FastAPI** backend (with SQLAlchemy models, Pydantic v2 validation schemas, and automated Alembic migrations).
- A modular, responsive, multi-page **React 18 (TypeScript, Vite, Tailwind CSS)** CRUD frontend with dynamic relational selectors and a beautiful Dashboard.

📚 **[Read the Official Technical Documentation Here](https://sirius-cli.sirius-aah.com/)**

---

## Prerequisites

Before using Sirius-CLI, ensure you have the following installed:

| Requirement | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.9+ | Runtime for the CLI tool itself |
| **pip** | Latest | Installing sirius-cli from PyPI |
| **Node.js** | 16+ | Running the generated React frontend (`npm install`, `npm run dev`) |
| **Docker** *(optional)* | 20+ | Running the full stack via `docker compose up` |

---

## Key Capabilities

- **Multi-Source Ingestion & JSON Parity**: Ingest CSV, Excel (`.xlsx`), SQLite databases, or JSON configuration/arrays. Supports nested JSON flattening and multi-table relational extraction out of the box.
- **Automatic FK & Pluralization Heuristics**: Automatically extracts foreign key relationships and maps irregular English plurals (e.g. `category_id -> categories`, `person_id -> people`) using the `inflect` library engine.
- **Advanced Heuristic Form Validation**: Infer strict HTML5 inputs (`required`, `min`, `max`, `type="email"`, `type="tel"`, zip pattern validation) and native `<select>` dropdowns for low-cardinality enum columns.
- **Live Dashboard Charts**: Built-in Recharts analytics components with live date trend visualization (`created_at` grouping) and total row fallbacks.
- **Enterprise Data Grid & Cursor Pagination**: O(log n) cursor pagination, server-side search (`?search=`), server-side column sorting (`?order_by=`), and dual CSV + Excel exports.
- **Polished UX & Component Library**: Reusable React components (`SiriusTable`, `SiriusPagination`, `SiriusBadge`, `SiriusDropdown`, `SiriusError`), skeleton loading overlays, non-blocking toast notifications, and 404 deleted parent FK navigation handling.
- **Remote Data Fetching (`--from-url`)**: Fetch public datasets directly from HTTP/HTTPS URLs with local SHA-256 caching and streaming progress.
- **Relational Navigation & Highlight**: FK badges dynamically resolve human-readable parent record names and smooth-scroll + flash-highlight target records via URL params.
- **Multiple Database Targets**: Scaffold for SQLite by default, or target production-grade PostgreSQL (`--pg`) and MySQL (`--mysql`).
- **JWT Auth Scaffold (`--auth`)**: Integrated bcrypt password hashing, JWT Bearer authentication routes, protected endpoint dependencies, and a React Login screen.
- **In-Memory Instant Preview (`sirius-init preview`)**: Spin up an ephemeral backend + frontend preview directly in your browser without creating disk files.
- **Iterative Updates (`sirius-init update`)**: Safely add new tables or columns to an existing project with automated Alembic migration autogeneration.

---

## How It Works

```
 Data Source (CSV, Excel, SQLite, JSON, or --from-url)
                        │
                        ▼
           ┌─────────────────────────┐
           │ Schema Inference Engine │  (Types, Nullability, Min/Max, Phone/Zip/Enum Heuristics)
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │  Relational Graph & FK  │  (Inflect Pluralization Heuristics & PRAGMAs)
           └────────────┬────────────┘
                        │
                        ▼
           ┌─────────────────────────┐
           │ Jinja2 Code Generator   │
           └────────────┬────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
FastAPI Backend + Alembic     React 18 + Tailwind CSS
(SQLAlchemy, JWT, Pydantic)   (Sirius Component Library & Dashboard)
```

---

## Installation

Install the package directly from PyPI:
```bash
pip install sirius-cli
```

*(For local development: clone the repository and run `pip install -e .`)*

---

## Usage: Creating a New Project (`sirius-init init`)

### 1. Generating from CSVs or Excel
```bash
# From CSVs
sirius-init init store_system --csv examples/users.csv --csv examples/orders.csv --theme violet

# From Excel
sirius-init init store_system --excel examples/products.xlsx --theme amber
```

### 2. Generating from Remote URLs (`--from-url`)
Provide a public URL to a CSV, Excel, or JSON file. Sirius-CLI will stream-download it, cache it locally via SHA-256 (`~/.sirius_cache/`) to prevent rate-limits, and scaffold the app on the fly:
```bash
# Public economic dataset
sirius-init init remote_gdp --from-url https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv --theme emerald

# Remote JSON API dataset
sirius-init init remote_users --from-url https://jsonplaceholder.typicode.com/users --theme sky
```

### 3. Target Production Databases
By default, the stack uses an embedded SQLite file (`app.db`). You can target Postgres or MySQL instead:
```bash
sirius-init init billing_system --config schema.json --pg
```
*(The generated `docker-compose.yml` and `database.py` will expect a `DATABASE_URL` environment variable).*

### 4. Generating from JSON Configuration
Specify database schemas, relationships, and colors in a JSON file:
```json
{
  "project_name": "billing_system",
  "theme": "emerald",
  "entities": {
    "customers": {
      "columns": [
        { "name": "id",        "type": "Integer", "is_pk": true },
        { "name": "name",      "type": "String" },
        { "name": "email",     "type": "String" },
        { "name": "is_active", "type": "Boolean" }
      ]
    },
    "invoices": {
      "columns": [
        { "name": "id",          "type": "Integer", "is_pk": true },
        { "name": "ref_no",      "type": "String" },
        { "name": "amount",      "type": "Float" },
        { "name": "customer_id", "type": "Integer", "foreign_key": "customers.id" },
        { "name": "created_at", "type": "DateTime" }
      ]
    }
  }
}
```
Then run:
```bash
sirius-init init billing_system --config examples/billing-config.json
```

### 5. Generating with JWT Authentication
Pass the `--auth` flag to scaffold a secure project. This generates an `app_users` table, a beautiful Login screen, and protects all FastAPI routes with JWT Bearer tokens automatically.
```bash
sirius-init init secure_system --csv examples/users.csv --auth --admin-user "superadmin" --admin-pass "securepass123"
```
> **Security Note**: If you omit `--admin-pass`, a secure random password will be auto-generated and printed to your terminal. The generated project also reads `SECRET_KEY` from environment variables — be sure to set this in production.

---

## Usage: Instant Preview (`sirius-init preview`)

Want to see how your app looks before generating hundreds of files? Use the preview command to instantly spin up an in-memory database, dynamic API, and Vue 3 frontend in your browser!

```bash
sirius-init preview --csv examples/users.csv --port 8765
```

---

## Usage: Updating an Existing Project (`sirius-init update`)

If your data requirements change (e.g., adding a `reviews` table to your store), you don't need to start from scratch. Use the `update` command to merge new schemas into an existing project.

```bash
sirius-init update ./store_system --csv examples/new_reviews.csv
```

Sirius-CLI will:
1. Regenerate your SQLAlchemy models and Pydantic schemas.
2. Regenerate your frontend routing and CRUD views.
3. Automatically run `alembic revision --autogenerate` and `alembic upgrade head` to apply the database migrations seamlessly.

---

## All CLI Flags

### `sirius-init init` / `sirius-init update` / `sirius-init preview`

| Flag | Short | Default | Description |
|---|---|---|---|
| `--csv` | | | Path to a CSV file (repeatable) |
| `--excel` | | | Path to an Excel .xlsx/.xls file (repeatable) |
| `--from-url` | | | URL of a public CSV/JSON/Excel file to fetch (repeatable) |
| `--db` | | | Path to a SQLite .db file |
| `--config` | `-c` | | Path to a JSON config file |
| `--theme` | `-t` | `blue` | Frontend color theme (`blue`, `indigo`, `emerald`, `amber`, `rose`, `sky`, `violet`) |
| `--out` | `-o` | `.` | Output directory (only for `init`) |
| `--port` | `-p` | `8000` | Backend port (used in Dockerfile, docker-compose, .env) |
| `--api-url` | | `http://localhost:<port>` | Override the frontend VITE_API_URL |
| `--no-seed` | | `false` | Skip seeding the DB from source CSV/Excel files |
| `--auth` | | `false` | Generate JWT authentication logic and a React Login screen |
| `--admin-user` | | `admin` | The default admin username to seed if `--auth` is enabled |
| `--admin-pass` | | *(auto-generated)* | The admin password to seed if `--auth` is enabled |
| `--pg` | | `false` | Generate Postgres connection pool and drivers |
| `--mysql` | | `false` | Generate MySQL connection pool and drivers |

---

## Running the Scaffolded Stack

### Using Docker Compose
```bash
cd <project_name>
docker compose up --build
```

### Running Locally
1. **Start Backend**:
   ```bash
   cd <project_name>
   pip install -r backend/requirements.txt
   uvicorn backend.main:app --reload --port 8000
   ```
2. **Start Frontend** *(requires Node.js 16+)*:
   ```bash
   cd <project_name>/frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173/` in your browser.

---

## OS Compatibility

| OS | Supported Versions |
|---|---|
| **Windows** | 10, 11 |
| **macOS** | 12 (Monterey)+ |
| **Linux** | Ubuntu 20.04+, Fedora 36+, Debian 11+ |
| **WSL2** | Fully supported |

**Python**: Requires **3.9 or higher**.

---

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up your local development environment and run tests.

**Note**: All incoming Pull Requests must pass strict PEP8 formatting and linting via `black` and `flake8`, and type-checking via `mypy`. We recommend installing our pre-commit hooks.

---

## License & Commercial Use

Sirius-CLI is open-source and released under the **GNU AGPLv3 License**. 

This is a strong copyleft license that ensures the project remains free and open. By using this software, you agree that any modifications or larger works incorporating this tool that are distributed or provided as a network service (SaaS) **must also be open-sourced** under the same AGPLv3 license.

**Dual Licensing for Enterprise**
If your organization wishes to use Sirius-CLI in proprietary, closed-source software without being subject to the open-source requirements of the AGPLv3, a **Commercial License** is available for purchase. Please contact the maintainer for more details on enterprise licensing.
