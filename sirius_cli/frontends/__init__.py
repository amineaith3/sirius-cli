from typing import Dict, Type
from sirius_cli.frontends.base import FrontendStrategy
from sirius_cli.frontends.react import ReactFrontendStrategy

FRONTEND_STRATEGIES: Dict[str, Type[FrontendStrategy]] = {
    "react": ReactFrontendStrategy,
}


def get_frontend_strategy(name: str) -> FrontendStrategy:
    """
    Factory function to retrieve a frontend strategy by name.
    """
    if name not in FRONTEND_STRATEGIES:
        raise ValueError(
            f"Unsupported frontend engine: '{name}'. "
            f"Supported options are: {list(FRONTEND_STRATEGIES.keys())}"
        )
    return FRONTEND_STRATEGIES[name]()
