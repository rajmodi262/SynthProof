/* Tests for the capsule's browser-side verifier.
 *
 * These read synthproof/capsule/verifier.js OFF DISK and evaluate it, rather than importing
 * a separately-bundled copy. That is deliberate: generator.py inlines the same file into the
 * capsule verbatim, so the bytes under test here are the bytes a third party runs. There is
 * no build step in between that could drift.
 *
 * Why these tests exist at all: on 2026-09-12 the verifier shipped with a missing `try {`
 * that stopped the whole script parsing, and underneath it a fallback that rendered a GREEN
 * "Verified" badge whenever crypto.subtle.verify returned false -- so a forged capsule
 * displayed as authentic. Both were unreachable by any test, because the logic lived inside
 * a Python f-string. The single most valuable assertion in this file is `tampered -> failed`.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { webcrypto } from 'node:crypto'

const VERIFIER = resolve(__dirname, '../../../synthproof/capsule/verifier.js')

type Verdict = {
  state: 'verified' | 'failed' | 'unverifiable'
  headline: string
  summary: string
  detail: string
}
type Decide = (payload: unknown, subtle: unknown) => Promise<Verdict>

// Evaluate the shipped source and hand back its one global.
function loadVerifier(): Decide {
  const src = readFileSync(VERIFIER, 'utf8')
  return new Function(`${src}\nreturn spDecideVerdict;`)() as Decide
}

const subtle = webcrypto.subtle

/** A real signed payload, produced here rather than hard-coded, so the fixture cannot rot. */
async function makeSignedPayload() {
  const pair = (await webcrypto.subtle.generateKey({ name: 'Ed25519' }, true, [
    'sign',
    'verify',
  ])) as CryptoKeyPair
  const signing_payload = JSON.stringify({ total_proved_eps: 1.0, mechanism: 'pairwise' })
  const sig = await webcrypto.subtle.sign(
    { name: 'Ed25519' },
    pair.privateKey,
    new TextEncoder().encode(signing_payload),
  )
  const raw = await webcrypto.subtle.exportKey('raw', pair.publicKey)
  const hex = (b: ArrayBuffer) =>
    [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('')
  return { signing_payload, signature: hex(sig), public_key: hex(raw) }
}

describe('capsule verifier', () => {
  it('accepts a genuine capsule', async () => {
    const verdict = await loadVerifier()(await makeSignedPayload(), subtle)
    expect(verdict.state).toBe('verified')
    expect(verdict.headline).toMatch(/Cryptographically Verified/)
  })

  it('REJECTS a capsule whose payload was altered after signing', async () => {
    // The defect this file exists for. Understating the privacy budget by 1000x used to
    // render green, because a false verify() result fell through to a length check.
    const payload = await makeSignedPayload()
    payload.signing_payload = payload.signing_payload.replace(
      '"total_proved_eps":1',
      '"total_proved_eps":0.001',
    )
    const verdict = await loadVerifier()(payload, subtle)
    expect(verdict.state).toBe('failed')
    expect(verdict.headline).not.toMatch(/Verified/)
    expect(verdict.summary).toMatch(/does not match/)
  })

  it('REJECTS a capsule signed by a different key', async () => {
    const a = await makeSignedPayload()
    const b = await makeSignedPayload()
    const verdict = await loadVerifier()({ ...a, public_key: b.public_key }, subtle)
    expect(verdict.state).toBe('failed')
  })

  it('reports "unverifiable", not "verified", when WebCrypto is absent', async () => {
    const verdict = await loadVerifier()(await makeSignedPayload(), null)
    expect(verdict.state).toBe('unverifiable')
    expect(verdict.headline).not.toMatch(/Verified/)
    expect(verdict.summary).toMatch(/Not checked/)
  })

  it('reports "unverifiable" when this browser has no Ed25519', async () => {
    // Chrome before 137, Firefox before 130. The old code rendered green here.
    const noEd25519 = {
      importKey: () => Promise.reject(Object.assign(new Error('nope'), { name: 'NotSupportedError' })),
      verify: () => Promise.reject(new Error('unreachable')),
    }
    const verdict = await loadVerifier()(await makeSignedPayload(), noEd25519)
    expect(verdict.state).toBe('unverifiable')
    expect(verdict.summary).toMatch(/Ed25519 unsupported/)
  })

  it('treats a malformed signature as failure, never as a pass', async () => {
    // This was the OLD pass condition, inverted: the fallback asked only whether the
    // signature was 64 bytes and then said "Verified 64-byte Ed25519 Signature".
    const payload = await makeSignedPayload()
    for (const bad of [{ ...payload, signature: 'ab'.repeat(10) }, { ...payload, public_key: 'cd' }]) {
      const verdict = await loadVerifier()(bad, subtle)
      expect(verdict.state).toBe('failed')
      expect(verdict.headline).not.toMatch(/Verified/)
    }
  })

  it('fails closed when the payload is missing entirely', async () => {
    const verdict = await loadVerifier()({}, subtle)
    expect(verdict.state).toBe('failed')
  })

  it('never returns a verified state without a signature check — exhaustive', async () => {
    // The invariant behind every case above, stated once: the only route to 'verified' is a
    // verify() that returned true. No input shape, and no absent capability, may reach it.
    const decide = loadVerifier()
    const good = await makeSignedPayload()
    const cases: Array<[string, unknown, unknown]> = [
      ['no subtle', good, null],
      ['subtle without importKey', good, {}],
      ['bad signature length', { ...good, signature: 'ff' }, subtle],
      ['bad key length', { ...good, public_key: 'ff' }, subtle],
      ['empty payload', {}, subtle],
      ['tampered bytes', { ...good, signing_payload: good.signing_payload + ' ' }, subtle],
    ]
    for (const [name, payload, s] of cases) {
      const verdict = await decide(payload, s)
      expect(verdict.state, name).not.toBe('verified')
    }
  })
})
