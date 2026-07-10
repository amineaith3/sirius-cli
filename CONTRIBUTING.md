# Contributing to Sirius-CLI

Thank you for your interest in contributing to Sirius-CLI! This document provides guidelines and information to help you get started.

## Getting Started

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/amineaith3/sirius-cli.git
   cd sirius-cli
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e .[dev]
   ```

4. **Verify the installation:**
   ```bash
   sirius-init --version
   ```

### Project Structure

```
sirius_cli/
├── cli.py          — Typer CLI entrypoint (sirius-init init / update)
├── parser.py       — Schema inference engine (CSV, Excel, SQLite, JSON)
├── generator.py    — Jinja2 render pipeline → file output
└── templates/
    ├── backend/    — FastAPI, SQLAlchemy, Pydantic v2, Alembic, Dockerfile
    └── frontend/   — React 18, TypeScript, Vite, Tailwind CSS, CRUD pages
```

## How to Contribute

### Reporting Bugs

- Use the [GitHub Issues](https://github.com/amineaith3/sirius-cli/issues) page
- Include your OS, Python version, and the exact command you ran
- Include the full error traceback if applicable
- For **security vulnerabilities**, do NOT open a public issue — see [SECURITY.md](SECURITY.md)

### Suggesting Features

- Open an issue with the `[Feature Request]` prefix
- Describe the use case and why it would be valuable
- If you have a proposed implementation, outline it

### Submitting Code Changes

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** — follow the existing code style

3. **Test your changes** by running the automated test suite and manually scaffolding a test project:
   ```bash
   pytest tests/ -v
   sirius-init init test_project --csv examples/users.csv --csv examples/orders.csv
   ```

4. **Submit a Pull Request** with a clear description of:
   - What you changed and why
   - How to test the change
   - Any breaking changes

### Code Style

- Python files: Follow PEP 8 conventions
- Jinja2 templates: Match the existing template formatting style
- Use type hints where applicable
- Preserve existing comments and docstrings

### Areas Where Help Is Welcome

- **Test suite expansion**: We recently added a `pytest` suite for the parser, generator, and CLI. Adding more test cases for edge cases or edge-case CSVs is always welcome!
- **Template improvements**: Better error messages, accessibility, responsive design in generated frontends
- **Documentation**: Improving the docs, adding examples, writing tutorials
- **New input parsers**: Support for YAML, TOML, or remote database connections

## Code of Conduct

- Be respectful and constructive in all interactions
- Focus on the technical merit of contributions
- Help newcomers get started

## License

By contributing to Sirius-CLI, you agree that your contributions will be licensed under the **GNU AGPLv3 License**.
