"""Object-related response types from the IOTA JSON-RPC API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ObjectOwner(BaseModel):
    """Object ownership information. One of: AddressOwner, ObjectOwner, Shared, Immutable."""

    # The RPC returns ownership as a tagged union. We keep it flexible here
    # and provide helper properties for common cases.
    address_owner: str | None = None
    object_owner: str | None = None
    shared: dict[str, Any] | None = None
    immutable: bool | None = None

    @property
    def is_address_owned(self) -> bool:
        return self.address_owner is not None

    @property
    def is_shared(self) -> bool:
        return self.shared is not None

    @property
    def is_immutable(self) -> bool:
        return self.immutable is True


class ObjectContent(BaseModel):
    """Parsed Move object content."""

    data_type: str  # "moveObject" or "package"
    type: str | None = None  # Move type string, e.g. "0x2::coin::Coin<0x2::iota::IOTA>"
    has_public_transfer: bool | None = None
    fields: dict[str, Any] | None = None
    bcs_bytes: str | None = None


class ObjectData(BaseModel):
    """Full object data as returned by getObject."""

    model_config = {"populate_by_name": True}

    object_id: str = Field(alias="objectId")
    version: int = Field(default=0)
    digest: str = Field(default="")
    type: str | None = None
    owner: ObjectOwner | dict[str, Any] | None = None
    content: ObjectContent | None = None
    bcs: dict[str, Any] | None = None
    previous_transaction: str | None = Field(default=None, alias="previousTransaction")
    storage_rebate: int | None = Field(default=None, alias="storageRebate")
    display: dict[str, Any] | None = None


class ObjectResponse(BaseModel):
    """Response from getObject RPC call."""

    data: ObjectData | None = None
    error: dict[str, Any] | None = None


class ObjectsPage(BaseModel):
    """Paginated list of objects from getOwnedObjects."""

    data: list[ObjectResponse]
    next_cursor: str | None = None
    has_next_page: bool
