"""Format-agnostic core: DatasetReader Protocol + reader registry."""

from lakeview.core.readers import (
    DatasetReader,
    Filter,
    detect_mime,
    eq,
    is_plain_binary,
    normalize_binary_rows,
)
from lakeview.core.registry import (
    detect,
    open_dataset,
    reader_for_format,
    register,
)

__all__ = [
    "DatasetReader",
    "Filter",
    "detect",
    "detect_mime",
    "eq",
    "is_plain_binary",
    "normalize_binary_rows",
    "open_dataset",
    "reader_for_format",
    "register",
]
