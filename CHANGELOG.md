# Changelog

All notable changes to pyiota will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - Unreleased

### Added

- `IotaClient` (async) and `SyncIotaClient` for JSON-RPC interaction
- Client-side Programmable Transaction Block building with BCS serialization
- Transaction commands: `split_coins`, `transfer_objects`, `merge_coins`, `move_call`
- Ed25519 keypair generation, import, address derivation, and transaction signing
- Coin, object, balance, and event queries
- Testnet faucet integration
- Typed Pydantic v2 response models
- Unit tests with mocked responses
- Integration tests against IOTA testnet
