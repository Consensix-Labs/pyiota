"""Event-related response types from the IOTA JSON-RPC API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """A single event emitted by a transaction."""

    model_config = {"populate_by_name": True}

    id: dict[str, Any]  # {"txDigest": "...", "eventSeq": "..."}
    package_id: str = Field(alias="packageId")
    transaction_module: str = Field(alias="transactionModule")
    sender: str
    type: str  # Move event type, e.g. "0xPKG::module::EventName"
    parsed_json: dict[str, Any] | None = Field(default=None, alias="parsedJson")
    bcs: str | None = None
    timestamp_ms: str | None = Field(default=None, alias="timestampMs")


class EventPage(BaseModel):
    """Paginated list of events."""

    model_config = {"populate_by_name": True}

    data: list[Event]
    next_cursor: dict[str, Any] | None = Field(default=None, alias="nextCursor")
    has_next_page: bool = Field(alias="hasNextPage")


class EventFilter(BaseModel):
    """Filter criteria for event queries.

    Exactly one field must be set. The IOTA RPC treats each filter as a
    single variant -- to combine filters, use the "And" or "Or" wrappers
    via a raw dict passed directly to query_events().
    """

    sender: str | None = None
    transaction: str | None = None
    package: str | None = None
    move_module: dict[str, str] | None = None  # {"package": "0x...", "module": "name"}
    move_event_type: str | None = None
    move_event_field: dict[str, Any] | None = None
    time_range: dict[str, str] | None = None  # {"startTime": "...", "endTime": "..."}

    def to_rpc_filter(self) -> dict[str, Any]:
        """Convert to the dict format expected by the JSON-RPC API.

        Raises:
            ValueError: If zero or more than one field is set.
        """
        filters: list[tuple[str, Any]] = []
        if self.sender is not None:
            filters.append(("Sender", self.sender))
        if self.transaction is not None:
            filters.append(("Transaction", self.transaction))
        if self.package is not None:
            filters.append(("Package", self.package))
        if self.move_module is not None:
            filters.append(("MoveModule", self.move_module))
        if self.move_event_type is not None:
            filters.append(("MoveEventType", self.move_event_type))
        if self.move_event_field is not None:
            filters.append(("MoveEventField", self.move_event_field))
        if self.time_range is not None:
            filters.append(("TimeRange", self.time_range))

        if len(filters) == 0:
            raise ValueError("EventFilter must have exactly one field set")
        if len(filters) > 1:
            field_names = [f[0] for f in filters]
            raise ValueError(
                f"EventFilter must have exactly one field set, got {len(filters)}: "
                f"{', '.join(field_names)}. Use a raw dict with 'And'/'Or' wrappers "
                f"for composite filters."
            )

        key, value = filters[0]
        return {key: value}