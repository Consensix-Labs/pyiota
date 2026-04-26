"""Async IOTA client for the JSON-RPC API.

IotaClient is the primary interface for interacting with an IOTA Rebased node.
Methods map to JSON-RPC endpoints and return typed Pydantic models.

Usage:
    async with IotaClient(Network.TESTNET) as client:
        balance = await client.get_balance(owner="0x...")
"""

from __future__ import annotations

import asyncio
import base64
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from pyiota.crypto.ed25519 import Ed25519Keypair

from pyiota.exceptions import ObjectNotFoundError, RpcError, TransactionError
from pyiota.rpc import AsyncRpcTransport
from pyiota.types.common import (
    Balance,
    CoinData,
    CoinMetadata,
    CoinPage,
    Network,
    Supply,
    get_faucet_url,
    get_fullnode_url,
)
from pyiota.types.events import EventFilter, EventPage
from pyiota.types.objects import ObjectData, ObjectResponse, ObjectsPage
from pyiota.types.transactions import (
    DevInspectResults,
    DryRunTransactionResponse,
    TransactionResponse,
)

# Default IOTA coin type
IOTA_COIN_TYPE = "0x2::iota::IOTA"


class IotaClient:
    """Async client for the IOTA Rebased JSON-RPC API.

    Args:
        url_or_network: Either a full JSON-RPC URL string or a Network enum value.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, url_or_network: str | Network, *, timeout: float = 30.0) -> None:
        if isinstance(url_or_network, Network):
            url = get_fullnode_url(url_or_network)
            self._network: Network | None = url_or_network
        else:
            url = url_or_network
            self._network = None
        self._rpc = AsyncRpcTransport(url, timeout=timeout)
        self._url = url

    # -- Context manager --

    async def __aenter__(self) -> IotaClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._rpc.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._rpc.close()

    # -- Node info --

    async def get_rpc_api_version(self) -> str:
        """Get the RPC API version of the connected node."""
        result = await self._rpc.request("rpc.discover")
        version: str = result.get("info", {}).get("version", "unknown")
        return version

    async def get_chain_identifier(self) -> str:
        """Get the chain identifier (genesis digest)."""
        result: str = await self._rpc.request("iota_getChainIdentifier")
        return result

    async def get_reference_gas_price(self) -> int:
        """Get the current reference gas price for transaction budgeting."""
        result = await self._rpc.request("iotax_getReferenceGasPrice")
        return int(result)

    # -- Coin queries --

    async def get_balance(
        self,
        owner: str,
        coin_type: str = IOTA_COIN_TYPE,
    ) -> Balance:
        """Get the total balance of a specific coin type for an address."""
        result = await self._rpc.request("iotax_getBalance", [owner, coin_type])
        return Balance(
            coin_type=result["coinType"],
            coin_object_count=result["coinObjectCount"],
            total_balance=result["totalBalance"],
        )

    async def get_all_balances(self, owner: str) -> list[Balance]:
        """Get balances for all coin types owned by an address."""
        result = await self._rpc.request("iotax_getAllBalances", [owner])
        return [
            Balance(
                coin_type=item["coinType"],
                coin_object_count=item["coinObjectCount"],
                total_balance=item["totalBalance"],
            )
            for item in result
        ]

    async def get_coins(
        self,
        owner: str,
        coin_type: str = IOTA_COIN_TYPE,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> CoinPage:
        """Get coins of a specific type owned by an address (paginated)."""
        params: list[Any] = [owner, coin_type, cursor, limit]
        result = await self._rpc.request("iotax_getCoins", params)
        return CoinPage(
            data=[
                CoinData(
                    coin_type=c["coinType"],
                    coin_object_id=c["coinObjectId"],
                    version=int(c["version"]),
                    digest=c["digest"],
                    balance=c["balance"],
                )
                for c in result["data"]
            ],
            next_cursor=result.get("nextCursor"),
            has_next_page=result["hasNextPage"],
        )

    async def get_coin_metadata(self, coin_type: str = IOTA_COIN_TYPE) -> CoinMetadata | None:
        """Get metadata for a coin type (name, symbol, decimals, etc.)."""
        result = await self._rpc.request("iotax_getCoinMetadata", [coin_type])
        if result is None:
            return None
        return CoinMetadata(**result)

    async def get_total_supply(self, coin_type: str = IOTA_COIN_TYPE) -> Supply:
        """Get the total supply of a coin type."""
        result = await self._rpc.request("iotax_getTotalSupply", [coin_type])
        return Supply(value=result["value"])

    # -- Object queries --

    async def get_object(
        self,
        object_id: str,
        *,
        show_content: bool = False,
        show_bcs: bool = False,
        show_owner: bool = False,
        show_type: bool = False,
        show_previous_transaction: bool = False,
        show_storage_rebate: bool = False,
        show_display: bool = False,
    ) -> ObjectData:
        """Get an object by its ID.

        Args:
            object_id: The object's on-chain ID (0x-prefixed hex).
            show_*: Control which optional fields are included in the response.

        Raises:
            ObjectNotFoundError: If the object does not exist.
        """
        options = {
            "showContent": show_content,
            "showBcs": show_bcs,
            "showOwner": show_owner,
            "showType": show_type,
            "showPreviousTransaction": show_previous_transaction,
            "showStorageRebate": show_storage_rebate,
            "showDisplay": show_display,
        }
        result = await self._rpc.request("iota_getObject", [object_id, options])
        response = ObjectResponse(**result)
        if response.error is not None or response.data is None:
            raise ObjectNotFoundError(object_id)
        return response.data

    async def multi_get_objects(
        self,
        object_ids: list[str],
        *,
        show_content: bool = False,
        show_owner: bool = False,
        show_type: bool = False,
    ) -> list[ObjectData]:
        """Get multiple objects by their IDs in a single RPC call."""
        options = {
            "showContent": show_content,
            "showOwner": show_owner,
            "showType": show_type,
        }
        result = await self._rpc.request("iota_multiGetObjects", [object_ids, options])
        objects = []
        for item in result:
            resp = ObjectResponse(**item)
            if resp.data is not None:
                objects.append(resp.data)
        return objects

    async def get_owned_objects(
        self,
        owner: str,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        show_content: bool = False,
        show_type: bool = False,
        show_owner: bool = False,
        object_filter: dict[str, Any] | None = None,
    ) -> ObjectsPage:
        """Get objects owned by an address (paginated).

        Args:
            owner: The owner's IOTA address.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of objects to return.
            object_filter: Optional RPC-level filter (e.g. {"StructType": "0x2::coin::Coin"}).
        """
        query: dict[str, Any] = {}
        if object_filter is not None:
            query["filter"] = object_filter

        options = {
            "showContent": show_content,
            "showType": show_type,
            "showOwner": show_owner,
        }
        query["options"] = options

        result = await self._rpc.request("iotax_getOwnedObjects", [owner, query, cursor, limit])
        return ObjectsPage(
            data=[ObjectResponse(**item) for item in result["data"]],
            next_cursor=result.get("nextCursor"),
            has_next_page=result["hasNextPage"],
        )

    # -- Transaction execution --

    async def execute_transaction_block(
        self,
        tx_bytes: str,
        signatures: list[str],
        *,
        show_effects: bool = True,
        show_events: bool = False,
        show_object_changes: bool = False,
        show_balance_changes: bool = False,
        show_raw_transaction: bool = False,
        request_type: str = "WaitForLocalExecution",
    ) -> TransactionResponse:
        """Submit a signed transaction for execution.

        Args:
            tx_bytes: Base64-encoded BCS-serialized TransactionData.
            signatures: List of base64-encoded serialized signatures.
            show_*: Control which optional fields are included in the response.
            request_type: "WaitForEffectsCert" or "WaitForLocalExecution".

        Returns:
            Transaction response with digest and requested details.

        Raises:
            TransactionError: If the transaction execution fails.
        """
        options = {
            "showEffects": show_effects,
            "showEvents": show_events,
            "showObjectChanges": show_object_changes,
            "showBalanceChanges": show_balance_changes,
            "showRawTransaction": show_raw_transaction,
        }
        result = await self._rpc.request(
            "iota_executeTransactionBlock",
            [tx_bytes, signatures, options, request_type],
        )
        response = TransactionResponse(**result)
        if response.effects and not response.effects.is_success:
            raise TransactionError(
                f"Transaction {response.digest} failed: {response.effects.error_message}"
            )
        return response

    async def sign_and_execute_transaction(
        self,
        *,
        signer: Ed25519Keypair,
        tx_bytes: bytes,
        show_effects: bool = True,
        show_events: bool = False,
        show_object_changes: bool = False,
        show_balance_changes: bool = False,
    ) -> TransactionResponse:
        """Sign transaction bytes and execute in one step.

        Convenience method that combines signing and execution.

        Args:
            signer: The keypair to sign with.
            tx_bytes: Raw BCS-serialized TransactionData bytes.
            show_*: Control which optional fields are included in the response.
        """
        signature = signer.sign_transaction(tx_bytes)
        tx_b64 = base64.b64encode(tx_bytes).decode("ascii")
        return await self.execute_transaction_block(
            tx_bytes=tx_b64,
            signatures=[signature],
            show_effects=show_effects,
            show_events=show_events,
            show_object_changes=show_object_changes,
            show_balance_changes=show_balance_changes,
        )

    async def dev_inspect_transaction_block(
        self,
        sender: str,
        tx_bytes: str,
    ) -> DevInspectResults:
        """Dry-run a transaction without executing it (no gas charged).

        Args:
            sender: The sender address to simulate.
            tx_bytes: Base64-encoded BCS transaction kind bytes.
        """
        result = await self._rpc.request("iota_devInspectTransactionBlock", [sender, tx_bytes])
        return DevInspectResults(**result)

    async def dry_run_transaction_block(
        self,
        tx_bytes: str,
    ) -> DryRunTransactionResponse:
        """Dry-run a complete transaction (with gas estimation).

        Args:
            tx_bytes: Base64-encoded BCS-serialized TransactionData.
        """
        result = await self._rpc.request("iota_dryRunTransactionBlock", [tx_bytes])
        return DryRunTransactionResponse(**result)

    async def wait_for_transaction(
        self,
        digest: str,
        *,
        show_effects: bool = True,
        show_events: bool = False,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> TransactionResponse:
        """Wait for a transaction to be indexed by the node.

        Polls getTransactionBlock until the transaction is found or timeout.

        Args:
            digest: The transaction digest to wait for.
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between polls in seconds.
        """
        options = {
            "showEffects": show_effects,
            "showEvents": show_events,
        }
        elapsed = 0.0
        while elapsed < timeout:
            try:
                result = await self._rpc.request("iota_getTransactionBlock", [digest, options])
                return TransactionResponse(**result)
            except RpcError:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        raise TimeoutError(f"Transaction {digest} not found after {timeout}s")

    # -- Event queries --

    async def query_events(
        self,
        query: dict[str, Any] | EventFilter,
        *,
        cursor: dict[str, Any] | None = None,
        limit: int | None = None,
        descending_order: bool = False,
    ) -> EventPage:
        """Query events matching a filter.

        Args:
            query: Event filter -- either a dict or EventFilter instance.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of events to return.
            descending_order: If True, return newest events first.
        """
        if isinstance(query, EventFilter):
            query_dict = query.to_rpc_filter()
        else:
            query_dict = query

        result = await self._rpc.request(
            "iotax_queryEvents", [query_dict, cursor, limit, descending_order]
        )
        return EventPage(**result)

    # -- Faucet --

    async def request_testnet_tokens(
        self,
        recipient: str,
        network: Network | None = None,
    ) -> dict[str, Any]:
        """Request test IOTA tokens from the faucet.

        Only works on testnet, devnet, and localnet.

        Args:
            recipient: The address to fund.
            network: Override the network for faucet URL. Defaults to the
                client's network if it was constructed from a Network enum.
        """
        net = network or self._network
        if net is None:
            raise ValueError(
                "Cannot determine faucet URL. Provide a network parameter or "
                "construct the client with a Network enum."
            )
        faucet_url = get_faucet_url(net)
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.post(
                f"{faucet_url}/gas",
                json={
                    "FixedAmountRequest": {"recipient": recipient},
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
