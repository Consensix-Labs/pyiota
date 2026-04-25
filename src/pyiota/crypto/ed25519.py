"""Ed25519 keypair for IOTA transaction signing.

Uses PyNaCl (libsodium) for Ed25519 operations. IOTA derives addresses from
the public key using Blake2b-256. For Ed25519 specifically (the default scheme),
the flag byte is NOT prepended before hashing -- this is an IOTA-specific
exception to maintain backward compatibility with Stardust addresses.

For other schemes (Secp256k1, Secp256r1), the flag IS prepended.

Reference: https://docs.iota.org/developer/cryptography/transaction-auth/keys-addresses
"""

from __future__ import annotations

import hashlib

import nacl.signing

from pyiota.crypto.signature import SignatureScheme, hash_intent_message, to_serialized_signature
from pyiota.exceptions import SigningError


class Ed25519Keypair:
    """Ed25519 keypair for signing IOTA transactions."""

    def __init__(self, signing_key: nacl.signing.SigningKey) -> None:
        self._signing_key = signing_key

    @classmethod
    def generate(cls) -> Ed25519Keypair:
        """Generate a new random Ed25519 keypair."""
        return cls(nacl.signing.SigningKey.generate())

    @classmethod
    def from_secret_key(cls, secret_key: bytes) -> Ed25519Keypair:
        """Import a keypair from a 32-byte Ed25519 secret key (seed).

        Args:
            secret_key: 32-byte Ed25519 private key seed.
        """
        if len(secret_key) != 32:
            raise SigningError(f"Ed25519 secret key must be 32 bytes, got {len(secret_key)}")
        return cls(nacl.signing.SigningKey(secret_key))

    @property
    def public_key(self) -> bytes:
        """Raw 32-byte Ed25519 public key."""
        return bytes(self._signing_key.verify_key)

    @property
    def secret_key(self) -> bytes:
        """Raw 32-byte Ed25519 secret key (seed)."""
        return bytes(self._signing_key)

    @property
    def address(self) -> str:
        """IOTA address derived from this keypair.

        Format: 0x-prefixed, 64-char hex string.
        Derivation: Blake2b-256(public_key_bytes)

        Note: For Ed25519 (the default scheme), the flag byte is NOT prepended
        before hashing. This differs from Secp256k1/Secp256r1 where the flag
        IS prepended. This is an IOTA-specific behavior for backward
        compatibility with Stardust addresses.
        """
        # Ed25519 exception: hash the public key directly, no flag byte prefix
        addr_bytes = hashlib.blake2b(self.public_key, digest_size=32).digest()
        return f"0x{addr_bytes.hex()}"

    def sign(self, message: bytes) -> bytes:
        """Sign a raw message, returning the 64-byte Ed25519 signature.

        Note: For transaction signing, use sign_transaction() instead -- it
        handles intent message construction and hashing.
        """
        try:
            signed = self._signing_key.sign(message)
            # PyNaCl returns signature + message; extract just the signature
            return signed.signature
        except Exception as e:
            raise SigningError(f"Ed25519 signing failed: {e}") from e

    def sign_transaction(self, tx_data_bcs: bytes) -> str:
        """Sign BCS-serialized transaction data, returning a serialized signature.

        Handles the full IOTA signing flow:
        1. Construct intent message (intent_bytes || tx_data_bcs)
        2. Hash with Blake2b-256
        3. Sign the hash with Ed25519
        4. Encode as flag || signature || public_key (base64)

        Args:
            tx_data_bcs: BCS-serialized TransactionData bytes.

        Returns:
            Base64-encoded serialized signature ready for executeTransactionBlock.
        """
        from pyiota.crypto.signature import make_intent_message

        intent_msg = make_intent_message(tx_data_bcs)
        msg_hash = hash_intent_message(intent_msg)
        signature = self.sign(msg_hash)

        return to_serialized_signature(
            scheme=SignatureScheme.ED25519,
            signature=signature,
            public_key=self.public_key,
        )

    def __repr__(self) -> str:
        return f"Ed25519Keypair(address={self.address})"