# How to Use Sirius-CLI

This guide covers all the different ways you can use Sirius-CLI to generate a production-ready FastAPI and React application from various data sources.

## 1. Using CSV Files (`--csv`)
You can pass one or multiple CSV files as input. Sirius-CLI will parse each CSV, infer data types based on the content, and automatically map relationships using intelligent naming heuristics (e.g., matching a `customer_id` column to a `customers.csv` file).

```bash
sirius-init init store_system --csv users.csv --csv orders.csv
```
**Note:** By default, the CLI will automatically seed the generated database with the rows from these CSV files. If you want to skip seeding, append the `--no-seed` flag.

## 2. Using Excel Files (`--excel`)
Similar to CSVs, you can pass Excel spreadsheets (`.xlsx` or `.xls`). You can even mix them with CSV files!

```bash
sirius-init init inventory_app --excel products.xlsx --excel categories.xlsx
```

## 3. Using SQLite Databases (`--db`)
If you already have a designed SQLite database containing tables and data, you can pass the `.db` file directly. The CLI will introspect the existing schema and explicitly defined foreign key constraints.

```bash
sirius-init init transport_app --db transport.db
```

## 4. Using JSON Configurations (`--config`)
For the highest level of control, you can define your schema explicitly using a JSON configuration file. This is useful for programmatic generation or complex schemas.

```json
{
  "project_name": "billing_system",
  "theme": "emerald",
  "entities": {
    "users": {
      "columns": [
        { "name": "id", "type": "Integer", "is_pk": true },
        { "name": "email", "type": "String" }
      ]
    }
  }
}
```
```bash
sirius-init init my_project --config schema.json
```

## 5. Targeting PostgreSQL (`--pg`)
By default, Sirius-CLI generates a project using a local SQLite `app.db` file for rapid prototyping. If you are building for production, you can pass the `--pg` flag. This will generate Postgres-compatible SQLAlchemy configurations, `psycopg2` drivers, and a `docker-compose.yml` that provisions a live PostgreSQL container.

```bash
sirius-init init pg_project --csv data.csv --pg
```

## 6. Targeting MySQL (`--mysql`)
Similar to Postgres, passing `--mysql` configures the generated project to use MySQL drivers (`pymysql`) and provisions a MySQL container in your `docker-compose.yml` stack.

```bash
sirius-init init mysql_project --csv data.csv --mysql
```

## 7. Authentication (`--auth`)
When you pass the `--auth` flag, Sirius-CLI wraps your entire application in a secure JWT authentication layer:
- **Backend**: Generates an `app_users` table, password hashing logic (bcrypt), and JWT login endpoints. All generated CRUD routes are automatically protected via a `Depends(get_current_user)` dependency.
- **Frontend**: Scaffolds a beautiful Login screen and wraps the React application in an Authentication Context. Users cannot view the dashboard or interact with data without a valid bearer token.

```bash
sirius-init init secure_app --csv data.csv --auth --admin-user "superadmin" --admin-pass "securepass123"
```
*(By default, the admin credentials will be `admin` / `admin` if not specified).*

---

## Complete CLI Flags Reference

### Input Flags
- `--csv <path>`: Path to input CSV files. Can be declared multiple times.
- `--excel <path>`: Path to input Excel (.xlsx/.xls) files. Can be declared multiple times.
- `--db <path>`: Path to an input SQLite database file.
- `--config, -c <path>`: Path to a JSON configuration file.

### Customization Flags
- `--theme, -t <color>`: The primary color theme for the React frontend. Options: `blue`, `indigo`, `emerald`, `amber`, `rose`, `sky`, `violet`. *(Default: `blue`)*
- `--port, -p <int>`: The port the backend will run on locally and inside Docker. *(Default: `8000`)*
- `--api-url <url>`: Override the frontend `VITE_API_URL` environment variable. *(Default: `http://localhost:<port>`)*
- `--no-seed`: Skip automatically seeding the generated database from source CSV/Excel files.

### Database Target Flags (Exclusive)
*(If neither is provided, defaults to SQLite)*
- `--pg`: Generate Postgres connection pool and drivers.
- `--mysql`: Generate MySQL connection pool and drivers.

### Authentication Flags
- `--auth`: Generate JWT authentication logic and a React Login screen.
- `--admin-user <str>`: The default admin username to seed into the DB if `--auth` is used. *(Default: `admin`)*
- `--admin-pass <str>`: The default admin password to seed into the DB if `--auth` is used. *(Default: `admin`)*
