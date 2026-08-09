# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| >= 0.5.3 | ✅ Active (Secure & Hardened) |
| < 0.5.3 | ⚠️ Legacy Scaffolding |
| < 0.2.7 | ❌ Vulnerable |

## Reporting a Vulnerability

If you discover a security vulnerability in Sirius-CLI or its template generators, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. Email the maintainer directly at: **amineaithamma2004@gmail.com**
3. Include a detailed description of the vulnerability, reproduction steps, and potential impact.
4. You will receive an acknowledgment response within 48 hours.

---

## Security Considerations for Generated Projects

Sirius-CLI generates application scaffolds for **9 full-stack target combinations** (FastAPI, Flask, Django × React, Vue 3, SvelteKit). The generated code provides hardened baseline security defaults. Below are key operational security guidelines for production deployment:

### 1. Authentication & JWT Key Management (`--auth` flag)

- **JWT Secret Key**: Scaffolded backends (FastAPI, Flask, Django) read `SECRET_KEY` from environment variables. If not set, a random secret key is generated at container startup — invalidating existing active sessions on server restarts. **Always set a static `SECRET_KEY` in production `.env` files.**
- **Admin Password**: When `--admin-pass` is omitted, Sirius-CLI auto-generates a 16-byte cryptographically secure random password (`secrets.token_urlsafe(16)`) and prints it once to the terminal.
- **Token Storage**: Generated frontends store access tokens in `localStorage`. For high-security enterprise environments, consider upgrading authentication to use `HttpOnly`, `SameSite=Strict`, `Secure` cookies.
- **SvelteKit SSR Protection**: Scaffolded SvelteKit applications explicitly set `export const ssr = false;` in `src/routes/+layout.ts` to prevent server-side execution leaks of browser storage.

### 2. Database Credentials & Parameterization

- Default connection configurations read `DATABASE_URL` or individual `PG*` / `MYSQL_*` environment variables.
- All ORM queries (SQLAlchemy, Flask-SQLAlchemy, Django ORM) and seed data ingestion routines use strict positional parameter bindings (`%s` / `?`), protecting against SQL injection attacks.
- A `.env.example` file is automatically generated in every project root detailing all required environment variables.

### 3. CORS Policy & Environment Binding

- Scaffolded backends dynamically inspect the `ALLOWED_ORIGINS` environment variable (comma-separated origins). If omitted, backends fall back to local development origins (`http://localhost:5173`, `http://127.0.0.1:5173`, and `--api-url`).
- Set `ALLOWED_ORIGINS="https://yourdomain.com"` in your production environment variables to lock down cross-origin requests without editing code.

### 4. Container Hardening (Non-Root Execution)

- Backend Dockerfiles across all strategies (FastAPI, Flask, Django) are hardened to create and run under a non-privileged system user (`appuser` with UID/GID 999):
  ```dockerfile
  RUN groupadd -g 999 appuser && useradd -r -u 999 -g appuser appuser && chown -R appuser:appuser /app
  USER appuser
  ```

### 5. HTTP Security Response Headers

- Scaffolded backends automatically inject standard browser security response headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`

---

## Security Changelog

### v0.5.3 (Current Release)
- **Hardened**: Backend Dockerfiles across FastAPI, Flask, and Django strategies now create and execute under a non-privileged `appuser` system account (UID/GID 999).
- **Added**: Built-in HTTP Security Response Headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`) across all backend API templates.
- **Added**: Dynamic `ALLOWED_ORIGINS` environment variable configuration for backend CORS middleware.
- **Added**: Client-side SPA enforcement (`export const ssr = false;`) in SvelteKit templates to prevent `localStorage` token leaks during SSR rendering.
- **Added**: SHA-256 integrity verification and content validation in `--from-url` remote dataset fetching engine.

### v0.2.7
- **Fixed**: Hardcoded JWT secret key replaced with environment variable + auto-generated fallback.
- **Fixed**: Shell injection vulnerability via `--message` flag in `sirius-init update` (removed `shell=True`).
- **Fixed**: SQL injection defense-in-depth in database seeder (quoted identifiers).
- **Fixed**: CORS wildcard replaced with explicit origin allowlist.
- **Fixed**: Default admin credentials auto-generated when `--admin-pass` is omitted.
- **Fixed**: `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` (Python 3.12+ compatible).
- **Fixed**: `order_by` parameter validated against column allowlist.
