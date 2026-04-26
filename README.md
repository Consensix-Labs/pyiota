# pyiota

[![CI](https://github.com/Consensix-Labs/pyiota/actions/workflows/ci.yml/badge.svg)](https://github.com/Consensix-Labs/pyiota/actions/workflows/ci.yml)

Python SDK for [IOTA Rebased](https://docs.iota.org/) -- the Move-based Layer 1 blockchain.

pyiota provides a developer-friendly Python interface for interacting with IOTA Rebased nodes via JSON-RPC. It supports client-side transaction building with BCS serialization, Ed25519 signing, and typed responses.

**Status:** Alpha (v0.1.0) -- API may change before 1.0.

## Features

- Async-first client with sync wrapper (powered by httpx)
- Client-side Programmable Transaction Block building with BCS serialization
- Ed25519 keypair generation, import, and transaction signing
- Typed responses using Pydantic v2 models
- Coin, object, balance, and event queries
- Testnet faucet integration
- API aligned with the [IOTA TypeScript SDK](https://docs.iota.org/developer/ts-sdk) conventions

## Installation

```bash
pip install pyiota
```

Optional extras:

```bash
pip install pyiota[secp256k1]   # Secp256k1 signing support
pip install pyiota[mnemonic]    # BIP-39 mnemonic key derivation
```

Requires Python 3.12+.

## Quick Start

```python
import asyncio
from pyiota import IotaClient, Network, Transaction, NANOS_PER_IOTA
from pyiota.crypto import Ed25519Keypair

async def main():
    sender = Ed25519Keypair.generate()
    recipient = Ed25519Keypair.generate()

    async with IotaClient(Network.TESTNET) as client:
        # Fund the sender from the testnet faucet
        await client.request_testnet_tokens(sender.address)
        await asyncio.sleep(3)

        # Check balance
        balance = await client.get_balance(owner=sender.address)
        print(f"Balance: {balance.total_balance_int / NANOS_PER_IOTA} IOTA")

        # Transfer 0.1 IOTA
        tx = Transaction()
        coin = tx.split_coins(tx.gas, [NANOS_PER_IOTA // 10])
        tx.transfer_objects([coin], recipient.address)

        tx_bytes = await tx.build(client=client, signer=sender)
        result = await client.sign_and_execute_transaction(
            signer=sender, tx_bytes=tx_bytes
        )
        print(f"Transaction: {result.digest}")

asyncio.run(main())
```

### Sync Usage

```python
from pyiota import SyncIotaClient, Network, Transaction
from pyiota.crypto import Ed25519Keypair

keypair = Ed25519Keypair.generate()

with SyncIotaClient(Network.TESTNET) as client:
    balance = client.get_balance(owner=keypair.address)
    print(f"Balance: {balance.total_balance_int}")
```

### Move Call

```python
tx = Transaction()
tx.move_call(
    target="0xPACKAGE::module::function",
    arguments=[tx.pure_string("hello"), tx.object("0xOBJECT_ID")],
    type_arguments=["0x2::coin::Coin<0x2::iota::IOTA>"],
)
```

## API Reference

### Client Methods

| Method | Description |
|---|---|
| `get_balance(owner, coin_type?)` | Get coin balance for an address |
| `get_all_balances(owner)` | Get all coin type balances |
| `get_coins(owner, coin_type?, cursor?, limit?)` | Get coin objects (paginated) |
| `get_object(object_id, show_*?)` | Get an object by ID |
| `get_owned_objects(owner, ...)` | Get objects owned by address |
| `multi_get_objects(object_ids, ...)` | Batch get objects |
| `execute_transaction_block(tx_bytes, signatures, ...)` | Submit signed transaction |
| `sign_and_execute_transaction(signer, tx_bytes, ...)` | Sign and submit |
| `dev_inspect_transaction_block(sender, tx_bytes)` | Dry-run (no gas) |
| `dry_run_transaction_block(tx_bytes)` | Dry-run (with gas estimation) |
| `query_events(query, ...)` | Query emitted events |
| `wait_for_transaction(digest, ...)` | Poll until indexed |
| `get_reference_gas_price()` | Current gas price |
| `get_chain_identifier()` | Chain genesis digest |
| `request_testnet_tokens(recipient)` | Faucet (test networks only) |

### Transaction Builder

| Method | Description |
|---|---|
| `tx.split_coins(coin, amounts)` | Split a coin into new coins |
| `tx.transfer_objects(objects, recipient)` | Transfer objects to address |
| `tx.merge_coins(destination, sources)` | Merge coins together |
| `tx.move_call(target, arguments?, type_arguments?)` | Call a Move function |
| `tx.pure(value, type_hint?)` | Create a pure input value |
| `tx.object(object_id, ...)` | Create an object reference input |
| `tx.build(client, signer?)` | Build to BCS bytes (async) |
| `tx.build_sync(client, signer?)` | Build to BCS bytes (sync) |

## Development

```bash
git clone https://github.com/Consensix-Labs/pyiota.git
cd pyiota
pip install -e ".[dev]"

# Run unit tests
pytest tests/unit/

# Run integration tests (requires network)
pytest tests/integration/ -m integration

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/pyiota/
```

### Docker

```bash
# Unit tests
docker compose run --rm test-unit

# Integration tests (hits IOTA testnet)
docker compose run --rm test-integration
```

## License

MIT -- see [LICENSE](LICENSE).

## Links

- [IOTA Documentation](https://docs.iota.org/)
- [IOTA TypeScript SDK](https://docs.iota.org/developer/ts-sdk)
- [Consensix Labs](https://consensixlabs.com)
- [GitHub](https://github.com/Consensix-Labs/pyiota)
