"""Low-level JSON-RPC 2.0 transport over HTTP.

Handles request construction, response parsing, and error extraction.
This module has no IOTA-specific knowledge -- it works with any JSON-RPC endpoint.
"""

from __future__ import annotations

import itertools
from typing import Any

import httpx

from pyiota.exceptions import RpcError

# Monotonically increasing request IDs within a process
_request_id_counter = itertools.count(1)


def _build_request(method: str, params: list[Any]) -> dict[str, Any]:
    """Construct a JSON-RPC 2.0 request envelope."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": next(_request_id_counter),
    }


def _extract_result(response_json: dict[str, Any]) -> Any:
    """Extract the result from a JSON-RPC response, raising RpcError on failure."""
    if "error" in response_json:
        err = response_json["error"]
        raise RpcError(
            code=err.get("code", -1),
            message=err.get("message", "Unknown RPC error"),
            data=err.get("data"),
        )
    return response_json.get("result")


class AsyncRpcTransport:
    """Async JSON-RPC transport using httpx.AsyncClient."""

    def __init__(self, url: str, *, timeout: float = 30.0) -> None:
        self._url = url
        self._client = httpx.AsyncClient(
            base_url=url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def request(self, method: str, params: list[Any] | None = None) -> Any:
        """Send a JSON-RPC request and return the result.

        Args:
            method: The RPC method name (e.g. "iota_getObject").
            params: Positional parameters for the method.

        Returns:
            The "result" field from the JSON-RPC response.

        Raises:
            RpcError: If the RPC endpoint returns an error response.
            httpx.HTTPError: On network/transport failures.
        """
        body = _build_request(method, params or [])
        response = await self._client.post("", json=body)
        response.raise_for_status()
        return _extract_result(response.json())

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncRpcTransport:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class SyncRpcTransport:
    """Sync JSON-RPC transport using httpx.Client."""

    def __init__(self, url: str, *, timeout: float = 30.0) -> None:
        self._url = url
        self._client = httpx.Client(
            base_url=url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    def request(self, method: str, params: list[Any] | None = None) -> Any:
        """Send a JSON-RPC request and return the result."""
        body = _build_request(method, params or [])
        response = self._client.post("", json=body)
        response.raise_for_status()
        return _extract_result(response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SyncRpcTransport:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
