"""Tests for Pydantic type models and common utilities."""

import pytest

from pyiota.types.common import (
    Balance,
    CoinData,
    CoinPage,
    Network,
    Supply,
    get_faucet_url,
    get_fullnode_url,
    normalize_iota_address,
)
from pyiota.types.events import EventFilter
from pyiota.types.transactions import TransactionEffects


class TestNetwork:
    def test_get_fullnode_url_testnet(self):
        url = get_fullnode_url("testnet")
        assert "testnet" in url
        assert url.startswith("https://")

    def test_get_fullnode_url_enum(self):
        url = get_fullnode_url(Network.DEVNET)
        assert "devnet" in url

    def test_get_fullnode_url_localnet(self):
        url = get_fullnode_url(Network.LOCALNET)
        assert "127.0.0.1" in url

    def test_get_fullnode_url_invalid(self):
        with pytest.raises(ValueError):
            get_fullnode_url("nonexistent")

    def test_get_faucet_url(self):
        url = get_faucet_url("testnet")
        assert "faucet" in url

    def test_get_faucet_url_mainnet_raises(self):
        with pytest.raises(ValueError):
            get_faucet_url("mainnet")


class TestNormalizeAddress:
    def test_with_prefix(self):
        addr = "0x" + "ab" * 32
        assert normalize_iota_address(addr) == addr

    def test_without_prefix(self):
        addr = "ab" * 32
        assert normalize_iota_address(addr) == "0x" + addr

    def test_short_address_padded(self):
        result = normalize_iota_address("0x1")
        assert result == "0x" + "0" * 63 + "1"
        assert len(result) == 66

    def test_uppercase_normalized(self):
        result = normalize_iota_address("0xABCD")
        assert result == "0x" + "0" * 60 + "abcd"

    def test_invalid_hex(self):
        with pytest.raises(ValueError, match="Invalid hex"):
            normalize_iota_address("0xGGGG")

    def test_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            normalize_iota_address("0x" + "ab" * 33)


class TestBalance:
    def test_total_balance_int(self):
        b = Balance(
            coin_type="0x2::iota::IOTA",
            coin_object_count=1,
            total_balance="5000000000",
        )
        assert b.total_balance_int == 5_000_000_000


class TestCoinData:
    def test_balance_int(self):
        c = CoinData(
            coin_type="0x2::iota::IOTA",
            coin_object_id="0x1234",
            version=1,
            digest="abc",
            balance="1000000000",
        )
        assert c.balance_int == 1_000_000_000


class TestSupply:
    def test_value_int(self):
        s = Supply(value="4600000000000000000")
        assert s.value_int == 4_600_000_000_000_000_000


class TestTransactionEffects:
    def test_is_success(self):
        effects = TransactionEffects(status={"status": "success"})
        assert effects.is_success is True
        assert effects.error_message is None

    def test_is_failure(self):
        effects = TransactionEffects(
            status={"status": "failure", "error": "InsufficientGas"}
        )
        assert effects.is_success is False
        assert effects.error_message == "InsufficientGas"


class TestEventFilter:
    def test_sender_filter(self):
        f = EventFilter(sender="0xabc")
        assert f.to_rpc_filter() == {"Sender": "0xabc"}

    def test_package_filter(self):
        f = EventFilter(package="0xpkg")
        assert f.to_rpc_filter() == {"Package": "0xpkg"}

    def test_move_event_type_filter(self):
        f = EventFilter(move_event_type="0xpkg::module::Event")
        assert f.to_rpc_filter() == {"MoveEventType": "0xpkg::module::Event"}

    def test_empty_filter_raises(self):
        f = EventFilter()
        with pytest.raises(ValueError, match="exactly one field"):
            f.to_rpc_filter()

    def test_multiple_fields_raises(self):
        f = EventFilter(sender="0xabc", package="0xpkg")
        with pytest.raises(ValueError, match="exactly one field"):
            f.to_rpc_filter()