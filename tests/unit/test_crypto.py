"""Tests for cryptographic operations -- key generation, address derivation, signing."""

import base64
import hashlib

import pytest

from pyiota.crypto.ed25519 import Ed25519Keypair
from pyiota.crypto.signature import (
    SignatureScheme,
    hash_intent_message,
    make_intent_message,
    to_serialized_signature,
)
from pyiota.exceptions import SigningError


class TestEd25519Keypair:
    def test_generate_produces_valid_keypair(self):
        kp = Ed25519Keypair.generate()
        assert len(kp.public_key) == 32
        assert len(kp.secret_key) == 32
        assert kp.public_key != kp.secret_key

    def test_generate_produces_unique_keys(self):
        kp1 = Ed25519Keypair.generate()
        kp2 = Ed25519Keypair.generate()
        assert kp1.public_key != kp2.public_key

    def test_from_secret_key_deterministic(self):
        """Same secret key always produces the same keypair."""
        seed = bytes(range(32))
        kp1 = Ed25519Keypair.from_secret_key(seed)
        kp2 = Ed25519Keypair.from_secret_key(seed)
        assert kp1.public_key == kp2.public_key
        assert kp1.address == kp2.address

    def test_from_secret_key_wrong_length(self):
        with pytest.raises(SigningError):
            Ed25519Keypair.from_secret_key(b"too short")

    def test_address_format(self):
        """Address should be 0x-prefixed, 66 chars total (0x + 64 hex)."""
        kp = Ed25519Keypair.generate()
        assert kp.address.startswith("0x")
        assert len(kp.address) == 66
        # Verify it's valid hex
        int(kp.address, 16)

    def test_address_derivation(self):
        """Verify address = Blake2b-256(public_key) for Ed25519 (no flag prefix).

        IOTA exception: Ed25519 is the default scheme, so the flag byte 0x00
        is NOT prepended before hashing. Other schemes (Secp256k1, etc.) do
        prepend their flag byte.
        """
        seed = bytes(range(32))
        kp = Ed25519Keypair.from_secret_key(seed)

        # Ed25519: hash the public key directly, no flag byte prefix
        expected_hash = hashlib.blake2b(kp.public_key, digest_size=32).digest()
        expected_address = f"0x{expected_hash.hex()}"

        assert kp.address == expected_address

    def test_sign_produces_64_bytes(self):
        kp = Ed25519Keypair.generate()
        signature = kp.sign(b"test message")
        assert len(signature) == 64

    def test_sign_deterministic(self):
        """Same key + same message = same signature (Ed25519 is deterministic)."""
        seed = bytes(range(32))
        kp = Ed25519Keypair.from_secret_key(seed)
        sig1 = kp.sign(b"test message")
        sig2 = kp.sign(b"test message")
        assert sig1 == sig2

    def test_sign_different_messages(self):
        kp = Ed25519Keypair.generate()
        sig1 = kp.sign(b"message 1")
        sig2 = kp.sign(b"message 2")
        assert sig1 != sig2

    def test_sign_transaction_returns_base64(self):
        kp = Ed25519Keypair.generate()
        fake_tx_bytes = b"\x00" * 64
        result = kp.sign_transaction(fake_tx_bytes)

        # Should be valid base64
        decoded = base64.b64decode(result)
        # Format: flag(1) + signature(64) + pubkey(32) = 97 bytes
        assert len(decoded) == 97
        assert decoded[0] == SignatureScheme.ED25519

    def test_sign_transaction_embeds_correct_public_key(self):
        """The serialized signature must contain our public key so the node
        can derive the correct address from it."""
        kp = Ed25519Keypair.generate()
        result = kp.sign_transaction(b"\x00" * 64)
        decoded = base64.b64decode(result)

        embedded_pk = decoded[65:97]
        assert embedded_pk == kp.public_key

        # Address derived from embedded PK must match keypair address
        # Ed25519: no flag prefix
        embedded_addr = hashlib.blake2b(embedded_pk, digest_size=32).digest()
        assert f"0x{embedded_addr.hex()}" == kp.address

    def test_repr(self):
        kp = Ed25519Keypair.generate()
        r = repr(kp)
        assert "Ed25519Keypair" in r
        assert kp.address in r


class TestSignature:
    def test_make_intent_message(self):
        tx_data = b"\x01\x02\x03"
        intent_msg = make_intent_message(tx_data)
        # Intent prefix is 3 bytes [0, 0, 0]
        assert intent_msg == b"\x00\x00\x00\x01\x02\x03"
        assert len(intent_msg) == 6

    def test_hash_intent_message(self):
        intent_msg = b"\x00\x00\x00\x01\x02\x03"
        msg_hash = hash_intent_message(intent_msg)
        # Blake2b-256 produces 32 bytes
        assert len(msg_hash) == 32

    def test_hash_deterministic(self):
        msg = b"test"
        h1 = hash_intent_message(msg)
        h2 = hash_intent_message(msg)
        assert h1 == h2

    def test_to_serialized_signature(self):
        sig = bytes(range(64))
        pubkey = bytes(range(32))
        result = to_serialized_signature(SignatureScheme.ED25519, sig, pubkey)

        decoded = base64.b64decode(result)
        assert decoded[0] == 0x00  # Ed25519 flag
        assert decoded[1:65] == sig
        assert decoded[65:97] == pubkey
