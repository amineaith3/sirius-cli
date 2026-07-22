from typing import Dict, Type
from sirius_cli.backends.base import BackendStrategy
from sirius_cli.backends.fastapi import FastAPIBackendStrategy

BACKEND_STRATEGIES: Dict[str, Type[BackendStrategy]] = {
    "fastapi": FastAPIBackendStrategy,
}


def get_backend_strategy(name: str) -> BackendStrategy:
    """
    Factory function to retrieve a backend strategy by name.
    """
    if name not in BACKEND_STRATEGIES:
        raise ValueError(
            f"Unsupported backend engine: '{name}'. "
            f"Supported options are: {list(BACKEND_STRATEGIES.keys())}"
        )
    return BACKEND_STRATEGIES[name]()
