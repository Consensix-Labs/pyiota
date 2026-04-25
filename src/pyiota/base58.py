"""Base58 encoding/decoding for IOTA Rebased digest fields.

IOTA Rebased uses Base58 (Bitcoin alphabet) for object and transaction digests.
This is a minimal implementation -- no checksum variant (Base58Check), just the
raw encoding used by Sui/IOTA for digest strings.
"""

_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE = len(_ALPHABET)
_ALPHABET_MAP = {char: index for index, char in enumerate(_ALPHABET)}


def base58_decode(encoded: str) -> bytes:
    """Decode a Base58-encoded string to bytes."""
    if not encoded:
        return b""

    # Count leading '1' characters (they represent leading zero bytes)
    leading_zeros = 0
    for ch in encoded:
        if ch == '1':
            leading_zeros += 1
        else:
            break

    # Convert from base58 to integer
    value = 0
    for ch in encoded.encode("ascii"):
        if ch not in _ALPHABET_MAP:
            raise ValueError(f"Invalid Base58 character: {chr(ch)}")
        value = value * _BASE + _ALPHABET_MAP[ch]

    # Convert integer to bytes
    if value == 0:
        result = b""
    else:
        result = value.to_bytes((value.bit_length() + 7) // 8, "big")

    return b"\x00" * leading_zeros + result


def base58_encode(data: bytes) -> str:
    """Encode bytes to a Base58 string."""
    if not data:
        return ""

    # Count leading zero bytes
    leading_zeros = 0
    for byte in data:
        if byte == 0:
            leading_zeros += 1
        else:
            break

    # Convert bytes to integer
    value = int.from_bytes(data, "big")

    # Convert integer to base58
    chars = []
    while value > 0:
        value, remainder = divmod(value, _BASE)
        chars.append(_ALPHABET[remainder:remainder + 1])
    chars.reverse()

    return "1" * leading_zeros + b"".join(chars).decode("ascii")