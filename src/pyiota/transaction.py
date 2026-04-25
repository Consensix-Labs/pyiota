"""Programmable Transaction Block builder.

Mirrors the IOTA TypeScript SDK's Transaction class. Builds transactions
client-side using BCS serialization -- no server-side unsafe_ methods needed.

Usage:
    tx = Transaction()
    coin = tx.split_coins(tx.gas, [1_000_000_000])
    tx.transfer_objects([coin], recipient_address)

    # Build and sign
    tx_bytes = await tx.build(client=client, signer=keypair)
    result = await client.sign_and_execute_transaction(
        signer=keypair, tx_bytes=tx_bytes
    )
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

from pyiota.base58 import base58_decode
from pyiota.bcs_types import (
    ADDRESS_LENGTH,
    Argument,
    ArgumentKind,
    CallArg,
    CallArgKind,
    Command,
    CommandKind,
    GAS_COIN,
    GasPayment,
    ObjectArgKind,
    BcsObjectRef,
    ProgrammableMoveCall,
    ProgrammableTransaction,
    SharedObjectRef,
    TransactionData,
    input_arg,
    result_arg,
    serialize_pure_address,
    serialize_pure_bool,
    serialize_pure_bytes,
    serialize_pure_string,
    serialize_pure_u128,
    serialize_pure_u16,
    serialize_pure_u256,
    serialize_pure_u32,
    serialize_pure_u64,
    serialize_pure_u8,
)

if TYPE_CHECKING:
    from pyiota.client import IotaClient
    from pyiota.crypto.ed25519 import Ed25519Keypair
    from pyiota.sync_client import SyncIotaClient

# Default gas budget if not specified
DEFAULT_GAS_BUDGET = 50_000_000


class TransactionResult:
    """Reference to the result of a transaction command.

    Can be used as an argument to subsequent commands in the same PTB.
    Supports indexing for commands that return multiple results.
    """

    def __init__(self, index: int) -> None:
        self._index = index

    def to_argument(self) -> Argument:
        """Convert to a BCS Argument for serialization."""
        return result_arg(self._index)

    def __getitem__(self, nested_index: int) -> Argument:
        """Access a specific result from a multi-result command."""
        from pyiota.bcs_types import nested_result_arg
        return nested_result_arg(self._index, nested_index)


class Transaction:
    """Builder for Programmable Transaction Blocks.

    Provides a fluent API for constructing transactions with multiple commands.
    """

    def __init__(self) -> None:
        self._inputs: list[CallArg] = []
        self._commands: list[Command] = []
        # Explicitly set gas budget/price, or let build() resolve them
        self._gas_budget: int | None = None
        self._gas_price: int | None = None
        self._gas_payment: list[dict[str, Any]] | None = None
        self._sender: str | None = None

    @property
    def gas(self) -> Argument:
        """Special argument referencing the gas coin. Mirrors TS SDK's tx.gas."""
        return GAS_COIN

    # -- Input constructors --

    def _add_input(self, call_arg: CallArg) -> Argument:
        """Register a new input and return its Argument reference."""
        index = len(self._inputs)
        self._inputs.append(call_arg)
        return input_arg(index)

    def pure(self, value: Any, type_hint: str | None = None) -> Argument:
        """Create a pure (non-object) input value.

        If type_hint is provided, it determines the BCS serialization format.
        Otherwise the type is inferred from the Python value.

        Args:
            value: The value to serialize (int, str, bool, bytes, or address string).
            type_hint: Optional type hint ("u8", "u16", "u32", "u64", "u128", "u256",
                "bool", "string", "address", or "bytes").
        """
        data = self._serialize_pure(value, type_hint)
        return self._add_input(CallArg(kind=CallArgKind.PURE, pure_data=data))

    def pure_u8(self, value: int) -> Argument:
        return self.pure(value, "u8")

    def pure_u16(self, value: int) -> Argument:
        return self.pure(value, "u16")

    def pure_u32(self, value: int) -> Argument:
        return self.pure(value, "u32")

    def pure_u64(self, value: int) -> Argument:
        return self.pure(value, "u64")

    def pure_u128(self, value: int) -> Argument:
        return self.pure(value, "u128")

    def pure_u256(self, value: int) -> Argument:
        return self.pure(value, "u256")

    def pure_bool(self, value: bool) -> Argument:
        return self.pure(value, "bool")

    def pure_string(self, value: str) -> Argument:
        return self.pure(value, "string")

    def pure_address(self, address: str) -> Argument:
        return self.pure(address, "address")

    def object(
        self,
        object_id: str,
        *,
        version: int | None = None,
        digest: str | None = None,
        initial_shared_version: int | None = None,
        mutable: bool = True,
    ) -> Argument:
        """Create an object input reference.

        For immutable/owned objects, provide version and digest.
        For shared objects, provide initial_shared_version.
        If only object_id is provided, the transaction build step will resolve
        the object's details from the chain.
        """
        if initial_shared_version is not None:
            # Shared object
            obj_bytes = bytes.fromhex(
                object_id.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
            )
            shared_ref = SharedObjectRef(
                object_id=obj_bytes,
                initial_shared_version=initial_shared_version,
                mutable=mutable,
            )
            return self._add_input(CallArg(
                kind=CallArgKind.OBJECT,
                object_kind=ObjectArgKind.SHARED_OBJECT,
                shared_ref=shared_ref,
            ))
        elif version is not None and digest is not None:
            # Immutable or owned object with known version
            obj_bytes = bytes.fromhex(
                object_id.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
            )
            # Digests from the RPC are Base58-encoded
            digest_bytes = base58_decode(digest)
            obj_ref = BcsObjectRef(
                object_id=obj_bytes,
                version=version,
                digest=digest_bytes,
            )
            return self._add_input(CallArg(
                kind=CallArgKind.OBJECT,
                object_kind=ObjectArgKind.IMM_OR_OWNED_OBJECT,
                object_ref=obj_ref,
            ))
        else:
            raise ValueError(
                f"Object reference for {object_id} requires version and digest. "
                f"Use client.get_object() to fetch them, or pass them directly: "
                f"tx.object(object_id, version=..., digest=...)"
            )

    # -- Transaction commands --

    def transfer_objects(
        self,
        objects: list[Argument | TransactionResult],
        recipient: str | Argument,
    ) -> TransactionResult:
        """Transfer one or more objects to a recipient address.

        Args:
            objects: List of object arguments to transfer.
            recipient: Recipient address (string) or an Argument reference.
        """
        resolved_objects = [self._resolve_argument(obj) for obj in objects]

        if isinstance(recipient, str):
            recipient_arg = self.pure_address(recipient)
        else:
            recipient_arg = self._resolve_argument(recipient)

        cmd_index = len(self._commands)
        self._commands.append(Command(
            kind=CommandKind.TRANSFER_OBJECTS,
            transfer_objects=resolved_objects,
            transfer_recipient=recipient_arg,
        ))
        return TransactionResult(cmd_index)

    def split_coins(
        self,
        coin: Argument | TransactionResult,
        amounts: list[int | Argument | TransactionResult],
    ) -> TransactionResult:
        """Split a coin into new coins with the specified amounts.

        Args:
            coin: The coin to split (commonly tx.gas for the gas coin).
            amounts: List of amounts for each new coin. Integers are
                automatically wrapped as pure u64 inputs.

        Returns:
            TransactionResult that can be indexed to access individual coins.
        """
        coin_arg = self._resolve_argument(coin)
        amount_args = []
        for amount in amounts:
            if isinstance(amount, int):
                amount_args.append(self.pure_u64(amount))
            else:
                amount_args.append(self._resolve_argument(amount))

        cmd_index = len(self._commands)
        self._commands.append(Command(
            kind=CommandKind.SPLIT_COINS,
            split_coin=coin_arg,
            split_amounts=amount_args,
        ))
        return TransactionResult(cmd_index)

    def merge_coins(
        self,
        destination: Argument | TransactionResult,
        sources: list[Argument | TransactionResult],
    ) -> TransactionResult:
        """Merge multiple coins into one.

        Args:
            destination: The coin to merge into.
            sources: Coins to merge from (consumed after merge).
        """
        dest_arg = self._resolve_argument(destination)
        source_args = [self._resolve_argument(src) for src in sources]

        cmd_index = len(self._commands)
        self._commands.append(Command(
            kind=CommandKind.MERGE_COINS,
            merge_destination=dest_arg,
            merge_sources=source_args,
        ))
        return TransactionResult(cmd_index)

    def move_call(
        self,
        *,
        target: str,
        arguments: list[Argument | TransactionResult] | None = None,
        type_arguments: list[str] | None = None,
    ) -> TransactionResult:
        """Call a Move function.

        Args:
            target: The function to call in "package::module::function" format.
            arguments: Arguments to pass to the function.
            type_arguments: Move type arguments (generics), e.g.
                ["0x2::coin::Coin<0x2::iota::IOTA>"].
        """
        parts = target.split("::")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid target format: {target}. "
                "Expected 'package_id::module::function'"
            )
        package_str, module, function = parts

        package_bytes = bytes.fromhex(
            package_str.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
        )

        resolved_args = [
            self._resolve_argument(arg) for arg in (arguments or [])
        ]

        cmd_index = len(self._commands)
        self._commands.append(Command(
            kind=CommandKind.MOVE_CALL,
            move_call=ProgrammableMoveCall(
                package=package_bytes,
                module=module,
                function=function,
                type_arguments=type_arguments or [],
                arguments=resolved_args,
            ),
        ))
        return TransactionResult(cmd_index)

    # -- Configuration --

    def set_sender(self, address: str) -> Transaction:
        self._sender = address
        return self

    def set_gas_budget(self, budget: int) -> Transaction:
        self._gas_budget = budget
        return self

    def set_gas_price(self, price: int) -> Transaction:
        self._gas_price = price
        return self

    def set_gas_payment(self, coins: list[dict[str, Any]]) -> Transaction:
        """Set specific coin objects for gas payment.

        Args:
            coins: List of coin references, each with "objectId", "version", "digest".
        """
        self._gas_payment = coins
        return self

    # -- Build --

    async def build(
        self,
        *,
        client: IotaClient,
        signer: Ed25519Keypair | None = None,
    ) -> bytes:
        """Build the transaction into BCS-serialized bytes ready for signing.

        Resolves gas price, gas coins, and unresolved object references from
        the chain. Requires a client connection.

        Args:
            client: Connected IotaClient for resolving on-chain data.
            signer: Keypair whose address is used as the sender. Required if
                set_sender() was not called.

        Returns:
            BCS-serialized TransactionData bytes.
        """
        sender = self._sender
        if sender is None and signer is not None:
            sender = signer.address
        if sender is None:
            raise ValueError("Sender address required. Call set_sender() or provide a signer.")

        sender_bytes = bytes.fromhex(
            sender.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
        )

        # Resolve gas price from the network if not set
        gas_price = self._gas_price
        if gas_price is None:
            gas_price = await client.get_reference_gas_price()

        gas_budget = self._gas_budget or DEFAULT_GAS_BUDGET

        # Resolve gas payment coins
        gas_refs = await self._resolve_gas_payment(client, sender)

        ptb = ProgrammableTransaction(
            inputs=self._inputs,
            commands=self._commands,
        )

        gas = GasPayment(
            payment=gas_refs,
            owner=sender_bytes,
            price=gas_price,
            budget=gas_budget,
        )

        tx_data = TransactionData(
            kind=ptb,
            sender=sender_bytes,
            gas=gas,
        )

        return tx_data.serialize()

    def build_sync(
        self,
        *,
        client: SyncIotaClient,
        signer: Ed25519Keypair | None = None,
    ) -> bytes:
        """Synchronous version of build().

        Uses the sync client to resolve on-chain data.
        """
        sender = self._sender
        if sender is None and signer is not None:
            sender = signer.address
        if sender is None:
            raise ValueError("Sender address required. Call set_sender() or provide a signer.")

        sender_bytes = bytes.fromhex(
            sender.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
        )

        gas_price = self._gas_price
        if gas_price is None:
            gas_price = client.get_reference_gas_price()

        gas_budget = self._gas_budget or DEFAULT_GAS_BUDGET
        gas_refs = self._resolve_gas_payment_sync(client, sender)

        ptb = ProgrammableTransaction(
            inputs=self._inputs,
            commands=self._commands,
        )

        gas = GasPayment(
            payment=gas_refs,
            owner=sender_bytes,
            price=gas_price,
            budget=gas_budget,
        )

        tx_data = TransactionData(
            kind=ptb,
            sender=sender_bytes,
            gas=gas,
        )

        return tx_data.serialize()

    # -- Internal helpers --

    def _resolve_argument(self, arg: Argument | TransactionResult) -> Argument:
        """Convert a TransactionResult to its Argument representation."""
        if isinstance(arg, TransactionResult):
            return arg.to_argument()
        return arg

    @staticmethod
    def _serialize_pure(value: Any, type_hint: str | None) -> bytes:
        """Serialize a Python value to BCS bytes for a pure input."""
        if type_hint is not None:
            serializers = {
                "u8": serialize_pure_u8,
                "u16": serialize_pure_u16,
                "u32": serialize_pure_u32,
                "u64": serialize_pure_u64,
                "u128": serialize_pure_u128,
                "u256": serialize_pure_u256,
                "bool": serialize_pure_bool,
                "string": serialize_pure_string,
                "address": serialize_pure_address,
                "bytes": serialize_pure_bytes,
            }
            serializer = serializers.get(type_hint)
            if serializer is None:
                raise ValueError(f"Unknown type hint: {type_hint}")
            return serializer(value)

        # Auto-detect type from Python value
        if isinstance(value, bool):
            return serialize_pure_bool(value)
        if isinstance(value, int):
            return serialize_pure_u64(value)
        if isinstance(value, str):
            # Strings starting with 0x are treated as addresses
            if value.startswith("0x"):
                return serialize_pure_address(value)
            return serialize_pure_string(value)
        if isinstance(value, (bytes, bytearray)):
            return serialize_pure_bytes(value)
        raise ValueError(f"Cannot auto-serialize type {type(value).__name__}. Use a type hint.")

    async def _resolve_gas_payment(
        self, client: IotaClient, sender: str
    ) -> list[BcsObjectRef]:
        """Resolve gas payment coins from the chain."""
        if self._gas_payment is not None:
            return [
                BcsObjectRef(
                    object_id=bytes.fromhex(
                        c["objectId"].lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
                    ),
                    version=int(c["version"]),
                    digest=base58_decode(c["digest"]),
                )
                for c in self._gas_payment
            ]

        # Auto-select: get the sender's IOTA coins
        coins = await client.get_coins(sender)
        if not coins.data:
            raise ValueError(f"No IOTA coins found for sender {sender}")

        # Use the first coin for gas payment
        first_coin = coins.data[0]
        obj = await client.get_object(first_coin.coin_object_id)
        return [
            BcsObjectRef(
                object_id=bytes.fromhex(
                    obj.object_id.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
                ),
                version=obj.version,
                digest=base58_decode(obj.digest),
            )
        ]

    def _resolve_gas_payment_sync(
        self, client: SyncIotaClient, sender: str
    ) -> list[BcsObjectRef]:
        """Synchronous version of _resolve_gas_payment."""
        if self._gas_payment is not None:
            return [
                BcsObjectRef(
                    object_id=bytes.fromhex(
                        c["objectId"].lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
                    ),
                    version=int(c["version"]),
                    digest=base58_decode(c["digest"]),
                )
                for c in self._gas_payment
            ]

        coins = client.get_coins(sender)
        if not coins.data:
            raise ValueError(f"No IOTA coins found for sender {sender}")

        first_coin = coins.data[0]
        obj = client.get_object(first_coin.coin_object_id)
        return [
            BcsObjectRef(
                object_id=bytes.fromhex(
                    obj.object_id.lower().removeprefix("0x").zfill(ADDRESS_LENGTH * 2)
                ),
                version=obj.version,
                digest=base58_decode(obj.digest),
            )
        ]