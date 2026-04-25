/**
 * Golden vector generator for pyiota BCS tests.
 *
 * Uses the official @iota/iota-sdk to serialize various BCS structures
 * and outputs the raw bytes as hex. The pyiota Python tests assert
 * their output matches these vectors byte-for-byte.
 */

const { bcs } = require('@iota/iota-sdk/bcs');
const { toBase58, fromBase58, toHex, fromHex } = require('@iota/bcs');

function toHexStr(bytes) {
  return Buffer.from(bytes).toString('hex');
}

const vectors = {};

// ============================================================
// 1. Raw BCS primitives
// ============================================================

vectors.pure_u8_0 = toHexStr(bcs.u8().serialize(0).toBytes());
vectors.pure_u8_255 = toHexStr(bcs.u8().serialize(255).toBytes());
vectors.pure_u16_256 = toHexStr(bcs.u16().serialize(256).toBytes());
vectors.pure_u32_1 = toHexStr(bcs.u32().serialize(1).toBytes());
vectors.pure_u64_1000000000 = toHexStr(bcs.u64().serialize(1000000000n).toBytes());
vectors.pure_u64_max = toHexStr(bcs.u64().serialize(18446744073709551615n).toBytes());
vectors.pure_u128_1 = toHexStr(bcs.u128().serialize(1n).toBytes());
vectors.pure_u128_max = toHexStr(bcs.u128().serialize(340282366920938463463374607431768211455n).toBytes());
vectors.pure_u256_1 = toHexStr(bcs.u256().serialize(1n).toBytes());
vectors.pure_bool_true = toHexStr(bcs.bool().serialize(true).toBytes());
vectors.pure_bool_false = toHexStr(bcs.bool().serialize(false).toBytes());
vectors.pure_string_hello = toHexStr(bcs.string().serialize("hello").toBytes());
vectors.pure_string_empty = toHexStr(bcs.string().serialize("").toBytes());

// Address: fixed 32 bytes
const testAddr = "0x" + "ab".repeat(32);
vectors.pure_address = toHexStr(bcs.Address.serialize(testAddr).toBytes());
// Short address should zero-pad to 32 bytes
vectors.pure_address_short = toHexStr(bcs.Address.serialize("0x1").toBytes());

// ============================================================
// 2. ObjectDigest (length-prefixed bytes)
// ============================================================

const digestBytes = new Uint8Array(32);
for (let i = 0; i < 32; i++) digestBytes[i] = i;
const digestBase58 = toBase58(digestBytes);
vectors.object_digest = toHexStr(bcs.ObjectDigest.serialize(digestBase58).toBytes());
vectors.object_digest_base58_input = digestBase58;

// ============================================================
// 3. IotaObjectRef
// ============================================================

const objRef = {
  objectId: "0x" + "a1".repeat(32),
  version: 42n,
  digest: digestBase58,
};
vectors.iota_object_ref = toHexStr(bcs.IotaObjectRef.serialize(objRef).toBytes());

// ============================================================
// 4. SharedObjectRef
// ============================================================

vectors.shared_object_ref = toHexStr(bcs.SharedObjectRef.serialize({
  objectId: "0x" + "b2".repeat(32),
  initialSharedVersion: 100n,
  mutable: true,
}).toBytes());

vectors.shared_object_ref_immutable = toHexStr(bcs.SharedObjectRef.serialize({
  objectId: "0x" + "b2".repeat(32),
  initialSharedVersion: 100n,
  mutable: false,
}).toBytes());

// ============================================================
// 5. Argument variants
// ============================================================

vectors.argument_gas_coin = toHexStr(bcs.Argument.serialize({ GasCoin: true }).toBytes());
vectors.argument_input_0 = toHexStr(bcs.Argument.serialize({ Input: 0 }).toBytes());
vectors.argument_input_5 = toHexStr(bcs.Argument.serialize({ Input: 5 }).toBytes());
vectors.argument_result_0 = toHexStr(bcs.Argument.serialize({ Result: 0 }).toBytes());
vectors.argument_result_3 = toHexStr(bcs.Argument.serialize({ Result: 3 }).toBytes());
vectors.argument_nested_result = toHexStr(bcs.Argument.serialize({ NestedResult: [2, 1] }).toBytes());

// ============================================================
// 6. CallArg variants
// ============================================================

// Pure: variant 0, struct Pure { bytes: vector<u8> }
const pureU64Bytes = Array.from(bcs.u64().serialize(1000000000n).toBytes());
vectors.call_arg_pure_u64 = toHexStr(bcs.CallArg.serialize({
  Pure: { bytes: pureU64Bytes },
}).toBytes());

// Object: ImmOrOwnedObject
vectors.call_arg_object_owned = toHexStr(bcs.CallArg.serialize({
  Object: { ImmOrOwnedObject: objRef },
}).toBytes());

// Object: SharedObject
vectors.call_arg_object_shared = toHexStr(bcs.CallArg.serialize({
  Object: {
    SharedObject: {
      objectId: "0x" + "b2".repeat(32),
      initialSharedVersion: 100n,
      mutable: true,
    },
  },
}).toBytes());

// Object: Receiving
vectors.call_arg_object_receiving = toHexStr(bcs.CallArg.serialize({
  Object: { Receiving: objRef },
}).toBytes());

// ============================================================
// 7. TypeTag serialization
// ============================================================

vectors.type_tag_bool = toHexStr(bcs.TypeTag.serialize("bool").toBytes());
vectors.type_tag_u8 = toHexStr(bcs.TypeTag.serialize("u8").toBytes());
vectors.type_tag_u16 = toHexStr(bcs.TypeTag.serialize("u16").toBytes());
vectors.type_tag_u32 = toHexStr(bcs.TypeTag.serialize("u32").toBytes());
vectors.type_tag_u64 = toHexStr(bcs.TypeTag.serialize("u64").toBytes());
vectors.type_tag_u128 = toHexStr(bcs.TypeTag.serialize("u128").toBytes());
vectors.type_tag_u256 = toHexStr(bcs.TypeTag.serialize("u256").toBytes());
vectors.type_tag_address = toHexStr(bcs.TypeTag.serialize("address").toBytes());
vectors.type_tag_signer = toHexStr(bcs.TypeTag.serialize("signer").toBytes());
vectors.type_tag_vector_u8 = toHexStr(bcs.TypeTag.serialize("vector<u8>").toBytes());
vectors.type_tag_struct_iota = toHexStr(bcs.TypeTag.serialize("0x2::iota::IOTA").toBytes());
vectors.type_tag_struct_coin = toHexStr(bcs.TypeTag.serialize("0x2::coin::Coin<0x2::iota::IOTA>").toBytes());
vectors.type_tag_vector_coin = toHexStr(bcs.TypeTag.serialize("vector<0x2::coin::Coin<0x2::iota::IOTA>>").toBytes());
vectors.type_tag_multi_generic = toHexStr(bcs.TypeTag.serialize("0x1::pair::Pair<u64, address>").toBytes());

// ============================================================
// 8. Command variants
// ============================================================

vectors.command_split_coins = toHexStr(bcs.Command.serialize({
  SplitCoins: {
    coin: { GasCoin: true },
    amounts: [{ Input: 0 }],
  },
}).toBytes());

vectors.command_transfer_objects = toHexStr(bcs.Command.serialize({
  TransferObjects: {
    objects: [{ Result: 0 }],
    address: { Input: 1 },
  },
}).toBytes());

vectors.command_merge_coins = toHexStr(bcs.Command.serialize({
  MergeCoins: {
    destination: { Input: 0 },
    sources: [{ Input: 1 }],
  },
}).toBytes());

vectors.command_move_call = toHexStr(bcs.Command.serialize({
  MoveCall: {
    package: "0x2",
    module: "coin",
    function: "split",
    typeArguments: ["0x2::iota::IOTA"],
    arguments: [{ GasCoin: true }, { Input: 0 }],
  },
}).toBytes());

// ============================================================
// 9. ProgrammableTransaction
// ============================================================

const ptb = {
  inputs: [
    { Pure: { bytes: Array.from(bcs.u64().serialize(1000000000n).toBytes()) } },
    { Pure: { bytes: Array.from(bcs.Address.serialize("0x" + "dd".repeat(32)).toBytes()) } },
  ],
  commands: [
    { SplitCoins: { coin: { GasCoin: true }, amounts: [{ Input: 0 }] } },
    { TransferObjects: { objects: [{ Result: 0 }], address: { Input: 1 } } },
  ],
};
vectors.programmable_transaction = toHexStr(bcs.ProgrammableTransaction.serialize(ptb).toBytes());

// ============================================================
// 10. Full TransactionData
// ============================================================

const senderAddr = "0x" + "cc".repeat(32);

const fullTxData = {
  V1: {
    kind: { ProgrammableTransaction: ptb },
    sender: senderAddr,
    gasData: {
      payment: [{
        objectId: "0x" + "ee".repeat(32),
        version: 10n,
        digest: digestBase58,
      }],
      owner: senderAddr,
      price: 1000n,
      budget: 50000000n,
    },
    expiration: { None: true },
  },
};
vectors.transaction_data_full = toHexStr(bcs.TransactionData.serialize(fullTxData).toBytes());

// With epoch expiration
const fullTxDataWithExpiry = {
  V1: {
    kind: { ProgrammableTransaction: ptb },
    sender: senderAddr,
    gasData: {
      payment: [{
        objectId: "0x" + "ee".repeat(32),
        version: 10n,
        digest: digestBase58,
      }],
      owner: senderAddr,
      price: 1000n,
      budget: 50000000n,
    },
    expiration: { Epoch: 100 },
  },
};
vectors.transaction_data_with_expiry = toHexStr(bcs.TransactionData.serialize(fullTxDataWithExpiry).toBytes());

// ============================================================
// 11. Intent message prefix
// ============================================================

vectors.intent_message_prefix = "000000";

// ============================================================
// Output
// ============================================================

console.log(JSON.stringify(vectors, null, 2));
