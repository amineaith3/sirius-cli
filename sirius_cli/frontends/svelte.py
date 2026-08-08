import os
from typing import Dict, Any
from sirius_cli.frontends.base import FrontendStrategy


class SvelteFrontendStrategy(FrontendStrategy):
    """
    SvelteKit frontend generation strategy.
    Generates a TypeScript + SvelteKit + Tailwind CSS frontend.
    """

    @property
    def name(self) -> str:
        return "svelte"

    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        from sirius_cli.generator import get_env, render_template

        env = get_env()
        frontend_path = os.path.join(project_path, "frontend")
        schemas = context.get("schemas", {})
        auth = context.get("auth", False)

        frontend_templates = {
            "frontends/svelte/package.json.jinja2": "package.json",
            "frontends/svelte/tsconfig.json.jinja2": "tsconfig.json",
            "frontends/svelte/svelte.config.js.jinja2": "svelte.config.js",
            "frontends/svelte/vite.config.ts.jinja2": "vite.config.ts",
            "frontends/svelte/tailwind.config.js.jinja2": "tailwind.config.js",
            "frontends/svelte/postcss.config.js.jinja2": "postcss.config.js",
            "frontends/svelte/Dockerfile.jinja2": "Dockerfile",
            "frontends/svelte/.env.jinja2": ".env",
            "frontends/svelte/src/app.html.jinja2": "src/app.html",
            "frontends/svelte/src/app.d.ts.jinja2": "src/app.d.ts",
            "frontends/svelte/src/index.css.jinja2": "src/index.css",
            "frontends/svelte/src/routes/+layout.svelte.jinja2": "src/routes/+layout.svelte",
            "frontends/svelte/src/routes/+layout.ts.jinja2": "src/routes/+layout.ts",
            "frontends/svelte/src/routes/+page.svelte.jinja2": "src/routes/+page.svelte",
            "frontends/svelte/src/routes/api/health/+server.ts.jinja2": "src/routes/api/health/+server.ts",
            "frontends/svelte/src/lib/stores/auth.ts.jinja2": "src/lib/stores/auth.ts",
            "frontends/svelte/src/lib/components/SiriusTable.svelte.jinja2": "src/lib/components/SiriusTable.svelte",
            "frontends/svelte/src/lib/components/SiriusPagination.svelte.jinja2": "src/lib/components/SiriusPagination.svelte",
            "frontends/svelte/src/lib/components/SiriusBadge.svelte.jinja2": "src/lib/components/SiriusBadge.svelte",
            "frontends/svelte/src/lib/components/SiriusDropdown.svelte.jinja2": "src/lib/components/SiriusDropdown.svelte",
            "frontends/svelte/src/lib/components/SiriusError.svelte.jinja2": "src/lib/components/SiriusError.svelte",
            "frontends/svelte/src/lib/components/SiriusToast.svelte.jinja2": "src/lib/components/SiriusToast.svelte",
        }

        if auth:
            frontend_templates[
                "frontends/svelte/src/routes/login/+page.svelte.jinja2"
            ] = "src/routes/login/+page.svelte"

        for t_path, dest_name in frontend_templates.items():
            render_template(
                env, t_path, os.path.join(frontend_path, dest_name), **context
            )

        # Generate dynamic CRUD view pages for each table
        for table_name, columns in schemas.items():
            # For SvelteKit routing, we generate: src/routes/{table_name}/+page.svelte
            dest_crud_path = os.path.join(
                frontend_path, "src", "routes", table_name, "+page.svelte"
            )
            render_template(
                env,
                "frontends/svelte/src/routes/TableCrud.svelte.jinja2",
                dest_crud_path,
                table_name=table_name,
                columns=columns,
                **context,
            )
