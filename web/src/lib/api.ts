import type {
  AttackType,
  CertificateVerifyResult,
  DatasetOption,
  LedgerState,
  Mechanism,
  NotImplementedAttack,
  RunRequest,
  RunResult,
  StageEvent,
  StartEvent,
  TamperResult,
  UploadResult,
} from '@/types'

const BASE = '/api'

/**
 * Optional API key, injected at build time via VITE_SYNTHPROOF_API_KEY.
 *
 * The service is unauthenticated by default so the local demo needs no configuration. When a
 * deployment sets SYNTHPROOF_API_KEY, the console must send it or every data endpoint answers
 * 401. Sent as X-API-Key rather than a cookie, so there is nothing a browser attaches
 * automatically and nothing for CSRF to abuse.
 *
 * A build-time key is visible to anyone who can read the bundle. That is acceptable for a
 * console served from the same origin as the API it talks to, and unacceptable for a public
 * deployment — which would need a real login rather than a shared secret.
 */
const API_KEY = (import.meta.env?.VITE_SYNTHPROOF_API_KEY ?? '') as string

function authHeaders(init?: RequestInit): RequestInit | undefined {
  if (!API_KEY) return init
  return { ...init, headers: { ...(init?.headers ?? {}), 'X-API-Key': API_KEY } }
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, authHeaders(init))
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(detail ? `${res.status}: ${detail}` : `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () =>
    json<{
      status: string
      ledger_verified: boolean
      ledger_head: string
      mechanisms_available: string[]
    }>('/health'),

  mechanisms: () =>
    json<{ mechanisms: Mechanism[]; attacks_not_implemented: NotImplementedAttack[] }>(
      '/mechanisms',
    ),

  datasets: () => json<{ datasets: DatasetOption[] }>('/datasets'),

  ledger: () => json<LedgerState>('/ledger'),

  tamper: (entryId: string) =>
    json<{
      verified: boolean
      tampered_entry: string
      broken_from_index: number | null
      broken_count: number
      explanation: string
    }>('/ledger/tamper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId, eps_spent: 0.01, attack_type: 'modify_eps' }),
    }),

  tamperAdvanced: (attackType: AttackType, entryId?: string, epsSpent = 0.01) =>
    json<TamperResult>('/ledger/tamper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attack_type: attackType, entry_id: entryId, eps_spent: epsSpent }),
    }),

  exportCapsule: async (
    sheet: Record<string, any>,
    records?: Record<string, any>[],
    curatorName = 'SynthProof Autonomous Curator',
  ): Promise<string> => {
    const res = await fetch(
      `${BASE}/capsule/export`,
      authHeaders({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheet, records, curator_name: curatorName }),
      }),
    )
    if (!res.ok) throw new Error((await res.text()) || 'Failed to export capsule')
    return res.text()
  },

  verifyCertificate: (sheet: Record<string, any>, publicKey?: string) =>
    json<CertificateVerifyResult>('/certificate/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sheet, public_key: publicKey }),
    }),

  verifyCapsule: (htmlContent: string) =>
    json<{
      verified: boolean
      lod_safe: boolean
      lod_status: string
      proved_eps?: number
      audited_eps?: number
      audit_ceiling?: number
      dataset_name?: string
      num_rows?: number
      total_records_in_capsule?: number
      mechanism?: string
      ledger_hash?: string
      public_key?: string
      error?: string
    }>('/capsule/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html_content: htmlContent }),
    }),

  exportCroissant: (sheet: Record<string, any>) =>
    json<Record<string, any>>('/croissant/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sheet }),
    }),

  resetLedger: () => json<{ verified: boolean; head: string }>('/ledger/reset', { method: 'POST' }),

  upload: async (file: File): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/upload`, authHeaders({ method: 'POST', body: form }))
    if (!res.ok) throw new Error((await res.text()) || 'Upload failed')
    return res.json()
  },
}

export interface RunHandlers {
  onStart?: (e: StartEvent) => void
  onStage?: (e: StageEvent) => void
  onDone?: (e: RunResult) => void
  onError?: (message: string) => void
}

/**
 * Runs a release and dispatches each pipeline stage as the server completes it.
 *
 * The browser's EventSource cannot issue a POST, and the run needs a JSON body, so this
 * reads the SSE frames off a fetch stream by hand. Frames are separated by a blank line and
 * a partial frame may straddle two chunks — hence the buffer.
 *
 * Returns an abort function; calling it stops the stream but does NOT stop the server-side
 * run, which is already in flight on a worker thread.
 */
export function runRelease(req: RunRequest, handlers: RunHandlers): () => void {
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(
        `${BASE}/run`,
        authHeaders({
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          body: JSON.stringify(req),
          signal: controller.signal,
        })!,
      )

      if (!res.ok || !res.body) {
        handlers.onError?.(`Server refused the run (${res.status}).`)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let split: number
        while ((split = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, split)
          buffer = buffer.slice(split + 2)

          let event = 'message'
          const dataLines: string[] = []
          for (const line of frame.split('\n')) {
            if (line.startsWith('event: ')) event = line.slice(7).trim()
            else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
          }
          if (!dataLines.length) continue

          let payload: unknown
          try {
            payload = JSON.parse(dataLines.join('\n'))
          } catch {
            continue
          }

          if (event === 'start') handlers.onStart?.(payload as StartEvent)
          else if (event === 'stage') handlers.onStage?.(payload as StageEvent)
          else if (event === 'done') handlers.onDone?.(payload as RunResult)
          else if (event === 'error') {
            handlers.onError?.((payload as { message?: string }).message ?? 'Run failed.')
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        handlers.onError?.(
          (err as Error).message ||
            'Could not reach the API. Is uvicorn running on port 8000?',
        )
      }
    }
  })()

  return () => controller.abort()
}
