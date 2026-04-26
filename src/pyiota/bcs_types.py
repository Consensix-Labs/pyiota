"""BCS type definitions for IOTA Rebased transaction structures.

These define the exact binary layout that IOTA nodes expect for transaction
serialization. Derived from the TypeScript SDK's BCS registrations and the
Rust types in the iotaledger/iota monorepo.

Each class has a serialize() method returning BCS bytes, and the structure
mirrors IOTA's on-chain types.

Key references:
- Rust types: iota-types/src/transaction.rs, iota-types/src/base_types.rs
- TS SDK BCS: @iota/iota-sdk/src/bcs/bcs.ts
- TS SDK internal types: @iota/iota-sdk/src/transactions/data/internal.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from pyiota.bcs import BcsWriter

# -- Address and digest constants --

ADDRESS_LENGTH = 32  # 32 bytes = 64 hex chars
DIGEST_LENGTH = 32


# -- Argument types (references to inputs/results within a PTB) --


class ArgumentKind(IntEnum):
    """BCS variant index for the Argument enum."""

    GAS_COIN = 0
    INPUT = 1
    RESULT = 2
    NESTED_RESULT = 3


@dataclass
class Argument:
    """A reference to a value within a Programmable Transaction Block.

    Used as arguments to transaction commands (MoveCall, TransferObjects, etc.).
    """

    kind: ArgumentKind
    # For INPUT and RESULT: the index
    index: int = 0
    # For NESTED_RESULT: the result index within a multi-result command
    nested_index: int = 0

    def serialize(self) -> bytes:
        w = BcsWriter()
        w.write_variant_index(self.kind)
        if self.kind == ArgumentKind.GAS_COIN:
            pass  # No additional data
        elif self.kind == ArgumentKind.INPUT or self.kind == ArgumentKind.RESULT:
            w.write_u16(self.index)
        elif self.kind == ArgumentKind.NESTED_RESULT:
            w.write_u16(self.index)
            w.write_u16(self.nested_index)
        return w.finish()


# Convenience constructors
GAS_COIN = Argument(kind=ArgumentKind.GAS_COIN)


def input_arg(index: int) -> Argument:
    return Argument(kind=ArgumentKind.INPUT, index=index)


def result_arg(index: int) -> Argument:
    return Argument(kind=ArgumentKind.RESULT, index=index)


def nested_result_arg(index: int, nested: int) -> Argument:
    return Argument(kind=ArgumentKind.NESTED_RESULT, index=index, nested_index=nested)


# -- CallArg types (transaction inputs) --


class CallArgKind(IntEnum):
    """BCS variant index for the CallArg enum."""

    PURE = 0
    OBJECT = 1


class ObjectArgKind(IntEnum):
    """BCS variant index for the ObjectArg enum."""

    IMM_OR_OWNED_OBJECT = 0
    SHARED_OBJECT = 1
    RECEIVING = 2


@dataclass
class BcsObjectRef:
    """A reference to a specific version of an on-chain object: (id, version, digest).

    In IOTA's Rust types this is a tuple (ObjectID, SequenceNumber, ObjectDigest).
    ObjectDigest is serialized as a length-prefixed byte vector in BCS, not as
    fixed 32 bytes -- it wraps Digest which uses BCS bytes serialization.
    """

    object_id: bytes  # 32 bytes
    version: int  # u64
    digest: bytes  # 32 bytes, but BCS-serialized as length-prefixed

    def serialize(self) -> bytes:
        w = BcsWriter()
        # ObjectID: fixed 32 bytes (AccountAddress)
        w.write_fixed_bytes(self.object_id)
        # SequenceNumber: u64
        w.write_u64(self.version)
        # ObjectDigest: serialized as BCS bytes (ULEB128 length prefix + data)
        # In Rust: ObjectDigest(Digest) where Digest serializes as Vec<u8>
        w.write_bytes(self.digest)
        return w.finish()


@dataclass
class SharedObjectRef:
    """Reference to a shared object, including the version at which it became shared."""

    object_id: bytes  # 32 bytes
    initial_shared_version: int  # u64
    mutable: bool

    def serialize(self) -> bytes:
        w = BcsWriter()
        w.write_fixed_bytes(self.object_id)
        w.write_u64(self.initial_shared_version)
        w.write_bool(self.mutable)
        return w.finish()


@dataclass
class CallArg:
    """An input to a Programmable Transaction Block."""

    kind: CallArgKind
    # For PURE: the BCS-serialized value
    pure_data: bytes = b""
    # For OBJECT: the object reference
    object_kind: ObjectArgKind = ObjectArgKind.IMM_OR_OWNED_OBJECT
    object_ref: BcsObjectRef | None = None
    shared_ref: SharedObjectRef | None = None

    def serialize(self) -> bytes:
        w = BcsWriter()
        w.write_variant_index(self.kind)
        if self.kind == CallArgKind.PURE:
            w.write_bytes(self.pure_data)
        elif self.kind == CallArgKind.OBJECT:
            w.write_variant_index(self.object_kind)
            if self.object_kind == ObjectArgKind.IMM_OR_OWNED_OBJECT:
                assert self.object_ref is not None
                w.write_fixed_bytes(self.object_ref.serialize())
            elif self.object_kind == ObjectArgKind.SHARED_OBJECT:
                assert self.shared_ref is not None
                w.write_fixed_bytes(self.shared_ref.serialize())
            elif self.object_kind == ObjectArgKind.RECEIVING:
                assert self.object_ref is not None
                w.write_fixed_bytes(self.object_ref.serialize())
        return w.finish()


# -- Command types (operations within a PTB) --


class CommandKind(IntEnum):
    """BCS variant index for the Command enum."""

    MOVE_CALL = 0
    TRANSFER_OBJECTS = 1
    SPLIT_COINS = 2
    MERGE_COINS = 3
    PUBLISH = 4
    MAKE_MOVE_VEC = 5
    UPGRADE = 6


@dataclass
class ProgrammableMoveCall:
    """A Move function call within a PTB."""

    package: bytes  # 32-byte package ID
    module: str
    function: str
    type_arguments: list[str]  # TypeTag strings
    arguments: list[Argument]


@dataclass
class Command:
    """A single command in a Programmable Transaction Block."""

    kind: CommandKind
    # Fields vary by kind
    move_call: ProgrammableMoveCall | None = None
    # TransferObjects: (objects, recipient)
    transfer_objects: list[Argument] | None = None
    transfer_recipient: Argument | None = None
    # SplitCoins: (coin, amounts)
    split_coin: Argument | None = None
    split_amounts: list[Argument] | None = None
    # MergeCoins: (destination, sources)
    merge_destination: Argument | None = None
    merge_sources: list[Argument] | None = None
    # Publish: (modules, dependencies)
    publish_modules: list[bytes] | None = None
    publish_dependencies: list[bytes] | None = None

    def serialize(self) -> bytes:
        w = BcsWriter()
        w.write_variant_index(self.kind)

        if self.kind == CommandKind.MOVE_CALL:
            assert self.move_call is not None
            mc = self.move_call
            w.write_fixed_bytes(mc.package)
            w.write_str(mc.module)
            w.write_str(mc.function)
            # Type arguments as a vector of TypeTag
            w.write_vector_length(len(mc.type_arguments))
            for type_arg in mc.type_arguments:
                w.write_fixed_bytes(_serialize_type_tag(type_arg))
            # Arguments
            w.write_vector_length(len(mc.arguments))
            for arg in mc.arguments:
                w.write_fixed_bytes(arg.serialize())

        elif self.kind == CommandKind.TRANSFER_OBJECTS:
            assert self.transfer_objects is not None
            assert self.transfer_recipient is not None
            w.write_vector_length(len(self.transfer_objects))
            for obj in self.transfer_objects:
                w.write_fixed_bytes(obj.serialize())
            w.write_fixed_bytes(self.transfer_recipient.serialize())

        elif self.kind == CommandKind.SPLIT_COINS:
            assert self.split_coin is not None
            assert self.split_amounts is not None
            w.write_fixed_bytes(self.split_coin.serialize())
            w.write_vector_length(len(self.split_amounts))
            for amount in self.split_amounts:
                w.write_fixed_bytes(amount.serialize())

        elif self.kind == CommandKind.MERGE_COINS:
            assert self.merge_destination is not None
            assert self.merge_sources is not None
            w.write_fixed_bytes(self.merge_destination.serialize())
            w.write_vector_length(len(self.merge_sources))
            for src in self.merge_sources:
                w.write_fixed_bytes(src.serialize())

        elif self.kind == CommandKind.PUBLISH:
            assert self.publish_modules is not None
            assert self.publish_dependencies is not None
            w.write_vector_length(len(self.publish_modules))
            for module in self.publish_modules:
                w.write_bytes(module)
            w.write_vector_length(len(self.publish_dependencies))
            for dep in self.publish_dependencies:
                w.write_fixed_bytes(dep)

        return w.finish()


# -- TypeTag serialization --
# Move type tags are complex (struct types with generics). For v0.1, we support
# the common cases needed for MoveCall type arguments.


class TypeTagKind(IntEnum):
    BOOL = 0
    U8 = 1
    U64 = 2
    U128 = 3
    ADDRESS = 4
    SIGNER = 5
    VECTOR = 6
    STRUCT = 7
    U16 = 8
    U32 = 9
    U256 = 10


def _serialize_type_tag(type_str: str) -> bytes:
    """Serialize a Move type tag string to BCS.

    Handles primitive types and struct types like "0xPKG::module::Type<T>".
    """
    w = BcsWriter()

    # Primitive types
    primitives = {
        "bool": TypeTagKind.BOOL,
        "u8": TypeTagKind.U8,
        "u16": TypeTagKind.U16,
        "u32": TypeTagKind.U32,
        "u64": TypeTagKind.U64,
        "u128": TypeTagKind.U128,
        "u256": TypeTagKind.U256,
        "address": TypeTagKind.ADDRESS,
        "signer": TypeTagKind.SIGNER,
    }
    if type_str in primitives:
        w.write_variant_index(primitives[type_str])
        return w.finish()

    # Vector type: vector<T>
    if type_str.startswith("vector<") and type_str.endswith(">"):
        inner = type_str[7:-1]
        w.write_variant_index(TypeTagKind.VECTOR)
        w.write_fixed_bytes(_serialize_type_tag(inner))
        return w.finish()

    # Struct type: 0xADDR::module::Name or 0xADDR::module::Name<T1, T2>
    w.write_variant_index(TypeTagKind.STRUCT)
    w.write_fixed_bytes(_serialize_struct_tag(type_str))
    return w.finish()


def _serialize_struct_tag(type_str: str) -> bytes:
    """Serialize a Move StructTag: address::module::name<type_params>."""
    w = BcsWriter()

    # Split off type parameters if present
    type_params_str = ""
    base = type_str
    # Find the outermost '<' for generic params
    depth = 0
    split_pos = -1
    for i, ch in enumerate(type_str):
        if ch == "<" and depth == 0:
            split_pos = i
            break
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1

    if split_pos >= 0:
        base = type_str[:split_pos]
        type_params_str = type_str[split_pos + 1 : -1]  # Strip outer < >

    parts = base.split("::")
    if len(parts) != 3:
        raise ValueError(f"Invalid struct type: {type_str}. Expected address::module::name")

    address_str, module, name = parts

    # Serialize address as 32 bytes
    addr_hex = address_str.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
    w.write_fixed_bytes(bytes.fromhex(addr_hex))
    w.write_str(module)
    w.write_str(name)

    # Parse and serialize type parameters
    if type_params_str:
        type_params = _split_type_params(type_params_str)
        w.write_vector_length(len(type_params))
        for param in type_params:
            w.write_fixed_bytes(_serialize_type_tag(param.strip()))
    else:
        w.write_vector_length(0)

    return w.finish()


def _split_type_params(params_str: str) -> list[str]:
    """Split comma-separated type parameters, respecting nested generics."""
    params = []
    depth = 0
    current = ""
    for ch in params_str:
        if ch == "<":
            depth += 1
            current += ch
        elif ch == ">":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        params.append(current.strip())
    return params


# -- Transaction data envelope --


class TransactionExpiration(IntEnum):
    """BCS variant for transaction expiration."""

    NONE = 0
    EPOCH = 1


@dataclass
class GasPayment:
    """Gas configuration for a transaction.

    Rust struct field order (which BCS follows): payment, owner, price, budget.
    """

    payment: list[BcsObjectRef]  # Coin objects to pay gas from
    owner: bytes  # 32-byte sender address
    price: int  # Gas price (u64)
    budget: int  # Gas budget (u64)

    def serialize(self) -> bytes:
        w = BcsWriter()
        # Payment: vector of BcsObjectRef (field order matches Rust struct)
        w.write_vector_length(len(self.payment))
        for ref in self.payment:
            w.write_fixed_bytes(ref.serialize())
        # Owner: fixed 32-byte address
        w.write_fixed_bytes(self.owner)
        # Price: u64
        w.write_u64(self.price)
        # Budget: u64
        w.write_u64(self.budget)
        return w.finish()


@dataclass
class ProgrammableTransaction:
    """A Programmable Transaction Block: inputs + commands."""

    inputs: list[CallArg]
    commands: list[Command]

    def serialize(self) -> bytes:
        w = BcsWriter()
        w.write_vector_length(len(self.inputs))
        for inp in self.inputs:
            w.write_fixed_bytes(inp.serialize())
        w.write_vector_length(len(self.commands))
        for cmd in self.commands:
            w.write_fixed_bytes(cmd.serialize())
        return w.finish()


class TransactionKindVariant(IntEnum):
    """BCS variant for TransactionKind."""

    PROGRAMMABLE_TRANSACTION = 0
    # Other variants (ChangeEpoch, Genesis, ConsensusCommitPrologue) are system-only


@dataclass
class TransactionData:
    """The complete transaction data envelope that gets BCS-serialized and signed.

    This is the V1 format used by IOTA Rebased.

    BCS layout (TransactionData enum, variant 0 = V1):
        variant_index(0)  -- V1
        TransactionKind   -- variant 0 = ProgrammableTransaction
        sender            -- 32-byte address
        gas_data          -- GasPayment struct
        expiration        -- TransactionExpiration enum

    Field order must match Rust's TransactionDataV1:
        kind, sender, gas_data, expiration
    """

    kind: ProgrammableTransaction
    sender: bytes  # 32-byte sender address
    gas: GasPayment
    expiration_epoch: int | None = None  # None = no expiration

    def serialize(self) -> bytes:
        """Serialize to BCS bytes ready for signing."""
        w = BcsWriter()
        # TransactionData is an enum with variant V1 = 0
        w.write_variant_index(0)  # V1
        # Field 1: TransactionKind enum
        w.write_variant_index(TransactionKindVariant.PROGRAMMABLE_TRANSACTION)
        w.write_fixed_bytes(self.kind.serialize())
        # Field 2: sender address (32 bytes)
        w.write_fixed_bytes(self.sender)
        # Field 3: gas_data
        w.write_fixed_bytes(self.gas.serialize())
        # Field 4: expiration
        if self.expiration_epoch is None:
            w.write_variant_index(TransactionExpiration.NONE)
        else:
            w.write_variant_index(TransactionExpiration.EPOCH)
            w.write_u64(self.expiration_epoch)
        return w.finish()


# -- Pure value serialization helpers --


def serialize_pure_u8(value: int) -> bytes:
    return BcsWriter().write_u8(value).finish()


def serialize_pure_u16(value: int) -> bytes:
    return BcsWriter().write_u16(value).finish()


def serialize_pure_u32(value: int) -> bytes:
    return BcsWriter().write_u32(value).finish()


def serialize_pure_u64(value: int) -> bytes:
    return BcsWriter().write_u64(value).finish()


def serialize_pure_u128(value: int) -> bytes:
    return BcsWriter().write_u128(value).finish()


def serialize_pure_u256(value: int) -> bytes:
    return BcsWriter().write_u256(value).finish()


def serialize_pure_bool(value: bool) -> bytes:
    return BcsWriter().write_bool(value).finish()


def serialize_pure_string(value: str) -> bytes:
    return BcsWriter().write_str(value).finish()


def serialize_pure_address(address: str) -> bytes:
    """Serialize an IOTA address (0x-prefixed hex) as a 32-byte pure value."""
    addr_hex = address.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
    return bytes.fromhex(addr_hex)


def serialize_pure_bytes(data: bytes) -> bytes:
    return BcsWriter().write_bytes(data).finish()
