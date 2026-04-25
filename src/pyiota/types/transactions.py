"""Transaction-related response types from the IOTA JSON-RPC API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TransactionEffects(BaseModel):
    """Effects produced by executing a transaction."""

    status: dict[str, Any]  # {"status": "success"} or {"status": "failure", "error": "..."}
    gas_used: dict[str, Any] | None = None
    created: list[dict[str, Any]] | None = None
    mutated: list[dict[str, Any]] | None = None
    deleted: list[dict[str, Any]] | None = None
    events_digest: str | None = None
    transaction_digest: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status.get("status") == "success"

    @property
    def error_message(self) -> str | None:
        if not self.is_success:
            return self.status.get("error")
        return None


class TransactionResponse(BaseModel):
    """Response from executeTransactionBlock or getTransactionBlock."""

    digest: str
    effects: TransactionEffects | None = None
    events: list[dict[str, Any]] | None = None
    object_changes: list[dict[str, Any]] | None = None
    balance_changes: list[dict[str, Any]] | None = None
    timestamp_ms: str | None = None
    errors: list[str] | None = None
    raw_transaction: str | None = None


class DryRunTransactionResponse(BaseModel):
    """Response from dryRunTransactionBlock."""

    effects: TransactionEffects
    events: list[dict[str, Any]]
    object_changes: list[dict[str, Any]]
    balance_changes: list[dict[str, Any]]
    input: dict[str, Any] | None = None


class DevInspectResults(BaseModel):
    """Response from devInspectTransactionBlock."""

    effects: TransactionEffects
    events: list[dict[str, Any]]
    results: list[dict[str, Any]] | None = None
    error: str | None = None
