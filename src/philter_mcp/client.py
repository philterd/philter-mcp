"""Async HTTP client for the Philter REST API.

Wraps the endpoints documented at
https://github.com/philterd/philter/blob/main/docs/docs/api_and_sdks/api/ :

- POST /api/explain          filter text and return a detailed explanation
- GET  /api/policies         list policy names
- GET  /api/policies/{name}  get a policy's JSON definition
- GET  /api/status           health/status of the Philter instance

Redaction goes through /api/explain (not /api/filter) so the tools can return a
report of what was redacted alongside the redacted text.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("false", "0", "no", "off")


class PhilterError(RuntimeError):
    """Raised when a request to the Philter instance fails."""


class PhilterClient:
    """Thin async wrapper around the Philter REST API.

    Configuration is read from the environment unless overridden:

    - ``PHILTER_BASE_URL``       base URL of the Philter instance (default ``http://localhost:8080``)
    - ``PHILTER_API_KEY``        sent as ``Authorization: Bearer <key>`` when set
    - ``PHILTER_DEFAULT_POLICY`` policy name used when a call omits ``policy``
    - ``PHILTER_VERIFY_SSL``     verify TLS certificates (default ``true``; set ``false``
      for Philter's default self-signed certificate)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        default_policy: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("PHILTER_BASE_URL", "http://localhost:8080")
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("PHILTER_API_KEY")
        self.verify_ssl = verify_ssl if verify_ssl is not None else _env_bool("PHILTER_VERIFY_SSL", True)
        self.default_policy = (
            default_policy if default_policy is not None else os.environ.get("PHILTER_DEFAULT_POLICY")
        )
        self.timeout = timeout
        self._transport = transport

    def _headers(self, content_type: Optional[str] = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "verify": self.verify_ssl,
        }
        if self._transport is not None:
            # Used in tests; httpx ignores `verify` when a transport is supplied.
            kwargs["transport"] = self._transport
            kwargs.pop("verify", None)
        return httpx.AsyncClient(**kwargs)

    def resolve_policy(self, policy: Optional[str]) -> Optional[str]:
        return policy or self.default_policy

    async def explain(
        self,
        text: str,
        policy: Optional[str] = None,
        context: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Filter ``text`` and return Philter's explanation JSON."""
        params: dict[str, str] = {}
        resolved = self.resolve_policy(policy)
        if resolved:
            params["p"] = resolved
        if context:
            params["c"] = context
        if document_id:
            params["d"] = document_id
        async with self._client() as client:
            try:
                resp = await client.post(
                    "/api/explain",
                    params=params,
                    content=text.encode("utf-8"),
                    headers=self._headers("text/plain"),
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise PhilterError(f"Philter explain request failed: {exc}") from exc

    async def policies(self) -> Any:
        """Return the list of policy names available on the Philter instance."""
        async with self._client() as client:
            try:
                resp = await client.get("/api/policies", headers=self._headers())
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise PhilterError(f"Philter policies request failed: {exc}") from exc

    async def policy(self, name: str) -> Any:
        """Return a single policy's JSON definition."""
        async with self._client() as client:
            try:
                resp = await client.get(f"/api/policies/{name}", headers=self._headers())
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise PhilterError(f"Philter policy request for '{name}' failed: {exc}") from exc

    async def status(self) -> Any:
        """Return the Philter instance status (JSON when available, else text)."""
        async with self._client() as client:
            try:
                resp = await client.get("/api/status", headers=self._headers())
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise PhilterError(f"Philter status request failed: {exc}") from exc
            try:
                return resp.json()
            except ValueError:
                return {"status": resp.text.strip()}
