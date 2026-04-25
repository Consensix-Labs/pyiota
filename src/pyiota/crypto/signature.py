"""Signature scheme flags and intent signing for IOTA transactions.

IOTA signs a Blake2b-256 hash of an "intent message" which is:
    intent_bytes (3 bytes) || bcs_serialized_transaction_data

The serialized signature format sent to the RPC is:
    flag_byte || signature_bytes || public_key_bytes

Reference: https://docs.iota.org/developer/iota-101/transactions/sign-and-send-transactions
"""

from __future__ import annotations

import base64
import hashlib
from enum import IntEnum


class SignatureScheme(IntEnum):
    """Signature scheme flag bytes used in IOTA addresses and serialized signatures."""

    ED25519 = 0x00
    SECP256K1 = 0x01
    SECP256R1 = 0x02
    MULTISIG = 0x03


# Intent bytes: [scope, version, app_id]
# scope=0 (TransactionData), version=0 (V0), app_id=0 (Iota)
TRANSACTION_DATA_INTENT = bytes([0, 0, 0])


def make_intent_message(tx_data_bcs: bytes) -> bytes:
    """Construct the intent message that gets hashed before signing.

    Args:
        tx_data_bcs: BCS-serialized TransactionData bytes.

    Returns:
        The intent message: intent_bytes || tx_data_bcs
    """
    return TRANSACTION_DATA_INTENT + tx_data_bcs


def hash_intent_message(intent_message: bytes) -> bytes:
    """Blake2b-256 hash of the intent message. This is what gets signed."""
    return hashlib.blake2b(intent_message, digest_size=32).digest()


def to_serialized_signature(
    scheme: SignatureScheme,
    signature: bytes,
    public_key: bytes,
) -> str:
    """Encode a signature in IOTA's wire format (base64).

    Format: flag_byte || signature_bytes || public_key_bytes
    Then base64-encode the whole thing.

    Args:
        scheme: The signature scheme used.
        signature: Raw signature bytes (64 bytes for Ed25519).
        public_key: Raw public key bytes (32 bytes for Ed25519).

    Returns:
        Base64-encoded serialized signature string.
    """
    raw = bytes([scheme.value]) + signature + public_key
    return base64.b64encode(raw).decode("ascii")
