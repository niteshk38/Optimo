"""Registry of available job sources.

To add a source: create a module here, subclass JobSource, and add it to
REGISTRY keyed by its `name`. Nothing else needs to change.
"""

from .adzuna import AdzunaSource
from .base import JobSource
from .greenhouse import GreenhouseSource
from .jsearch import JSearchSource
from .remoteok import RemoteOKSource
from .websearch import WebSearchSource

REGISTRY: dict[str, type[JobSource]] = {
    AdzunaSource.name: AdzunaSource,
    RemoteOKSource.name: RemoteOKSource,
    GreenhouseSource.name: GreenhouseSource,
    JSearchSource.name: JSearchSource,
    WebSearchSource.name: WebSearchSource,
}

__all__ = [
    "JobSource", "AdzunaSource", "RemoteOKSource", "GreenhouseSource",
    "JSearchSource", "WebSearchSource", "REGISTRY",
]
