# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.4] — 2026-07-13

### Added
- `--from-url` flag added to `init`, `update`, and `preview` commands to scaffold projects directly from public CSV/JSON/Excel URLs.
- Implemented robust remote file downloader with streaming progress indicators.
- Added intelligent local caching using URL SHA-256 hashes (`~/.sirius_cache/`) to prevent redundant downloads and rate limiting.
- Graceful Content-Type header fallback detection for URLs missing explicit file extensions.

---

## [0.3.3] — 2026-07-13
- Decoupled `TableCrud.tsx` into a modular, enterprise-grade React component library:
  - `SiriusTable`: A fully dynamic data grid driven by a runtime JSON schema — zero Jinja loops in the table body.
  - `SiriusPagination`: Standalone cursor pagination footer component.
  - `SiriusBadge`: Reusable boolean TRUE/FALSE status indicator.
  - `SiriusDropdown`: Decoupled FK `<select>` resolver used in modals.
  - `SiriusError`: Unified server connectivity error component.
- Generator engine updated to scaffold `frontend/src/components/` directory.
- `TableCrud.tsx.jinja2` now emits a `tableSchema: ColumnSchema[]` JSON array via Jinja and delegates all rendering to `<SiriusTable>`.

---

## [0.3.2] — 2026-07-12

### Added
- Implemented **Cursor Pagination** for O(log N) deep-page loading in the generated FastAPI backend.
- UI Pagination state is now perfectly backed by URL `searchParams` to survive browser refreshes.

### Changed
- Extracted and deduplicated heuristic relationship inference across CSV and Excel parsers.

---

## [0.3.1] — 2026-07-11

### Fixed
- Fixed CI pipeline Black formatting discrepancy (`conftest.py` line endings).
- Synchronized `AUDIT.md` roadmap.

---

## [0.3.0] — 2026-07-11

### Added
- Dynamic form validation in generated React apps (infers `required`, `min`, `max` from data sources)

### Fixed
- Fixed Flake8 and formatting issues across the codebase
- Fixed MyPy type checking errors and configuration

---

## [0.2.8] — 2026-07-10

### Added
- `sirius-init preview` command for instant, ephemeral scaffolding without generating files
- In-memory SQLite generation combined with dynamic FastAPI and Pydantic models for live previewing
- Beautiful Vue 3 + Tailwind CSS frontend preview UI rendered directly from the CLI

---

## [0.2.7] — 2026-07-08

### 🔒 Security
- **CRITICAL**: Replaced hardcoded JWT secret key with environment variable (`SECRET_KEY`) + auto-generated fallback with startup warning
- **CRITICAL**: Eliminated all `shell=True` subprocess calls — prevents shell injection via `--message` flag
- **HIGH**: SQL injection defense-in-depth — database seeder now uses double-quoted identifiers
- **HIGH**: CORS wildcard (`*`) replaced with explicit origin allowlist
- **HIGH**: Default admin password is now auto-generated with `secrets.token_urlsafe(16)` when `--admin-pass` is omitted
- **MEDIUM**: `order_by` query parameter validated against per-table column allowlist
- **LOW**: `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` for Python 3.12+ compatibility

### Added
- `SECURITY.md` — responsible disclosure policy and security guidance for generated projects
- `CHANGELOG.md` — this file
- `CONTRIBUTING.md` — contributor guidelines
- `.env.example` auto-generated in scaffolded projects documenting required environment variables
- Production warning comments in generated `database.py` for PostgreSQL/MySQL credentials
- Prerequisites section in README (Python 3.9+, Node.js 16+, Docker)
- OS Compatibility section in README

### Changed
- Bumped `requires-python` from `>=3.8` to `>=3.9` (Python 3.8 is EOL; `inflect>=7.0` requires 3.9+)
- `project_name` now correctly passed to all Jinja2 templates (fixes `database.py` defaulting to `'app'`)
- Generator refactored to use shared context dict for template rendering

### Fixed
- README documentation now correctly references `sirius-init update` instead of `sirius-update`
- `--admin-pass` default changed from `"admin"` to auto-generated (printed to stdout)

---

## [0.2.6] — 2026-07-07

### Added
- `--version` / `-v` flag to display installed version

---

## [0.2.5] — 2026-07-07

### Added
- `inflect` library integration for FK heuristic plural resolution (replaces hand-rolled engine)
- FK badge → parent record navigation with highlight animation
- FK label resolution in table rows (zero extra API calls)

---

## [0.2.4] — 2026-07-07

### Added
- Documentation directory (`docs/`)
- `HOW_IT_WORKS.md` and `HOW_TO_USE.md` guides

### Fixed
- Backend module import fix for Docker (backend treated as Python package)

---

## [0.2.3] — 2026-07-06

### Added
- PyPI distribution via GitHub Actions (OIDC trusted publishing)
- `MANIFEST.in` for template file inclusion

---

## [0.2.0] — 2026-07-06

### Added
- JWT authentication scaffold (`--auth`, `--admin-user`, `--admin-pass`)
- PostgreSQL and MySQL target support (`--pg`, `--mysql`)
- `sirius-init update` command for iterative schema updates
- Server-side search and column sorting
- CSV and Excel dual export
- Dashboard with Recharts analytics
- Docker Compose output

---

## [0.1.0] — 2026-07-06

### Added
- Initial release
- CSV and Excel schema inference
- SQLite database introspection
- JSON configuration support
- FastAPI backend generation with SQLAlchemy models
- React 18 frontend generation with Tailwind CSS
- Alembic migration wiring at scaffold time
- FK relational dropdowns in CRUD forms
