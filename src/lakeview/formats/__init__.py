"""Format layer — abstract dataset readers for different datalake formats."""

from lakeview.formats.base import DatasetReader
from lakeview.formats.lance import LanceReader


def open_dataset(path: str, kind: str) -> DatasetReader | None:
    if kind == "lance":
        return LanceReader.open(path)
    return None
