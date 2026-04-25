"""Shared fixtures and helpers for unit tests."""

import pytest


# Known test vectors for address derivation.
# Generated from a deterministic Ed25519 seed for reproducibility.
TEST_SECRET_KEY = bytes(range(32))  # 0x00..0x1f -- deterministic seed for testing

# Sample JSON-RPC responses for mocking
MOCK_BALANCE_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "coinType": "0x2::iota::IOTA",
        "coinObjectCount": 3,
        "totalBalance": "5000000000",
    },
}

MOCK_COINS_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "data": [
            {
                "coinType": "0x2::iota::IOTA",
                "coinObjectId": "0x" + "a1" * 32,
                "version": "42",
                "digest": "ABC123==",
                "balance": "3000000000",
            },
            {
                "coinType": "0x2::iota::IOTA",
                "coinObjectId": "0x" + "b2" * 32,
                "version": "15",
                "digest": "DEF456==",
                "balance": "2000000000",
            },
        ],
        "nextCursor": None,
        "hasNextPage": False,
    },
}

MOCK_OBJECT_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "data": {
            "objectId": "0x" + "a1" * 32,
            "version": 42,
            "digest": "ABC123==",
            "type": "0x2::coin::Coin<0x2::iota::IOTA>",
            "owner": {"AddressOwner": "0x" + "cc" * 32},
        },
        "error": None,
    },
}

MOCK_OBJECT_NOT_FOUND_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "data": None,
        "error": {
            "code": "notExists",
            "object_id": "0x" + "ff" * 32,
        },
    },
}

MOCK_GAS_PRICE_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": "1000",
}

MOCK_CHAIN_ID_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": "4c78adac",
}

MOCK_EXECUTE_TX_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "digest": "TX_DIGEST_ABC123",
        "effects": {
            "status": {"status": "success"},
            "gasUsed": {
                "computationCost": "1000000",
                "storageCost": "2000000",
                "storageRebate": "500000",
            },
        },
    },
}

MOCK_EXECUTE_TX_FAILURE_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "digest": "TX_DIGEST_FAIL",
        "effects": {
            "status": {
                "status": "failure",
                "error": "InsufficientGas",
            },
        },
    },
}

MOCK_EVENTS_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "data": [
            {
                "id": {"txDigest": "TX123", "eventSeq": "0"},
                "packageId": "0x" + "aa" * 32,
                "transactionModule": "my_module",
                "sender": "0x" + "cc" * 32,
                "type": "0x" + "aa" * 32 + "::my_module::MyEvent",
                "parsedJson": {"value": 42},
            }
        ],
        "nextCursor": None,
        "hasNextPage": False,
    },
}

MOCK_RPC_ERROR_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32602,
        "message": "Invalid params",
    },
}