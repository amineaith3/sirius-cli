from abc import ABC, abstractmethod
from typing import Dict, Any


class FrontendStrategy(ABC):
    """
    Abstract Base Class defining the pluggable strategy pattern for frontend generation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for the frontend framework (e.g. 'react').
        """
        pass

    @abstractmethod
    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        """
        Renders templates and writes all frontend-specific source files to disk.
        """
        pass
