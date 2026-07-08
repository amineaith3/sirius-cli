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

- **Automatic Relationship Mapping**: Automatically extracts foreign keys from databases and resolves CSV/Excel associations using naming heuristics (linking `[table]_id` fields), navigating irregular English plurals effortlessly.
- **Auto-Seeding**: Automatically seeds the generated database with the entries inside the source CSV/Excel files during migration (if using SQLite).
- **Relational Integrity**: Generates dropdowns in the UI for foreign keys and displays badges that navigate to parent entities.
- **Enterprise Data Grid**: The generated tables feature server-side searching (`?search=`), server-side column sorting (`?order_by=`), and dual data export buttons (CSV and Excel `.xlsx`).
- **Dashboard Analytics**: A built-in Recharts dashboard showing live dataset distribution and entity insights.
- **Multiple Database Engines**: Target `SQLite` for rapid local prototyping, or generate `PostgreSQL` and `MySQL` ready projects out of the box using `--pg` and `--mysql`.
- **Iterative Updates**: Use `sirius-init update` to safely inject new tables or columns into an existing scaffolded project.

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

### 2. Target Production Databases
By default, the stack uses an embedded SQLite file (`app.db`). You can target Postgres or MySQL instead:
```bash
sirius-init init billing_system --config schema.json --pg
```
*(The generated `docker-compose.yml` and `database.py` will expect a `DATABASE_URL` environment variable).*

### 3. Generating from JSON Configuration
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

### 4. Generating with JWT Authentication
Pass the `--auth` flag to scaffold a secure project. This generates an `app_users` table, a beautiful Login screen, and protects all FastAPI routes with JWT Bearer tokens automatically.
```bash
sirius-init init secure_system --csv examples/users.csv --auth --admin-user "superadmin" --admin-pass "securepass123"
```
> **Security Note**: If you omit `--admin-pass`, a secure random password will be auto-generated and printed to your terminal. The generated project also reads `SECRET_KEY` from environment variables — be sure to set this in production.

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

### `sirius-init init` / `sirius-init update`

| Flag | Short | Default | Description |
|---|---|---|---|
| `--csv` | | | Path to a CSV file (repeatable) |
| `--excel` | | | Path to an Excel .xlsx/.xls file (repeatable) |
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

## License & Commercial Use

Sirius-CLI is open-source and released under the **GNU AGPLv3 License**. 

This is a strong copyleft license that ensures the project remains free and open. By using this software, you agree that any modifications or larger works incorporating this tool that are distributed or provided as a network service (SaaS) **must also be open-sourced** under the same AGPLv3 license.

**Dual Licensing for Enterprise**
If your organization wishes to use Sirius-CLI in proprietary, closed-source software without being subject to the open-source requirements of the AGPLv3, a **Commercial License** is available for purchase. Please contact the maintainer for more details on enterprise licensing.
