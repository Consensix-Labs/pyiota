"""Common types shared across the SDK.

Defines fundamental IOTA types (addresses, object IDs, digests) and network
configuration. These are the building blocks used by client, transaction, and
crypto modules.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator

# IOTA addresses and object IDs are 32 bytes, represented as 0x-prefixed hex
IOTA_ADDRESS_LENGTH = 32
OBJECT_DIGEST_LENGTH = 32

# 1 IOTA = 1_000_000_000 NANOS
NANOS_PER_IOTA = 1_000_000_000


class Network(str, Enum):
    """Known IOTA network endpoints."""

    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"
    LOCALNET = "localnet"


# RPC URLs for known networks
_NETWORK_URLS: dict[Network, str] = {
    Network.MAINNET: "https://api.mainnet.iota.cafe",
    Network.TESTNET: "https://api.testnet.iota.cafe",
    Network.DEVNET: "https://api.devnet.iota.cafe",
    Network.LOCALNET: "http://127.0.0.1:9000",
}

# Faucet URLs for test networks
_FAUCET_URLS: dict[Network, str] = {
    Network.TESTNET: "https://faucet.testnet.iota.cafe",
    Network.DEVNET: "https://faucet.devnet.iota.cafe",
    Network.LOCALNET: "http://127.0.0.1:9123",
}


def get_fullnode_url(network: str | Network) -> str:
    """Get the JSON-RPC URL for a known network.

    Mirrors the TS SDK's getFullnodeUrl() helper.
    """
    if isinstance(network, str):
        network = Network(network)
    url = _NETWORK_URLS.get(network)
    if url is None:
        raise ValueError(f"Unknown network: {network}")
    return url


def get_faucet_url(network: str | Network) -> str:
    """Get the faucet URL for a test network."""
    if isinstance(network, str):
        network = Network(network)
    url = _FAUCET_URLS.get(network)
    if url is None:
        raise ValueError(f"No faucet available for network: {network}")
    return url


def normalize_iota_address(address: str) -> str:
    """Normalize an IOTA address to lowercase 0x-prefixed, zero-padded to 64 hex chars.

    Accepts addresses with or without 0x prefix, and pads short addresses.
    """
    addr = address.lower().removeprefix("0x")
    if not all(c in "0123456789abcdef" for c in addr):
        raise ValueError(f"Invalid hex in address: {address}")
    if len(addr) > IOTA_ADDRESS_LENGTH * 2:
        raise ValueError(f"Address too long: {address}")
    # Zero-pad to full length
    addr = addr.zfill(IOTA_ADDRESS_LENGTH * 2)
    return f"0x{addr}"


# -- Pydantic models for common JSON-RPC response structures --


class ObjectRef(BaseModel):
    """Reference to a specific version of an on-chain object."""

    object_id: str
    version: int
    digest: str


class GasData(BaseModel):
    """Gas configuration for a transaction."""

    payment: list[ObjectRef]
    owner: str
    price: int
    budget: int


class Balance(BaseModel):
    """Coin balance for an address."""

    coin_type: str
    coin_object_count: int
    total_balance: str  # String because it can exceed JS Number range

    @property
    def total_balance_int(self) -> int:
        return int(self.total_balance)


class CoinData(BaseModel):
    """A single coin object."""

    coin_type: str
    coin_object_id: str
    version: int
    digest: str
    balance: str

    @property
    def balance_int(self) -> int:
        return int(self.balance)


class CoinPage(BaseModel):
    """Paginated list of coins."""

    data: list[CoinData]
    next_cursor: str | None = None
    has_next_page: bool


class CoinMetadata(BaseModel):
    """Metadata about a coin type."""

    decimals: int
    name: str
    symbol: str
    description: str
    icon_url: str | None = None
    id: str | None = None


class Supply(BaseModel):
    """Total supply of a coin type."""

    value: str

    @property
    def value_int(self) -> int:
        return int(self.value)
