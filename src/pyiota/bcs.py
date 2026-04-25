"""Binary Canonical Serialization (BCS) engine.

BCS is a deterministic binary format used by Move-based blockchains (Sui, Aptos,
IOTA Rebased) for serializing transaction data. It encodes values sequentially
with no field names -- the schema is known at both ends.

This module provides the low-level encoding/decoding primitives. IOTA-specific
type layouts are defined in bcs_types.py.

Reference: https://github.com/zefchain/bcs
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

from pyiota.exceptions import SerializationError


class BcsWriter:
    """Accumulates BCS-encoded bytes for a single value or structure."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def finish(self) -> bytes:
        """Return the accumulated bytes."""
        return bytes(self._buf)

    # -- Integers (little-endian, fixed-width) --

    def write_u8(self, value: int) -> BcsWriter:
        if not 0 <= value <= 0xFF:
            raise SerializationError(f"u8 out of range: {value}")
        self._buf.append(value)
        return self

    def write_u16(self, value: int) -> BcsWriter:
        if not 0 <= value <= 0xFFFF:
            raise SerializationError(f"u16 out of range: {value}")
        self._buf.extend(struct.pack("<H", value))
        return self

    def write_u32(self, value: int) -> BcsWriter:
        if not 0 <= value <= 0xFFFF_FFFF:
            raise SerializationError(f"u32 out of range: {value}")
        self._buf.extend(struct.pack("<I", value))
        return self

    def write_u64(self, value: int) -> BcsWriter:
        if not 0 <= value <= 0xFFFF_FFFF_FFFF_FFFF:
            raise SerializationError(f"u64 out of range: {value}")
        self._buf.extend(struct.pack("<Q", value))
        return self

    def write_u128(self, value: int) -> BcsWriter:
        if not 0 <= value <= (1 << 128) - 1:
            raise SerializationError(f"u128 out of range: {value}")
        self._buf.extend(value.to_bytes(16, "little"))
        return self

    def write_u256(self, value: int) -> BcsWriter:
        if not 0 <= value <= (1 << 256) - 1:
            raise SerializationError(f"u256 out of range: {value}")
        self._buf.extend(value.to_bytes(32, "little"))
        return self

    # -- Boolean --

    def write_bool(self, value: bool) -> BcsWriter:
        self._buf.append(1 if value else 0)
        return self

    # -- ULEB128 --

    def write_uleb128(self, value: int) -> BcsWriter:
        """Encode an unsigned integer as ULEB128 (variable-length)."""
        if value < 0:
            raise SerializationError(f"ULEB128 cannot encode negative: {value}")
        while value >= 0x80:
            self._buf.append((value & 0x7F) | 0x80)
            value >>= 7
        self._buf.append(value)
        return self

    # -- Bytes and strings --

    def write_bytes(self, data: bytes | bytearray) -> BcsWriter:
        """Length-prefixed byte sequence (ULEB128 length + raw bytes)."""
        self.write_uleb128(len(data))
        self._buf.extend(data)
        return self

    def write_str(self, value: str) -> BcsWriter:
        """UTF-8 string, length-prefixed like bytes."""
        return self.write_bytes(value.encode("utf-8"))

    # -- Fixed-length bytes (no length prefix) --

    def write_fixed_bytes(self, data: bytes | bytearray) -> BcsWriter:
        """Raw bytes with no length prefix (caller knows the expected size)."""
        self._buf.extend(data)
        return self

    # -- Sequences --

    def write_vector_length(self, length: int) -> BcsWriter:
        """Write the ULEB128 length prefix for a vector. Elements are written separately."""
        return self.write_uleb128(length)

    # -- Enums --

    def write_variant_index(self, index: int) -> BcsWriter:
        """Write the ULEB128 variant index for an enum. Variant data follows."""
        return self.write_uleb128(index)

    # -- Optional --

    def write_option_none(self) -> BcsWriter:
        """Encode None (0x00)."""
        self._buf.append(0)
        return self

    def write_option_some(self) -> BcsWriter:
        """Write the Some marker (0x01). The value is written separately after this."""
        self._buf.append(1)
        return self


class BcsReader:
    """Reads BCS-encoded bytes sequentially."""

    def __init__(self, data: bytes | bytearray) -> None:
        self._data = bytes(data)
        self._pos = 0

    @property
    def remaining(self) -> int:
        return len(self._data) - self._pos

    def _check(self, n: int) -> None:
        if self._pos + n > len(self._data):
            raise SerializationError(
                f"BCS read overflow: need {n} bytes, have {self.remaining}"
            )

    # -- Integers --

    def read_u8(self) -> int:
        self._check(1)
        val = self._data[self._pos]
        self._pos += 1
        return val

    def read_u16(self) -> int:
        self._check(2)
        val: int = struct.unpack_from("<H", self._data, self._pos)[0]
        self._pos += 2
        return val

    def read_u32(self) -> int:
        self._check(4)
        val: int = struct.unpack_from("<I", self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_u64(self) -> int:
        self._check(8)
        val: int = struct.unpack_from("<Q", self._data, self._pos)[0]
        self._pos += 8
        return val

    def read_u128(self) -> int:
        self._check(16)
        val = int.from_bytes(self._data[self._pos : self._pos + 16], "little")
        self._pos += 16
        return val

    def read_u256(self) -> int:
        self._check(32)
        val = int.from_bytes(self._data[self._pos : self._pos + 32], "little")
        self._pos += 32
        return val

    # -- Boolean --

    def read_bool(self) -> bool:
        val = self.read_u8()
        if val not in (0, 1):
            raise SerializationError(f"Invalid bool byte: {val}")
        return val == 1

    # -- ULEB128 --

    def read_uleb128(self) -> int:
        result = 0
        shift = 0
        while True:
            self._check(1)
            byte = self._data[self._pos]
            self._pos += 1
            result |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
            shift += 7
            if shift > 63:
                raise SerializationError("ULEB128 overflow")
        return result

    # -- Bytes and strings --

    def read_bytes(self) -> bytes:
        length = self.read_uleb128()
        self._check(length)
        data = self._data[self._pos : self._pos + length]
        self._pos += length
        return data

    def read_str(self) -> str:
        return self.read_bytes().decode("utf-8")

    # -- Fixed-length bytes --

    def read_fixed_bytes(self, length: int) -> bytes:
        self._check(length)
        data = self._data[self._pos : self._pos + length]
        self._pos += length
        return data

    # -- Sequences --

    def read_vector_length(self) -> int:
        return self.read_uleb128()

    # -- Enums --

    def read_variant_index(self) -> int:
        return self.read_uleb128()

    # -- Optional --

    def read_option_is_some(self) -> bool:
        """Read the option tag. Returns True if Some (caller reads the value next)."""
        tag = self.read_u8()
        if tag not in (0, 1):
            raise SerializationError(f"Invalid option tag: {tag}")
        return tag == 1


# -- Convenience functions for common serialization patterns --


def bcs_serialize_vector(items: Sequence[bytes]) -> bytes:
    """Serialize a vector of pre-serialized items."""
    writer = BcsWriter()
    writer.write_vector_length(len(items))
    for item in items:
        writer.write_fixed_bytes(item)
    return writer.finish()
