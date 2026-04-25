"""Integration tests for IOTA testnet queries.

These tests hit the real IOTA testnet RPC -- they require network access
and are skipped in CI by default.

Run with: pytest tests/integration/ -m integration
"""

import pytest

from pyiota import IotaClient, Network
from pyiota.types.common import Balance, Supply


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_chain_identifier(client):
    chain_id = await client.get_chain_identifier()
    assert isinstance(chain_id, str)
    assert len(chain_id) > 0


@pytest.mark.asyncio
async def test_get_reference_gas_price(client):
    price = await client.get_reference_gas_price()
    assert isinstance(price, int)
    assert price > 0


@pytest.mark.asyncio
async def test_get_total_supply(client):
    supply = await client.get_total_supply()
    assert isinstance(supply, Supply)
    assert supply.value_int > 0


@pytest.mark.asyncio
async def test_get_balance_empty_address(client, keypair):
    """A fresh keypair with no funds should have zero balance."""
    balance = await client.get_balance(owner=keypair.address)
    assert isinstance(balance, Balance)
    assert balance.total_balance_int == 0
    assert balance.coin_object_count == 0
