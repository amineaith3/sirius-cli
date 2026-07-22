from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BackendStrategy(ABC):
    """
    Abstract Base Class defining the pluggable strategy pattern for backend generation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for the backend (e.g. 'fastapi').
        """
        pass

    @abstractmethod
    def generate_files(self, project_path: str, context: Dict[str, Any]) -> None:
        """
        Renders templates and writes all backend-specific source files to disk.
        """
        pass

    @abstractmethod
    def post_init_setup(self, project_path: str, context: Dict[str, Any]) -> None:
        """
        Runs backend-specific database and environment initialization tasks (e.g., alembic init)
        during the 'init' command.
        """
        pass

    @abstractmethod
    def post_update_setup(
        self, project_path: str, context: Dict[str, Any], message: str
    ) -> None:
        """
        Runs backend-specific database and schema update tasks (e.g., alembic revision)
        during the 'update' command.
        """
        pass

    @abstractmethod
    def seed_data(self, project_path: str, seed_files: List[str]) -> None:
        """
        Seeds the target database with row data extracted from CSV, Excel, or JSON sources.
        """
        pass
