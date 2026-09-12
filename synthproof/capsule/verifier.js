/* SynthProof capsule verifier — the single source of truth for browser-side verification.
 *
 * WHY THIS IS A FILE. This logic used to live as a string literal inside an f-string in
 * generator.py, where no linter, type checker or test could reach it. Two defects shipped
 * that way on 2026-09-12: a missing `try {` that stopped the whole script parsing, so the
 * badge never left "VERIFYING PROOF...", and underneath it a fallback that painted the badge
 * green whenever `crypto.subtle.verify` returned false — meaning a forged capsule displayed
 * as verified. Neither could have survived a test, and neither was reachable by one.
 *
 * It is a plain script, not a module, and defines exactly one global. generator.py inlines
 * this file verbatim into the capsule's <script> block, and the vitest suite reads the same
 * bytes off disk and evaluates them. So the thing under test is literally the thing that
 * ships; there is no build step between them to drift.
 *
 * THREE OUTCOMES, NEVER TWO. A capsule is verified, refuted, or unverifiable-here, and the
 * third is not a pass. "We could not check" must never render as "we checked and it passed".
 */

/**
 * Decide a capsule's verdict. Pure: no DOM, no globals, no I/O.
 *
 * @param {object} payload  the capsule's embedded payload; needs `signature`, `public_key`
 *                          (hex or base64) and `signing_payload` (the canonical bytes signed).
 * @param {SubtleCrypto|null|undefined} subtle  a WebCrypto SubtleCrypto, or null when the
 *                          host has none. Injected rather than read off `globalThis` so the
 *                          unverifiable paths are reachable from a test.
 * @returns {Promise<{state:'verified'|'failed'|'unverifiable', headline:string,
 *                    summary:string, detail:string}>}
 */
async function spDecideVerdict(payload, subtle) {
  function toBytes(str) {
    if (!str) return new Uint8Array(0);
    if (/^[0-9a-fA-F]+$/.test(str) && str.length % 2 === 0) {
      var arr = new Uint8Array(str.length / 2);
      for (var i = 0; i < str.length; i += 2) arr[i / 2] = parseInt(str.substr(i, 2), 16);
      return arr;
    }
    try {
      return Uint8Array.from(atob(str), function (c) { return c.charCodeAt(0); });
    } catch (e) {
      return new TextEncoder().encode(str);
    }
  }

  try {
    var sigBytes = toBytes(payload && payload.signature);
    var keyBytes = toBytes(payload && payload.public_key);
    var dataBytes = new TextEncoder().encode((payload && payload.signing_payload) || '');

    // A malformed signature or key is a FAILURE. In the version this replaces it was the
    // pass condition: the fallback asked only "is it 64 bytes" and then said "Verified".
    if (sigBytes.length !== 64 || keyBytes.length !== 32) {
      return {
        state: 'failed',
        headline: '✗ Verification Failed',
        summary: '✗ Malformed signature or public key',
        detail:
          'This capsule does not carry a well-formed Ed25519 signature. Expected 64 ' +
          'signature bytes and a 32-byte key; found ' + sigBytes.length + ' and ' +
          keyBytes.length + '.',
      };
    }

    if (!subtle || !subtle.importKey) {
      // No WebCrypto in this context at all — typically a non-secure origin, such as a
      // data: URL. Nothing has been checked, and the verdict says so.
      return {
        state: 'unverifiable',
        headline: '⚠ Cannot Verify In This Browser',
        summary: '⚠ Not checked — WebCrypto unavailable',
        detail:
          'This page has no WebCrypto in the current context, so the signature could not ' +
          'be checked. Nothing here has been verified. Open the capsule over https:// or ' +
          'localhost, or check it with: synthproof verify-capsule.',
      };
    }

    var key;
    try {
      key = await subtle.importKey('raw', keyBytes, { name: 'Ed25519' }, false, ['verify']);
    } catch (e) {
      // The ONLY outcome that is neither a pass nor a refutation: this host's WebCrypto
      // does not implement Ed25519. Chrome before 137 and Firefox before 130 land here.
      return {
        state: 'unverifiable',
        headline: '⚠ Cannot Verify In This Browser',
        summary: '⚠ Not checked — Ed25519 unsupported here',
        detail:
          "This browser's WebCrypto does not implement Ed25519, so the signature could " +
          'not be checked. Nothing here has been verified. Use a current Chrome, Firefox ' +
          'or Safari, or check it with: synthproof verify-capsule.',
      };
    }

    // From here a false result is a refutation, not a reason to try something weaker.
    var valid = await subtle.verify({ name: 'Ed25519' }, key, sigBytes, dataBytes);
    if (valid) {
      return {
        state: 'verified',
        headline: '✓ Cryptographically Verified',
        summary: '✓ Authentic Ed25519 Signature',
        detail:
          'Verified. The embedded Privacy Data Sheet carries a valid Ed25519 signature ' +
          'over its canonical bytes and has not been altered since it was signed.\n\n' +
          'This proves authorship and integrity. It does NOT prove the epsilon is ' +
          'correct: a key holder can sign a sheet saying anything.',
      };
    }
    return {
      state: 'failed',
      headline: '✗ Verification Failed',
      summary: '✗ Signature does not match this payload',
      detail:
        'REJECTED. The signature does not verify against this payload. Either the capsule ' +
        'was altered after signing, or it was not signed by this key.',
    };
  } catch (err) {
    // Fail closed. Anything unexpected is a failure, never a downgrade to a weaker check.
    return {
      state: 'failed',
      headline: '✗ Verification Failed',
      summary: '✗ Signature / Payload Mismatch',
      detail: 'Verification failed: ' + (err && err.message ? err.message : String(err)),
    };
  }
}
