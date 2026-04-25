# Golden Vector Generator

These scripts generate the expected BCS serialization bytes using the official
IOTA TypeScript SDK (`@iota/iota-sdk`). The output is used by
`tests/unit/test_golden_vectors.py` to verify our Python BCS implementation
matches the official SDK byte-for-byte.

## Regenerating vectors

When the IOTA SDK updates its BCS schema, re-run these to update the expected
values:

```bash
cd tests/golden_vectors_generator
npm install @iota/iota-sdk
node generate.cjs > ../unit/golden_vectors.json

# Merge signature vectors (uses @noble/hashes via the SDK)
node generate_signature.cjs > /tmp/sig.json
node -e "
const m = JSON.parse(require('fs').readFileSync('../unit/golden_vectors.json'));
const s = JSON.parse(require('fs').readFileSync('/tmp/sig.json'));
require('fs').writeFileSync('../unit/golden_vectors.json', JSON.stringify({...m,...s}, null, 2));
"
```

Then run `pytest tests/unit/test_golden_vectors.py -v` to verify.
