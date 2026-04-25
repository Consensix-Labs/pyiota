"""pyiota quickstart -- create a keypair, request testnet tokens, and transfer IOTA.

This example demonstrates the core pyiota workflow:
1. Generate an Ed25519 keypair
2. Request test IOTA from the faucet
3. Check the balance
4. Transfer IOTA to another address

Usage:
    python examples/quickstart.py
"""

import asyncio

from pyiota import IotaClient, Network, Transaction, NANOS_PER_IOTA
from pyiota.crypto import Ed25519Keypair


async def main():
    # Generate two keypairs -- a sender and a recipient
    sender = Ed25519Keypair.generate()
    recipient = Ed25519Keypair.generate()

    print(f"Sender:    {sender.address}")
    print(f"Recipient: {recipient.address}")
    print()

    async with IotaClient(Network.TESTNET) as client:
        # Request test tokens from the faucet
        print("Requesting testnet tokens...")
        await client.request_testnet_tokens(sender.address)

        # Wait a moment for the faucet transaction to be processed
        await asyncio.sleep(3)

        # Check the sender's balance
        balance = await client.get_balance(owner=sender.address)
        print(f"Sender balance: {balance.total_balance_int / NANOS_PER_IOTA} IOTA")
        print()

        # Build a transfer transaction: send 0.1 IOTA to the recipient
        transfer_amount = NANOS_PER_IOTA // 10  # 0.1 IOTA in nanos
        tx = Transaction()
        coin = tx.split_coins(tx.gas, [transfer_amount])
        tx.transfer_objects([coin], recipient.address)

        # Build, sign, and execute
        tx_bytes = await tx.build(client=client, signer=sender)
        result = await client.sign_and_execute_transaction(
            signer=sender,
            tx_bytes=tx_bytes,
            show_effects=True,
            show_balance_changes=True,
        )

        print(f"Transaction digest: {result.digest}")
        print(f"Status: {result.effects.status}")
        print()

        # Check both balances after the transfer
        sender_balance = await client.get_balance(owner=sender.address)
        recipient_balance = await client.get_balance(owner=recipient.address)

        print(f"Sender balance:    {sender_balance.total_balance_int / NANOS_PER_IOTA} IOTA")
        print(f"Recipient balance: {recipient_balance.total_balance_int / NANOS_PER_IOTA} IOTA")


if __name__ == "__main__":
    asyncio.run(main())
