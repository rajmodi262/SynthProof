import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, runRelease } from './api'

/**
 * The console had no tests at all. These target `runRelease`, which hand-parses a
 * server-sent-event stream off a fetch body because the browser's EventSource cannot issue a
 * POST and the run needs a JSON body.
 *
 * That parser is the riskiest code in the frontend: a frame can straddle two network chunks,
 * and getting the buffering wrong drops pipeline stages silently — the console would simply
 * show fewer steps than ran, with no error anywhere.
 */

/** Builds a Response whose body streams the given chunks, so chunk boundaries are testable. */
function sseResponse(chunks: string[], ok = true, status = 200): Response {
  const encoder = new TextEncoder()
  let i = 0
  const body = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < chunks.length) controller.enqueue(encoder.encode(chunks[i++]))
      else controller.close()
    },
  })
  return { ok, status, body } as unknown as Response
}

const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

afterEach(() => {
  vi.restoreAllMocks()
})

describe('runRelease SSE parsing', () => {
  it('dispatches start, stage and done in order', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse([
          frame('start', { stages: ['profile', 'fit'] }),
          frame('stage', { name: 'profile' }),
          frame('stage', { name: 'fit' }),
          frame('done', { total_proved_eps: 0.91 }),
        ]),
      ),
    )

    const seen: string[] = []
    const done = vi.fn()
    runRelease({} as never, {
      onStart: () => seen.push('start'),
      onStage: (e) => seen.push(`stage:${(e as { name: string }).name}`),
      onDone: done,
    })
    await vi.waitFor(() => expect(done).toHaveBeenCalled())

    expect(seen).toEqual(['start', 'stage:profile', 'stage:fit'])
    expect(done).toHaveBeenCalledWith({ total_proved_eps: 0.91 })
  })

  it('reassembles a frame split across two chunks', async () => {
    // The case the buffer exists for. Without it this stage is dropped in silence.
    const whole = frame('stage', { name: 'audit' })
    const cut = Math.floor(whole.length / 2)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse([whole.slice(0, cut), whole.slice(cut)])),
    )

    const onStage = vi.fn()
    runRelease({} as never, { onStage })
    await vi.waitFor(() => expect(onStage).toHaveBeenCalledTimes(1))
    expect(onStage).toHaveBeenCalledWith({ name: 'audit' })
  })

  it('handles several frames arriving in one chunk', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse([frame('stage', { name: 'a' }) + frame('stage', { name: 'b' })]),
      ),
    )
    const onStage = vi.fn()
    runRelease({} as never, { onStage })
    await vi.waitFor(() => expect(onStage).toHaveBeenCalledTimes(2))
  })

  it('reports a server refusal instead of failing silently', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([], false, 422)))
    const onError = vi.fn()
    runRelease({} as never, { onError })
    await vi.waitFor(() => expect(onError).toHaveBeenCalled())
    expect(String(onError.mock.calls[0][0])).toContain('422')
  })

  it('surfaces an error frame message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse([frame('error', { message: 'budget exhausted' })])),
    )
    const onError = vi.fn()
    runRelease({} as never, { onError })
    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith('budget exhausted'))
  })

  it('skips a malformed frame rather than aborting the run', async () => {
    // One bad frame must not cost the user the rest of the pipeline.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse(['event: stage\ndata: {not json\n\n', frame('done', { ok: true })]),
      ),
    )
    const onDone = vi.fn()
    const onStage = vi.fn()
    runRelease({} as never, { onStage, onDone })
    await vi.waitFor(() => expect(onDone).toHaveBeenCalled())
    expect(onStage).not.toHaveBeenCalled()
  })

  it('returns an abort function that stops the stream quietly', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([frame('stage', { name: 'x' })])))
    const onError = vi.fn()
    const abort = runRelease({} as never, { onError })
    expect(typeof abort).toBe('function')
    abort()
    // An abort is a user action, not a failure, so it must not surface as an error.
    await new Promise((r) => setTimeout(r, 20))
    expect(onError).not.toHaveBeenCalled()
  })
})

describe('api error handling', () => {
  it('raises with the server detail when a request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        text: () => Promise.resolve('profiler exploded'),
      } as unknown as Response),
    )
    await expect(api.health()).rejects.toThrow(/profiler exploded/)
  })

  it('still raises when the server sends no detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        text: () => Promise.resolve(''),
      } as unknown as Response),
    )
    await expect(api.health()).rejects.toThrow(/503/)
  })

  it('sends requests to the /api prefix the dev proxy expects', async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) } as Response)
    vi.stubGlobal('fetch', f)
    await api.datasets()
    expect(String(f.mock.calls[0][0])).toBe('/api/datasets')
  })
})
