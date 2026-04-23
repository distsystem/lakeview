"""Root registry — resolves root name to RootBackend.

Storage roots:
  - ``s3`` when both $S3_BUCKET and $S3_PREFIX are set
  - ``local`` always, rooted at cwd

Namespace roots:
  - ``polaris`` when $POLARIS_ENDPOINT is set (plus $POLARIS_CLIENT_ID/_SECRET,
    $POLARIS_CATALOG). Points at a running Apache Polaris instance and exposes
    its Lance generic tables.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from lakeview.root_backends import (
    NamespaceRootBackend,
    RootBackend,
    StorageRootBackend,
)
from lakeview.root_backends.polaris_client import PolarisClient

# Auto-load repo-root .env for dev. In prod the orchestrator sets env vars
# directly so this is a no-op.
load_dotenv()


def _polaris_backend() -> NamespaceRootBackend | None:
    endpoint = os.environ.get("POLARIS_ENDPOINT")
    if not endpoint:
        return None
    catalog = os.environ.get("POLARIS_CATALOG", "lakeview_test")
    client = PolarisClient(
        endpoint=endpoint.rstrip("/"),
        client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
        client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
        catalog=catalog,
    )
    display = f"polaris://{catalog}@{endpoint}"
    return NamespaceRootBackend(
        name=os.environ.get("POLARIS_ROOT_NAME", "polaris"),
        uri=display,
        client=client,
    )


def _load_backends() -> dict[str, RootBackend]:
    backends: dict[str, RootBackend] = {}
    bucket = os.environ.get("S3_BUCKET")
    prefix = os.environ.get("S3_PREFIX")
    if bucket and prefix:
        backends["s3"] = StorageRootBackend(
            name="s3", uri=f"s3://{bucket}/{prefix}", driver="s3"
        )
    backends["local"] = StorageRootBackend(
        name="local", uri=str(Path.cwd()), driver="local"
    )
    polaris = _polaris_backend()
    if polaris is not None:
        backends[polaris.name] = polaris
    return backends


_BACKENDS = _load_backends()


def get_backend(name: str) -> RootBackend | None:
    return _BACKENDS.get(name)


def list_backends() -> list[RootBackend]:
    return list(_BACKENDS.values())
