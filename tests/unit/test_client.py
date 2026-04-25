"""Tests for IotaClient with mocked JSON-RPC responses."""

import json

import pytest
import httpx

from pyiota import IotaClient, SyncIotaClient, Network
from pyiota.exceptions import RpcError, ObjectNotFoundError, TransactionError
from pyiota.types.common import Balance, CoinPage
from pyiota.types.objects import ObjectData
from pyiota.types.events import EventPage
from pyiota.types.transactions import TransactionResponse

from tests.unit.conftest import (
    MOCK_BALANCE_RESPONSE,
    MOCK_COINS_RESPONSE,
    MOCK_OBJECT_RESPONSE,
    MOCK_OBJECT_NOT_FOUND_RESPONSE,
    MOCK_GAS_PRICE_RESPONSE,
    MOCK_EXECUTE_TX_RESPONSE,
    MOCK_EXECUTE_TX_FAILURE_RESPONSE,
    MOCK_EVENTS_RESPONSE,
    MOCK_RPC_ERROR_RESPONSE,
)


# -- Async client tests --

class TestIotaClientAsync:
    @pytest.fixture
    def mock_client(self, httpx_mock):
        """Create an IotaClient pointing at a mock URL."""
        return IotaClient("https://mock.iota.test")

    @pytest.mark.asyncio
    async def test_get_balance(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_BALANCE_RESPONSE)

        balance = await mock_client.get_balance(owner="0x" + "cc" * 32)

        assert isinstance(balance, Balance)
        assert balance.coin_type == "0x2::iota::IOTA"
        assert balance.coin_object_count == 3
        assert balance.total_balance_int == 5_000_000_000

    @pytest.mark.asyncio
    async def test_get_balance_sends_correct_rpc_method(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_BALANCE_RESPONSE)
        await mock_client.get_balance(owner="0xtest")

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["method"] == "iotax_getBalance"
        assert body["params"][0] == "0xtest"

    @pytest.mark.asyncio
    async def test_get_coins(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_COINS_RESPONSE)

        coins = await mock_client.get_coins(owner="0xtest")

        assert isinstance(coins, CoinPage)
        assert len(coins.data) == 2
        assert coins.data[0].balance_int == 3_000_000_000
        assert coins.has_next_page is False

    @pytest.mark.asyncio
    async def test_get_object(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_OBJECT_RESPONSE)

        obj = await mock_client.get_object("0x" + "a1" * 32)

        assert isinstance(obj, ObjectData)
        assert obj.object_id == "0x" + "a1" * 32
        assert obj.version == 42

    @pytest.mark.asyncio
    async def test_get_object_not_found(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_OBJECT_NOT_FOUND_RESPONSE)

        with pytest.raises(ObjectNotFoundError):
            await mock_client.get_object("0x" + "ff" * 32)

    @pytest.mark.asyncio
    async def test_get_reference_gas_price(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_GAS_PRICE_RESPONSE)

        price = await mock_client.get_reference_gas_price()
        assert price == 1000

    @pytest.mark.asyncio
    async def test_execute_transaction_success(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_EXECUTE_TX_RESPONSE)

        result = await mock_client.execute_transaction_block(
            tx_bytes="AAAA",
            signatures=["sig1"],
        )

        assert isinstance(result, TransactionResponse)
        assert result.digest == "TX_DIGEST_ABC123"
        assert result.effects.is_success

    @pytest.mark.asyncio
    async def test_execute_transaction_failure_raises(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_EXECUTE_TX_FAILURE_RESPONSE)

        with pytest.raises(TransactionError, match="InsufficientGas"):
            await mock_client.execute_transaction_block(
                tx_bytes="AAAA",
                signatures=["sig1"],
            )

    @pytest.mark.asyncio
    async def test_query_events(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_EVENTS_RESPONSE)

        events = await mock_client.query_events({"Sender": "0xtest"})

        assert isinstance(events, EventPage)
        assert len(events.data) == 1
        assert events.data[0].transaction_module == "my_module"
        assert events.data[0].parsed_json["value"] == 42

    @pytest.mark.asyncio
    async def test_rpc_error_raises(self, httpx_mock, mock_client):
        httpx_mock.add_response(json=MOCK_RPC_ERROR_RESPONSE)

        with pytest.raises(RpcError, match="Invalid params"):
            await mock_client.get_balance(owner="0xtest")

    @pytest.mark.asyncio
    async def test_network_enum_constructor(self):
        client = IotaClient(Network.TESTNET)
        assert "testnet" in client._url
        assert client._network == Network.TESTNET
        await client.close()


# -- Sync client tests --

class TestSyncIotaClient:
    @pytest.fixture
    def mock_sync_client(self, httpx_mock):
        return SyncIotaClient("https://mock.iota.test")

    def test_get_balance(self, httpx_mock, mock_sync_client):
        httpx_mock.add_response(json=MOCK_BALANCE_RESPONSE)

        balance = mock_sync_client.get_balance(owner="0xtest")

        assert isinstance(balance, Balance)
        assert balance.total_balance_int == 5_000_000_000

    def test_get_object(self, httpx_mock, mock_sync_client):
        httpx_mock.add_response(json=MOCK_OBJECT_RESPONSE)

        obj = mock_sync_client.get_object("0x" + "a1" * 32)
        assert isinstance(obj, ObjectData)

    def test_get_object_not_found(self, httpx_mock, mock_sync_client):
        httpx_mock.add_response(json=MOCK_OBJECT_NOT_FOUND_RESPONSE)

        with pytest.raises(ObjectNotFoundError):
            mock_sync_client.get_object("0x" + "ff" * 32)

    def test_rpc_error(self, httpx_mock, mock_sync_client):
        httpx_mock.add_response(json=MOCK_RPC_ERROR_RESPONSE)

        with pytest.raises(RpcError):
            mock_sync_client.get_balance(owner="0xtest")
