"""End-to-end integration test: full transaction lifecycle on IOTA testnet.

Covers the complete cycle that the quickstart example demonstrates:
1. Generate keypair
2. Request faucet tokens
3. Build a transfer transaction
4. Sign and execute
5. Verify effects and balances

Run with: pytest tests/integration/test_transfer.py -m integration
"""

import asyncio

import pytest

from pyiota import NANOS_PER_IOTA, IotaClient, Transaction
from pyiota.crypto import Ed25519Keypair

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_full_transfer_lifecycle(client: IotaClient):
    """Build, sign, execute a transfer and verify the result on testnet."""
    sender = Ed25519Keypair.generate()
    recipient = Ed25519Keypair.generate()

    # Fund the sender via faucet
    await client.request_testnet_tokens(sender.address)
    await asyncio.sleep(3)

    # Verify sender received funds
    sender_balance = await client.get_balance(owner=sender.address)
    assert sender_balance.total_balance_int > 0, "Faucet funding failed"

    # Build a transfer: send 0.1 IOTA to the recipient
    transfer_amount = NANOS_PER_IOTA // 10
    tx = Transaction()
    coin = tx.split_coins(tx.gas, [transfer_amount])
    tx.transfer_objects([coin], recipient.address)

    # Build, sign, execute
    tx_bytes = await tx.build(client=client, signer=sender)
    result = await client.sign_and_execute_transaction(
        signer=sender,
        tx_bytes=tx_bytes,
        show_effects=True,
        show_balance_changes=True,
    )

    # Verify transaction succeeded
    assert result.digest is not None
    assert result.effects is not None
    assert result.effects.is_success, f"Transaction failed: {result.effects.error_message}"

    # Verify recipient received funds
    recipient_balance = await client.get_balance(owner=recipient.address)
    assert recipient_balance.total_balance_int == transfer_amount
