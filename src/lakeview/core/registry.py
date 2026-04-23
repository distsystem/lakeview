"""Reader registry — iterate registered readers to detect / open / look up."""

from __future__ import annotations

from lakeview.core.readers import DatasetReader

_READERS: list[type[DatasetReader]] = []


def register(cls: type[DatasetReader]) -> None:
    if cls not in _READERS:
        _READERS.append(cls)


def detect(probe) -> type[DatasetReader] | None:
    for cls in _READERS:
        if cls.detect(probe):
            return cls
    return None


def open_dataset(uri: str) -> DatasetReader | None:
    for cls in _READERS:
        reader = cls.open(uri)
        if reader is not None:
            return reader
    return None


def reader_for_format(name: str) -> type[DatasetReader] | None:
    for cls in _READERS:
        if cls.KIND == name:
            return cls
    return None
