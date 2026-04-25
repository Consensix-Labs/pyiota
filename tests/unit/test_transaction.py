"""Tests for the Transaction builder."""

import pytest

from pyiota.bcs_types import (
    ArgumentKind,
    CallArgKind,
    CommandKind,
    serialize_pure_address,
    serialize_pure_u64,
)
from pyiota.transaction import Transaction, TransactionResult


class TestTransactionBuilder:
    def test_gas_property(self):
        tx = Transaction()
        gas = tx.gas
        assert gas.kind == ArgumentKind.GAS_COIN

    def test_pure_u64(self):
        tx = Transaction()
        arg = tx.pure_u64(1_000_000)
        assert arg.kind == ArgumentKind.INPUT
        assert arg.index == 0
        # Verify the input was registered
        assert len(tx._inputs) == 1
        assert tx._inputs[0].kind == CallArgKind.PURE

    def test_pure_address(self):
        tx = Transaction()
        addr = "0x" + "ab" * 32
        arg = tx.pure_address(addr)
        assert arg.kind == ArgumentKind.INPUT
        assert tx._inputs[0].pure_data == bytes.fromhex("ab" * 32)

    def test_pure_auto_detect_int(self):
        tx = Transaction()
        tx.pure(42)
        # Auto-detected as u64
        assert tx._inputs[0].pure_data == serialize_pure_u64(42)

    def test_pure_auto_detect_bool(self):
        tx = Transaction()
        tx.pure(True)
        assert tx._inputs[0].pure_data == b"\x01"

    def test_pure_auto_detect_address_string(self):
        tx = Transaction()
        addr = "0x" + "cc" * 32
        tx.pure(addr)
        assert tx._inputs[0].pure_data == serialize_pure_address(addr)

    def test_multiple_inputs_get_sequential_indices(self):
        tx = Transaction()
        a0 = tx.pure_u64(100)
        a1 = tx.pure_u64(200)
        a2 = tx.pure_u64(300)
        assert a0.index == 0
        assert a1.index == 1
        assert a2.index == 2

    def test_split_coins_creates_command(self):
        tx = Transaction()
        result = tx.split_coins(tx.gas, [1_000_000])
        assert isinstance(result, TransactionResult)
        assert len(tx._commands) == 1
        cmd = tx._commands[0]
        assert cmd.kind == CommandKind.SPLIT_COINS
        assert cmd.split_coin.kind == ArgumentKind.GAS_COIN

    def test_split_coins_wraps_int_amounts(self):
        """Integer amounts should be automatically wrapped as pure u64 inputs."""
        tx = Transaction()
        tx.split_coins(tx.gas, [100, 200])
        # Two amount inputs should have been added
        assert len(tx._inputs) == 2
        cmd = tx._commands[0]
        assert len(cmd.split_amounts) == 2

    def test_transfer_objects(self):
        tx = Transaction()
        coin = tx.split_coins(tx.gas, [1000])
        recipient = "0x" + "dd" * 32
        tx.transfer_objects([coin], recipient)

        assert len(tx._commands) == 2  # split + transfer
        transfer_cmd = tx._commands[1]
        assert transfer_cmd.kind == CommandKind.TRANSFER_OBJECTS
        assert len(transfer_cmd.transfer_objects) == 1

    def test_merge_coins(self):
        tx = Transaction()
        # Create two coins via split, then merge them
        coins = tx.split_coins(tx.gas, [100, 200])
        tx.merge_coins(coins[0], [coins[1]])

        assert len(tx._commands) == 2
        merge_cmd = tx._commands[1]
        assert merge_cmd.kind == CommandKind.MERGE_COINS

    def test_move_call(self):
        tx = Transaction()
        amount_arg = tx.pure_u64(1000)
        result = tx.move_call(
            target="0x2::coin::split",
            arguments=[tx.gas, amount_arg],
            type_arguments=["0x2::iota::IOTA"],
        )
        assert isinstance(result, TransactionResult)
        cmd = tx._commands[0]
        assert cmd.kind == CommandKind.MOVE_CALL
        assert cmd.move_call.module == "coin"
        assert cmd.move_call.function == "split"
        assert len(cmd.move_call.type_arguments) == 1

    def test_move_call_invalid_target(self):
        tx = Transaction()
        with pytest.raises(ValueError, match="Invalid target format"):
            tx.move_call(target="invalid_target")

    def test_set_sender(self):
        tx = Transaction()
        result = tx.set_sender("0x" + "aa" * 32)
        assert tx._sender == "0x" + "aa" * 32
        # Should return self for chaining
        assert result is tx

    def test_set_gas_budget(self):
        tx = Transaction()
        tx.set_gas_budget(100_000_000)
        assert tx._gas_budget == 100_000_000

    def test_set_gas_price(self):
        tx = Transaction()
        tx.set_gas_price(1000)
        assert tx._gas_price == 1000


class TestTransactionResult:
    def test_to_argument(self):
        result = TransactionResult(0)
        arg = result.to_argument()
        assert arg.kind == ArgumentKind.RESULT
        assert arg.index == 0

    def test_indexing(self):
        result = TransactionResult(2)
        nested = result[1]
        assert nested.kind == ArgumentKind.NESTED_RESULT
        assert nested.index == 2
        assert nested.nested_index == 1
