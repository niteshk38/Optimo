"""Base class every job source implements.

Add a new board by subclassing JobSource and returning a list[Job] from
`search`. Register it in jobagent/sources/__init__.py and it becomes available
to the CLI and the web UI automatically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job


class JobSource(ABC):
    name: str = "base"

    def __init__(self, config: dict | None = None, secrets: dict | None = None) -> None:
        self.config = config or {}
        self.secrets = secrets or {}

    @property
    def enabled(self) -> bool:
        """Sources missing credentials should report False rather than crash."""
        return bool(self.config.get("enabled", True))

    @abstractmethod
    def search(
        self,
        query: str,
        location: str | None = None,
        remote: bool | None = None,
        limit: int = 25,
    ) -> list[Job]:
        ...
