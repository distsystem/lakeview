"""Format layer — abstract dataset readers for different datalake formats."""

from lakeview.formats.base import DatasetReader
from lakeview.formats.lance import LanceReader

# Registered readers, in probe order. First matching marker set wins.
PROBERS: list[type] = [LanceReader]

_BY_KIND: dict[str, type] = {cls.KIND: cls for cls in PROBERS}


def detect(probe) -> type | None:
    """Return the reader class that claims `probe`, or None for a plain directory."""
    for cls in PROBERS:
        if cls.detect(probe):
            return cls
    return None


def open_dataset(path: str, kind: str) -> DatasetReader | None:
    cls = _BY_KIND.get(kind)
    return cls.open(path) if cls else None
