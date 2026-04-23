"""Root backends — browseable data sources behind /api/roots."""

from lakeview.root_backends.base import RootBackend
from lakeview.root_backends.namespace import NamespaceRootBackend
from lakeview.root_backends.storage import StorageRootBackend

__all__ = ["NamespaceRootBackend", "RootBackend", "StorageRootBackend"]
