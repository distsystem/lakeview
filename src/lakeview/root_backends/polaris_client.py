"""Thin Polaris REST client — just what NamespaceRootBackend needs.

Polaris exposes two relevant API surfaces:
  * Iceberg-REST for namespaces: /api/catalog/v1/{catalog}/namespaces
  * Polaris extension for Lance tables: /api/catalog/polaris/v1/{catalog}/namespaces/{ns}/generic-tables

We wrap both behind a single object so NamespaceRootBackend can stay
driver-agnostic. Tokens are cached and refreshed on 401.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

_NS_SEP = "\x1f"  # Iceberg REST multi-level namespace separator


def _ns_key(ns: list[str]) -> str:
    return _NS_SEP.join(ns)


@dataclass
class PolarisClient:
    endpoint: str
    client_id: str
    client_secret: str
    catalog: str
    _http: httpx.Client = field(
        default_factory=lambda: httpx.Client(timeout=10.0), init=False, repr=False
    )
    _token: str | None = field(default=None, init=False, repr=False)

    def _auth_headers(self, refresh: bool = False) -> dict[str, str]:
        if refresh or self._token is None:
            r = self._http.post(
                f"{self.endpoint}/api/catalog/v1/oauth/tokens",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "PRINCIPAL_ROLE:ALL",
                },
            )
            r.raise_for_status()
            self._token = r.json()["access_token"]
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        r = self._http.get(url, headers=self._auth_headers(), params=params)
        if r.status_code == 401:
            r = self._http.get(
                url, headers=self._auth_headers(refresh=True), params=params
            )
        return r

    def list_namespaces(self, parent: list[str] | None = None) -> list[list[str]]:
        """Child namespaces of ``parent`` (empty list = catalog root)."""
        params = {"parent": _ns_key(parent)} if parent else None
        r = self._get(
            f"{self.endpoint}/api/catalog/v1/{self.catalog}/namespaces", params=params
        )
        r.raise_for_status()
        return r.json().get("namespaces", [])

    def list_tables(self, namespace: list[str]) -> list[str]:
        """Lance generic tables directly under ``namespace``."""
        if not namespace:
            return []
        r = self._get(
            f"{self.endpoint}/api/catalog/polaris/v1/{self.catalog}"
            f"/namespaces/{_ns_key(namespace)}/generic-tables"
        )
        r.raise_for_status()
        return [t["name"] for t in r.json().get("identifiers", [])]

    def describe_table(self, namespace: list[str], name: str) -> dict[str, Any] | None:
        """Return the generic-table body ({name, format, base-location, ...}) or None."""
        r = self._get(
            f"{self.endpoint}/api/catalog/polaris/v1/{self.catalog}"
            f"/namespaces/{_ns_key(namespace)}/generic-tables/{name}"
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json().get("table")
