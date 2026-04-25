"""Tests for the BCS serialization engine."""

import pytest

from pyiota.bcs import BcsReader, BcsWriter, bcs_serialize_vector
from pyiota.exceptions import SerializationError


class TestBcsWriter:
    """Test BCS encoding for all primitive types."""

    def test_u8(self):
        assert BcsWriter().write_u8(0).finish() == b"\x00"
        assert BcsWriter().write_u8(255).finish() == b"\xff"

    def test_u8_out_of_range(self):
        with pytest.raises(SerializationError):
            BcsWriter().write_u8(256)
        with pytest.raises(SerializationError):
            BcsWriter().write_u8(-1)

    def test_u16(self):
        assert BcsWriter().write_u16(0).finish() == b"\x00\x00"
        # 0x0100 = 256, little-endian
        assert BcsWriter().write_u16(256).finish() == b"\x00\x01"
        assert BcsWriter().write_u16(0xFFFF).finish() == b"\xff\xff"

    def test_u32(self):
        assert BcsWriter().write_u32(1).finish() == b"\x01\x00\x00\x00"

    def test_u64(self):
        assert BcsWriter().write_u64(1).finish() == b"\x01" + b"\x00" * 7
        # 1 billion (NANOS_PER_IOTA)
        result = BcsWriter().write_u64(1_000_000_000).finish()
        assert len(result) == 8
        assert int.from_bytes(result, "little") == 1_000_000_000

    def test_u128(self):
        result = BcsWriter().write_u128(1).finish()
        assert len(result) == 16
        assert result[0] == 1
        assert all(b == 0 for b in result[1:])

    def test_u256(self):
        result = BcsWriter().write_u256(1).finish()
        assert len(result) == 32
        assert result[0] == 1

    def test_bool(self):
        assert BcsWriter().write_bool(True).finish() == b"\x01"
        assert BcsWriter().write_bool(False).finish() == b"\x00"

    def test_uleb128_small(self):
        # Values < 128 encode as a single byte
        assert BcsWriter().write_uleb128(0).finish() == b"\x00"
        assert BcsWriter().write_uleb128(1).finish() == b"\x01"
        assert BcsWriter().write_uleb128(127).finish() == b"\x7f"

    def test_uleb128_multibyte(self):
        # 128 = 0x80 -> encodes as [0x80, 0x01]
        assert BcsWriter().write_uleb128(128).finish() == b"\x80\x01"
        # 300 = 0x012C -> encodes as [0xAC, 0x02]
        assert BcsWriter().write_uleb128(300).finish() == b"\xac\x02"

    def test_uleb128_negative_raises(self):
        with pytest.raises(SerializationError):
            BcsWriter().write_uleb128(-1)

    def test_bytes(self):
        # Length prefix + data
        result = BcsWriter().write_bytes(b"hello").finish()
        assert result == b"\x05hello"

    def test_str(self):
        result = BcsWriter().write_str("abc").finish()
        assert result == b"\x03abc"

    def test_fixed_bytes(self):
        # No length prefix
        result = BcsWriter().write_fixed_bytes(b"\xaa\xbb").finish()
        assert result == b"\xaa\xbb"

    def test_option_none(self):
        assert BcsWriter().write_option_none().finish() == b"\x00"

    def test_option_some(self):
        w = BcsWriter()
        w.write_option_some()
        w.write_u8(42)
        assert w.finish() == b"\x01\x2a"

    def test_chaining(self):
        """Writer methods return self for chaining."""
        result = (
            BcsWriter()
            .write_u8(1)
            .write_u16(2)
            .write_bool(True)
            .finish()
        )
        assert result == b"\x01\x02\x00\x01"


class TestBcsReader:
    """Test BCS decoding for all primitive types."""

    def test_u8(self):
        assert BcsReader(b"\x00").read_u8() == 0
        assert BcsReader(b"\xff").read_u8() == 255

    def test_u16(self):
        assert BcsReader(b"\x00\x01").read_u16() == 256

    def test_u32(self):
        assert BcsReader(b"\x01\x00\x00\x00").read_u32() == 1

    def test_u64(self):
        data = (1_000_000_000).to_bytes(8, "little")
        assert BcsReader(data).read_u64() == 1_000_000_000

    def test_u128(self):
        data = (1).to_bytes(16, "little")
        assert BcsReader(data).read_u128() == 1

    def test_u256(self):
        data = (1).to_bytes(32, "little")
        assert BcsReader(data).read_u256() == 1

    def test_bool(self):
        assert BcsReader(b"\x01").read_bool() is True
        assert BcsReader(b"\x00").read_bool() is False

    def test_bool_invalid(self):
        with pytest.raises(SerializationError):
            BcsReader(b"\x02").read_bool()

    def test_uleb128(self):
        assert BcsReader(b"\x00").read_uleb128() == 0
        assert BcsReader(b"\x7f").read_uleb128() == 127
        assert BcsReader(b"\x80\x01").read_uleb128() == 128
        assert BcsReader(b"\xac\x02").read_uleb128() == 300

    def test_bytes(self):
        assert BcsReader(b"\x05hello").read_bytes() == b"hello"

    def test_str(self):
        assert BcsReader(b"\x03abc").read_str() == "abc"

    def test_fixed_bytes(self):
        assert BcsReader(b"\xaa\xbb\xcc").read_fixed_bytes(2) == b"\xaa\xbb"

    def test_option_none(self):
        assert BcsReader(b"\x00").read_option_is_some() is False

    def test_option_some(self):
        reader = BcsReader(b"\x01\x2a")
        assert reader.read_option_is_some() is True
        assert reader.read_u8() == 42

    def test_read_overflow(self):
        with pytest.raises(SerializationError, match="overflow"):
            BcsReader(b"\x01").read_u16()

    def test_remaining(self):
        reader = BcsReader(b"\x01\x02\x03")
        assert reader.remaining == 3
        reader.read_u8()
        assert reader.remaining == 2


class TestBcsRoundTrip:
    """Verify that encoding then decoding produces the original value."""

    @pytest.mark.parametrize("value", [0, 1, 127, 128, 255, 1000, 16383, 65535])
    def test_uleb128_round_trip(self, value):
        encoded = BcsWriter().write_uleb128(value).finish()
        decoded = BcsReader(encoded).read_uleb128()
        assert decoded == value

    @pytest.mark.parametrize("value", [0, 1, 2**64 - 1])
    def test_u64_round_trip(self, value):
        encoded = BcsWriter().write_u64(value).finish()
        decoded = BcsReader(encoded).read_u64()
        assert decoded == value

    def test_bytes_round_trip(self):
        data = b"hello world" * 10
        encoded = BcsWriter().write_bytes(data).finish()
        decoded = BcsReader(encoded).read_bytes()
        assert decoded == data

    def test_str_round_trip(self):
        text = "IOTA Rebased"
        encoded = BcsWriter().write_str(text).finish()
        decoded = BcsReader(encoded).read_str()
        assert decoded == text


class TestSerializeVector:
    def test_empty(self):
        result = bcs_serialize_vector([])
        assert result == b"\x00"  # ULEB128 length 0

    def test_single_item(self):
        result = bcs_serialize_vector([b"\x42"])
        # Length 1 + the byte
        assert result == b"\x01\x42"

    def test_multiple_items(self):
        items = [b"\x01\x02", b"\x03\x04"]
        result = bcs_serialize_vector(items)
        assert result == b"\x02\x01\x02\x03\x04"
