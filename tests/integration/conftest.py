"""Fixtures for integration tests against IOTA testnet.

These tests require network access and a funded testnet address.
Run with: pytest tests/integration/ -m integration
"""

import pytest

from pyiota import IotaClient, SyncIotaClient, Network
from pyiota.crypto import Ed25519Keypair


@pytest.fixture
def keypair():
    """Generate a fresh keypair for each test."""
    return Ed25519Keypair.generate()


@pytest.fixture
async def client():
    """Async client connected to IOTA testnet."""
    async with IotaClient(Network.TESTNET) as c:
        yield c


@pytest.fixture
def sync_client():
    """Sync client connected to IOTA testnet."""
    with SyncIotaClient(Network.TESTNET) as c:
        yield c
