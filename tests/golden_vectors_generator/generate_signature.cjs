/**
 * Generate a signature golden vector.
 *
 * Uses a deterministic Ed25519 keypair (seed = 0x00..0x1f) to sign
 * known transaction data, so the Python tests can reproduce the
 * exact same signature.
 */

const { bcs } = require('@iota/iota-sdk/bcs');
const { toBase58 } = require('@iota/bcs');
const { Ed25519Keypair } = require('@iota/iota-sdk/keypairs/ed25519');
const { blake2b } = require('@noble/hashes/blake2b');

function toHexStr(bytes) {
  return Buffer.from(bytes).toString('hex');
}

const vectors = {};

// Deterministic seed: bytes 0x00..0x1f
const seed = Buffer.alloc(32);
for (let i = 0; i < 32; i++) seed[i] = i;

// Create keypair from seed
const keypair = Ed25519Keypair.fromSecretKey(seed);
vectors.ed25519_public_key = toHexStr(keypair.getPublicKey().toRawBytes());

// IOTA address: Blake2b-256(public_key) -- no flag prefix for Ed25519
const pubkeyBytes = keypair.getPublicKey().toRawBytes();
const addressBytes = blake2b(pubkeyBytes, { dkLen: 32 });
vectors.ed25519_address = "0x" + toHexStr(addressBytes);

// Build a known TransactionData (same as in generate.cjs)
const digestBytes = new Uint8Array(32);
for (let i = 0; i < 32; i++) digestBytes[i] = i;
const digestBase58 = toBase58(digestBytes);

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

const txDataBcs = bcs.TransactionData.serialize(fullTxData).toBytes();
vectors.tx_data_bcs = toHexStr(txDataBcs);

// Intent message: [0, 0, 0] + tx_data_bcs
const intentPrefix = new Uint8Array([0, 0, 0]);
const intentMessage = new Uint8Array(intentPrefix.length + txDataBcs.length);
intentMessage.set(intentPrefix);
intentMessage.set(txDataBcs, intentPrefix.length);

// Blake2b-256 hash of intent message
const intentHash = blake2b(intentMessage, { dkLen: 32 });
vectors.intent_hash = toHexStr(intentHash);

// Sign the hash (async in this SDK version)
async function run() {
  const signature = await keypair.sign(intentHash);
  vectors.ed25519_signature = toHexStr(signature);

  // Serialized signature: flag(0x00) || signature(64) || public_key(32) -> base64
  const serialized = new Uint8Array(1 + 64 + 32);
  serialized[0] = 0x00; // Ed25519 flag
  serialized.set(signature, 1);
  serialized.set(pubkeyBytes, 65);
  vectors.serialized_signature_bytes = toHexStr(serialized);
  vectors.serialized_signature_base64 = Buffer.from(serialized).toString('base64');

  console.log(JSON.stringify(vectors, null, 2));
}

run();
