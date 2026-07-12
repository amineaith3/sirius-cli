# Sirius-CLI — Full Audit (v0.3.2)

## What It Is

A single CLI command that transforms raw data files (CSV, Excel, SQLite, or JSON) into a fully-containerized, production-ready full-stack application — FastAPI backend, React 18 frontend, Alembic migrations, and Docker Compose. No configuration required. One command, running stack.

---

## Architecture Overview

```
sirius_cli/
├── cli.py        — Typer CLI entrypoint (sirius-init / sirius-update)
├── parser.py     — Schema inference engine (CSV, Excel, SQLite, JSON)
├── generator.py  — Jinja2 render pipeline → file output
└── templates/
    ├── backend/  — FastAPI, SQLAlchemy, Pydantic v2, Alembic, Dockerfile
    └── frontend/ — React 18, TypeScript, Vite, Tailwind CSS, CRUD pages
```

The flow is: **Data → Parser → Schema Graph → Jinja2 Generator → Files on disk → Alembic runs migrations → Done.**

---

## What's Genuinely Powerful (The Differentiators)

These are capabilities that either don't exist or are significantly weaker in comparable tools like Wagtail, Django Admin, Retool, or Appsmith:

### 1. Multi-Source Schema Inference with Zero Config
The parser can ingest 4 different input formats and produce a normalized internal schema graph from any of them. Crucially, the SQLite parser uses `PRAGMA foreign_key_list` to extract real FK constraints — not guesses — while the CSV/Excel parser has a custom irregular-plural English heuristic engine (`_pluralize`, `_singularize`, 35+ irregular mappings) to resolve `customer_id → customers` automatically. No other open-source scaffolding tool does this.

### 2. Relational Dropdowns Out of the Box
When a FK is detected, the generated React CRUD form doesn't just show a raw integer input — it fetches the parent table's records and renders a `<select>` dropdown with smart label fallback: `name → username → email → title → label → id`. This is a significant UX feature that tools like Retool charge enterprise pricing to unlock.

### 3. FK Label Resolution in Table Rows
FK columns in the data table don't show a raw integer (`customers #3`) — they resolve the loaded options state to display the human-readable label (`Alice Johnson`). The options are already fetched for the form dropdowns, so this costs zero extra API calls.

### 4. Relationship Navigation with Highlight
Clicking a FK badge in the table navigates directly to the specific parent record: `/customers?highlight=3`. The target CRUD page reads the query param, smooth-scrolls the matching row into view, and flashes it with a brand-colored glow animation for 2.5 seconds. The URL param is cleaned immediately after reading to keep browser history tidy.

### 5. `inflect` Library for FK Heuristics
The hand-rolled 60-line `_pluralize/_singularize` engine has been replaced with the `inflect` PyPI library. This correctly resolves all irregular English plurals: `company_id → companies`, `category_id → categories`, `library_id → libraries`, `person_id → people`, `index_id → indices`, and hundreds more edge cases that the old engine silently got wrong.

### 6. Alembic Migration Wiring at Scaffold Time
Unlike most generators that simply call `Base.metadata.create_all()` (a dead-end for schema evolution), Sirius-CLI initializes a proper Alembic environment, renders `env.py`, autogenerates an initial migration, and runs `alembic upgrade head` — all during scaffolding. The project has professional migration history from day one.

### 7. Full-Stack Output in a Single Pass
The generator renders ~20 files across 3 layers (backend, frontend, infra) in one execution. This includes server-side search (`?search=`), server-side column sorting (`?order_by=`), dual data export (CSV + Excel), paginated data grids, a live dashboard with Recharts, and a complete CRUD form per entity — all without any user configuration.

### 8. True Server-Side Search
The search input debounces (350ms) and fires a real API request with a `?search=` param, re-fetching from the backend. Page resets to 1 on every new search. This works across all records in the database, not just the currently loaded page.

### 9. JWT Auth Scaffold (`--auth`)
The `--auth` flag generates a complete authentication layer: `auth.py` with bcrypt hashing, JWT issuance and validation, protected FastAPI route dependencies, an admin user seed, and a full React Login screen with AuthContext. Building this from scratch takes days; Sirius-CLI generates it in seconds.

### 10. Iterative Updates (`sirius-update`)
The `update` command regenerates backend and frontend for new tables/columns added to an existing project and runs a new `alembic revision --autogenerate` to migrate the database safely — without destroying existing data or project structure.

---

## Current State (v0.3.1)

| Feature | Status |
|---|---|
| CSV, Excel, SQLite, JSON input | ✅ Working |
| FK inference (heuristic + PRAGMA) | ✅ Working |
| `inflect` library for FK plural resolution | ✅ Added in v0.2.5 |
| Full CRUD routes (GET/POST/PUT/DELETE) | ✅ Working |
| Cursor Pagination (O(log n) deep loads) | ✅ Added in v0.3.2 |
| URL-Backed Pagination UI | ✅ Added in v0.3.2 |
| Server-side search + sorting | ✅ Working + Secured allowlist in v0.2.7 |
| FK label resolution + badge navigation | ✅ Added in v0.2.5 |
| JWT Authentication (`--auth`) | ✅ Secured in v0.2.7 (Env vars + auto-gen defaults) |
| SQL Injection Prevention | ✅ Secured in v0.2.7 (`_quote_ident` in seeder) |
| Shell Injection Prevention | ✅ Secured in v0.2.7 (Removed `shell=True`) |
| CORS Configuration | ✅ Secured in v0.2.7 (Explicit allowlist) |
| Postgres + MySQL targets (`--pg`, `--mysql`) | ✅ Working |
| `sirius-update` command | ✅ Working |
| PyPI distribution via GitHub Actions | ✅ Working |
| Documentation Website | ✅ Built & Live on GH Pages (v0.2.7) |
| Community Standards (SECURITY/CONTRIBUTING/CHANGELOG) | ✅ Added in v0.2.7 |
| Form validation (HTML5 required, min, max, email) | ✅ Added in v0.3.0 |
| In-memory Live Preview (`sirius-preview`) | ✅ Working (v0.2.8) |
| Comprehensive Automated Test Suite (`pytest`) | ✅ Working (v0.2.8) |

---

## Known Weaknesses

| Issue | Severity | Impact |
|---|---|---|
| No complex regex validation | Low | Email relies on basic HTML5 `type="email"` without strict regex |

---

## Roadmap: How to Move Forward

Prioritized by value-to-effort ratio:

### Tier 2 — High-Impact Features (3-5 days each)

| # | Feature | Why |
|---|---|---|
| 4 | **Refined UI Component Library** | Decouple the React frontend into modular standard components to allow developers to build new pages faster. |

### Tier 3 — Strategic Expansion (1-2 weeks each)

| # | Feature | Why |
|---|---|---|
| 5 | **`--backend=flask\|django\|fastapi` selector** | Unlocks the Django and Flask developer markets. |
| 6 | **`--frontend=react\|vue\|svelte` selector** | Combined with backend selectors = 9 unique stack combinations from a single command. |
| 7 | **`--from-url` flag** | Accept a public CSV URL and fetch + parse on the fly. |

---

## Competitive Position

| Tool | Closest to Sirius-CLI? | Key Difference |
|---|---|---|
| **Cookiecutter** | Partial | Template-based only, no schema inference, no migrations |
| **Retool / Appsmith** | Partial | Hosted/SaaS, no code generation, no ownership of output |
| **Django Admin autogenerate** | Partial | Django-only, no frontend, no Docker |
| **Hasura** | Partial | PostgreSQL only, GraphQL only, heavy infrastructure |
| **FastAPI-crudrouter** | Partial | Backend-only, no frontend, no migrations, no inference |

**Sirius-CLI's unique position:** it is the only open-source, pip-installable tool that takes raw data files and generates an owned, customizable, containerized full-stack CRUD application with a real migration system in under 60 seconds.
