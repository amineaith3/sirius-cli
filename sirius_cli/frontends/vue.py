import os
from typing import Dict, Any
from sirius_cli.frontends.base import FrontendStrategy


class VueFrontendStrategy(FrontendStrategy):
    """
    Vue frontend generation strategy.
    Generates a TypeScript + Vite + Tailwind CSS + Pinia Vue 3 frontend.
    """

    @property
    def name(self) -> str:
        return "vue"

    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        from sirius_cli.generator import get_env, render_template

        env = get_env()
        frontend_path = os.path.join(project_path, "frontend")
        schemas = context.get("schemas", {})
        auth = context.get("auth", False)

        frontend_templates = {
            "frontends/vue/index.html.jinja2": "index.html",
            "frontends/vue/package.json.jinja2": "package.json",
            "frontends/vue/tsconfig.json.jinja2": "tsconfig.json",
            "frontends/vue/vite.config.ts.jinja2": "vite.config.ts",
            "frontends/vue/tailwind.config.js.jinja2": "tailwind.config.js",
            "frontends/vue/postcss.config.js.jinja2": "postcss.config.js",
            "frontends/vue/Dockerfile.jinja2": "Dockerfile",
            "frontends/vue/.env.jinja2": ".env",
            "frontends/vue/src/main.ts.jinja2": "src/main.ts",
            "frontends/vue/src/index.css.jinja2": "src/index.css",
            "frontends/vue/src/App.vue.jinja2": "src/App.vue",
            "frontends/vue/src/Dashboard.vue.jinja2": "src/Dashboard.vue",
            "frontends/vue/src/stores/auth.ts.jinja2": "src/stores/auth.ts",
            "frontends/vue/src/components/SiriusTable.vue.jinja2": "src/components/SiriusTable.vue",
            "frontends/vue/src/components/SiriusPagination.vue.jinja2": "src/components/SiriusPagination.vue",
            "frontends/vue/src/components/SiriusBadge.vue.jinja2": "src/components/SiriusBadge.vue",
            "frontends/vue/src/components/SiriusDropdown.vue.jinja2": "src/components/SiriusDropdown.vue",
            "frontends/vue/src/components/SiriusError.vue.jinja2": "src/components/SiriusError.vue",
            "frontends/vue/src/components/SiriusToast.vue.jinja2": "src/components/SiriusToast.vue",
        }

        if auth:
            frontend_templates["frontends/vue/src/pages/Login.vue.jinja2"] = (
                "src/pages/Login.vue"
            )

        for t_path, dest_name in frontend_templates.items():
            render_template(
                env, t_path, os.path.join(frontend_path, dest_name), **context
            )

        # Generate dynamic CRUD view pages for each table
        for table_name, columns in schemas.items():
            pascal_name = table_name.replace("_", " ").title().replace(" ", "")
            dest_crud_path = os.path.join(
                frontend_path, "src", "pages", f"{pascal_name}Crud.vue"
            )
            render_template(
                env,
                "frontends/vue/src/pages/TableCrud.vue.jinja2",
                dest_crud_path,
                table_name=table_name,
                columns=columns,
                **context,
            )
