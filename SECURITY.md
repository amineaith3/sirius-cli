# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| >= 0.2.7 | ✅ Active (Secure) |
| < 0.2.7 | ❌ Vulnerable |

## Reporting a Vulnerability

If you discover a security vulnerability in Sirius-CLI, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. Email the maintainer directly at: **amineaithamma2004@gmail.com**
3. Include a clear description of the vulnerability, steps to reproduce, and potential impact.
4. You will receive a response within 48 hours acknowledging receipt.

## Security Considerations for Generated Projects

Sirius-CLI generates application scaffolds. The generated code is a **starting point** and should be reviewed before production deployment. Below are the key security considerations:

### Authentication (`--auth` flag)

- **JWT Secret Key**: The generated backend reads `SECRET_KEY` from environment variables. If not set, a random key is auto-generated at startup — but this means all tokens are invalidated on server restart. **Always set `SECRET_KEY` in production.**
- **Admin Password**: If `--admin-pass` is not provided, a secure random password is auto-generated and printed to the terminal once. Save it immediately.
- **Rate Limiting**: The generated auth endpoint (`/api/auth/token`) does not include rate limiting. For production, add rate limiting middleware such as [slowapi](https://github.com/laurentS/slowapi).

### Database Credentials

- The generated `database.py` uses placeholder credentials for PostgreSQL (`postgres:postgres`) and MySQL (`root:root`). **These must be changed in production.**
- Set the `DATABASE_URL` environment variable with your real credentials.
- A `.env.example` file is generated in the project root documenting all required environment variables.

### CORS Policy

- The generated backend restricts CORS origins to `localhost:5173` (the Vite dev server) and the configured `--api-url`. Add your production domain to the `_allowed_origins` list in `main.py`.

### Data Export

- Export endpoints (`/api/<table>/export`) load all records into memory. For tables with millions of rows, implement server-side streaming or pagination.

## Security Changelog

### v0.2.7 (Current Release)
- **Fixed**: Hardcoded JWT secret key replaced with environment variable + auto-generated fallback
- **Fixed**: Shell injection vulnerability via `--message` flag in `sirius-init update` (removed `shell=True`)
- **Fixed**: SQL injection defense-in-depth in database seeder (quoted identifiers)
- **Fixed**: CORS wildcard replaced with explicit origin allowlist
- **Fixed**: Default admin credentials now auto-generated when `--admin-pass` is omitted
- **Fixed**: `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` (Python 3.12+ compatible)
- **Fixed**: `order_by` parameter now validated against column allowlist
