"""Concrete DatasetReader implementations. Importing this package registers them."""

from lakeview.core.registry import register
from lakeview.readers.lance import LanceReader

register(LanceReader)

__all__ = ["LanceReader"]
