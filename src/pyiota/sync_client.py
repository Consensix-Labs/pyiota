"""Synchronous IOTA client wrapping the async client's API.

Uses httpx.Client (sync) internally -- no asyncio.run() needed.
Provides the same method signatures as IotaClient but without async/await.

Usage:
    with SyncIotaClient(Network.TESTNET) as client:
        balance = client.get_balance(owner="0x...")
"""

from __future__ import annotations

import base64
import time
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from pyiota.crypto.ed25519 import Ed25519Keypair

from pyiota.exceptions import ObjectNotFoundError, RpcError, TransactionError
from pyiota.rpc import SyncRpcTransport
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

IOTA_COIN_TYPE = "0x2::iota::IOTA"


class SyncIotaClient:
    """Synchronous client for the IOTA Rebased JSON-RPC API.

    Mirrors IotaClient's public API without async/await. See IotaClient
    for detailed method documentation.
    """

    def __init__(self, url_or_network: str | Network, *, timeout: float = 30.0) -> None:
        if isinstance(url_or_network, Network):
            url = get_fullnode_url(url_or_network)
            self._network: Network | None = url_or_network
        else:
            url = url_or_network
            self._network = None
        self._rpc = SyncRpcTransport(url, timeout=timeout)
        self._url = url

    def __enter__(self) -> SyncIotaClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self._rpc.close()

    def close(self) -> None:
        self._rpc.close()

    # -- Node info --

    def get_rpc_api_version(self) -> str:
        result = self._rpc.request("rpc.discover")
        version: str = result.get("info", {}).get("version", "unknown")
        return version

    def get_chain_identifier(self) -> str:
        result: str = self._rpc.request("iota_getChainIdentifier")
        return result

    def get_reference_gas_price(self) -> int:
        return int(self._rpc.request("iotax_getReferenceGasPrice"))

    # -- Coin queries --

    def get_balance(self, owner: str, coin_type: str = IOTA_COIN_TYPE) -> Balance:
        result = self._rpc.request("iotax_getBalance", [owner, coin_type])
        return Balance(
            coin_type=result["coinType"],
            coin_object_count=result["coinObjectCount"],
            total_balance=result["totalBalance"],
        )

    def get_all_balances(self, owner: str) -> list[Balance]:
        result = self._rpc.request("iotax_getAllBalances", [owner])
        return [
            Balance(
                coin_type=item["coinType"],
                coin_object_count=item["coinObjectCount"],
                total_balance=item["totalBalance"],
            )
            for item in result
        ]

    def get_coins(
        self,
        owner: str,
        coin_type: str = IOTA_COIN_TYPE,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> CoinPage:
        result = self._rpc.request("iotax_getCoins", [owner, coin_type, cursor, limit])

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

    def get_coin_metadata(self, coin_type: str = IOTA_COIN_TYPE) -> CoinMetadata | None:
        result = self._rpc.request("iotax_getCoinMetadata", [coin_type])
        if result is None:
            return None
        return CoinMetadata(**result)

    def get_total_supply(self, coin_type: str = IOTA_COIN_TYPE) -> Supply:
        result = self._rpc.request("iotax_getTotalSupply", [coin_type])
        return Supply(value=result["value"])

    # -- Object queries --

    def get_object(
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
        options = {
            "showContent": show_content,
            "showBcs": show_bcs,
            "showOwner": show_owner,
            "showType": show_type,
            "showPreviousTransaction": show_previous_transaction,
            "showStorageRebate": show_storage_rebate,
            "showDisplay": show_display,
        }
        result = self._rpc.request("iota_getObject", [object_id, options])
        response = ObjectResponse(**result)
        if response.error is not None or response.data is None:
            raise ObjectNotFoundError(object_id)
        return response.data

    def multi_get_objects(
        self,
        object_ids: list[str],
        *,
        show_content: bool = False,
        show_owner: bool = False,
        show_type: bool = False,
    ) -> list[ObjectData]:
        options = {
            "showContent": show_content,
            "showOwner": show_owner,
            "showType": show_type,
        }
        result = self._rpc.request("iota_multiGetObjects", [object_ids, options])
        objects = []
        for item in result:
            resp = ObjectResponse(**item)
            if resp.data is not None:
                objects.append(resp.data)
        return objects

    def get_owned_objects(
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
        query: dict[str, Any] = {}
        if object_filter is not None:
            query["filter"] = object_filter
        query["options"] = {
            "showContent": show_content,
            "showType": show_type,
            "showOwner": show_owner,
        }
        result = self._rpc.request("iotax_getOwnedObjects", [owner, query, cursor, limit])
        return ObjectsPage(
            data=[ObjectResponse(**item) for item in result["data"]],
            next_cursor=result.get("nextCursor"),
            has_next_page=result["hasNextPage"],
        )

    # -- Transaction execution --

    def execute_transaction_block(
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
        options = {
            "showEffects": show_effects,
            "showEvents": show_events,
            "showObjectChanges": show_object_changes,
            "showBalanceChanges": show_balance_changes,
            "showRawTransaction": show_raw_transaction,
        }
        result = self._rpc.request(
            "iota_executeTransactionBlock",
            [tx_bytes, signatures, options, request_type],
        )
        response = TransactionResponse(**result)
        if response.effects and not response.effects.is_success:
            raise TransactionError(
                f"Transaction {response.digest} failed: {response.effects.error_message}"
            )
        return response

    def sign_and_execute_transaction(
        self,
        *,
        signer: Ed25519Keypair,
        tx_bytes: bytes,
        show_effects: bool = True,
        show_events: bool = False,
        show_object_changes: bool = False,
        show_balance_changes: bool = False,
    ) -> TransactionResponse:
        signature = signer.sign_transaction(tx_bytes)
        tx_b64 = base64.b64encode(tx_bytes).decode("ascii")
        return self.execute_transaction_block(
            tx_bytes=tx_b64,
            signatures=[signature],
            show_effects=show_effects,
            show_events=show_events,
            show_object_changes=show_object_changes,
            show_balance_changes=show_balance_changes,
        )

    def dev_inspect_transaction_block(
        self, sender: str, tx_bytes: str,
    ) -> DevInspectResults:
        result = self._rpc.request("iota_devInspectTransactionBlock", [sender, tx_bytes])
        return DevInspectResults(**result)

    def dry_run_transaction_block(self, tx_bytes: str) -> DryRunTransactionResponse:
        result = self._rpc.request("iota_dryRunTransactionBlock", [tx_bytes])
        return DryRunTransactionResponse(**result)

    def wait_for_transaction(
        self,
        digest: str,
        *,
        show_effects: bool = True,
        show_events: bool = False,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> TransactionResponse:
        options = {"showEffects": show_effects, "showEvents": show_events}
        elapsed = 0.0
        while elapsed < timeout:
            try:
                result = self._rpc.request("iota_getTransactionBlock", [digest, options])
                return TransactionResponse(**result)
            except RpcError:
                time.sleep(poll_interval)
                elapsed += poll_interval
        raise TimeoutError(f"Transaction {digest} not found after {timeout}s")

    # -- Event queries --

    def query_events(
        self,
        query: dict[str, Any] | EventFilter,
        *,
        cursor: dict[str, Any] | None = None,
        limit: int | None = None,
        descending_order: bool = False,
    ) -> EventPage:
        if isinstance(query, EventFilter):
            query_dict = query.to_rpc_filter()
        else:
            query_dict = query
        result = self._rpc.request(
            "iotax_queryEvents", [query_dict, cursor, limit, descending_order]
        )
        return EventPage(**result)

    # -- Faucet --

    def request_testnet_tokens(
        self,
        recipient: str,
        network: Network | None = None,
    ) -> dict[str, Any]:
        net = network or self._network
        if net is None:
            raise ValueError(
                "Cannot determine faucet URL. Provide a network parameter or "
                "construct the client with a Network enum."
            )
        faucet_url = get_faucet_url(net)
        with httpx.Client(timeout=30.0) as http:
            response = http.post(
                f"{faucet_url}/gas",
                json={"FixedAmountRequest": {"recipient": recipient}},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
