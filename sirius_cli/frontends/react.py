import os
from typing import Dict, Any
from sirius_cli.frontends.base import FrontendStrategy


class ReactFrontendStrategy(FrontendStrategy):
    """
    React frontend generation strategy.
    Generates a TypeScript + Vite + Tailwind CSS React 18 frontend.
    """

    @property
    def name(self) -> str:
        return "react"

    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        from sirius_cli.generator import get_env, render_template

        env = get_env()
        frontend_path = os.path.join(project_path, "frontend")
        schemas = context.get("schemas", {})
        auth = context.get("auth", False)

        frontend_templates = {
            "frontends/react/index.html.jinja2": "index.html",
            "frontends/react/package.json.jinja2": "package.json",
            "frontends/react/tsconfig.json.jinja2": "tsconfig.json",
            "frontends/react/vite.config.ts.jinja2": "vite.config.ts",
            "frontends/react/tailwind.config.js.jinja2": "tailwind.config.js",
            "frontends/react/postcss.config.js.jinja2": "postcss.config.js",
            "frontends/react/Dockerfile.jinja2": "Dockerfile",
            "frontends/react/.env.jinja2": ".env",
            "frontends/react/src/main.tsx.jinja2": "src/main.tsx",
            "frontends/react/src/index.css.jinja2": "src/index.css",
            "frontends/react/src/App.tsx.jinja2": "src/App.tsx",
            "frontends/react/src/Dashboard.tsx.jinja2": "src/Dashboard.tsx",
            "frontends/react/src/components/SiriusTable.tsx.jinja2": "src/components/SiriusTable.tsx",
            "frontends/react/src/components/SiriusPagination.tsx.jinja2": "src/components/SiriusPagination.tsx",
            "frontends/react/src/components/SiriusBadge.tsx.jinja2": "src/components/SiriusBadge.tsx",
            "frontends/react/src/components/SiriusDropdown.tsx.jinja2": "src/components/SiriusDropdown.tsx",
            "frontends/react/src/components/SiriusError.tsx.jinja2": "src/components/SiriusError.tsx",
            "frontends/react/src/components/SiriusToast.tsx.jinja2": "src/components/SiriusToast.tsx",
        }

        if auth:
            frontend_templates["frontends/react/src/Login.tsx.jinja2"] = (
                "src/pages/Login.tsx"
            )

        for t_path, dest_name in frontend_templates.items():
            render_template(
                env, t_path, os.path.join(frontend_path, dest_name), **context
            )

        # 4. Generate dynamic CRUD view pages for each table
        for table_name, columns in schemas.items():
            pascal_name = table_name.replace("_", " ").title().replace(" ", "")
            dest_crud_path = os.path.join(
                frontend_path, "src", "pages", f"{pascal_name}Crud.tsx"
            )
            render_template(
                env,
                "frontends/react/src/TableCrud.tsx.jinja2",
                dest_crud_path,
                table_name=table_name,
                columns=columns,
                **context,
            )
