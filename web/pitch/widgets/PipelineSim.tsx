import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Press play, watch the whole product run.
 *
 * Six stages, and a stream of particles that visibly changes as it passes through each one:
 * ordered rows go in, the gate turns some away, noise scatters them, they re-form into a new
 * table, an attacker takes a swing at it, and a certificate drops out. Fifteen seconds, and
 * the panel has seen the entire system without a word of explanation.
 *
 * Driven by a timer rather than by frames, and every stage paints synchronously as well, so
 * it still advances on a machine where requestAnimationFrame is throttled.
 */

export type SimStage = {
  key: string
  name: string
  line: string
  tone: 'cyan' | 'yellow' | 'green' | 'coral' | 'violet' | 'red'
}

export const SIM_STAGES: SimStage[] = [
  { key: 'in', name: 'Real table', line: 'Sensitive records arrive.', tone: 'cyan' },
  { key: 'gate', name: 'Safety gate', line: 'Unsafe columns are refused before anything is read.', tone: 'red' },
  { key: 'learn', name: 'Learn + count', line: 'Every question about real people goes on the bill.', tone: 'yellow' },
  { key: 'noise', name: 'Add noise', line: 'Measured randomness. This is where privacy is bought.', tone: 'yellow' },
  { key: 'build', name: 'Build fake table', line: 'New rows from noisy counts. Costs nothing.', tone: 'green' },
  { key: 'attack', name: 'We attack it', line: 'We hunt our own output before anyone else can.', tone: 'coral' },
  { key: 'sheet', name: 'Certificate', line: 'Both numbers, signed, attached to the file.', tone: 'violet' },
]

const TONE_HEX: Record<SimStage['tone'], string> = {
  cyan: '#06bcd4',
  yellow: '#ffc93c',
  green: '#12b886',
  coral: '#ff5c39',
  violet: '#6c4cf1',
  red: '#e83b4a',
}

type Dot = { x: number; y: number; vy: number; lane: number; seed: number; dead: boolean }

function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

export function PipelineSim() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const dotsRef = useRef<Dot[]>([])
  const drawRef = useRef<null | (() => void)>(null)
  const stageRef = useRef(0)
  const [stage, setStage] = useState(0)
  const [playing, setPlaying] = useState(false)

  const build = useCallback((w: number, h: number) => {
    const rnd = mulberry(4242)
    const lanes = 9
    const dots: Dot[] = []
    for (let i = 0; i < 340; i++) {
      const lane = i % lanes
      dots.push({
        x: rnd() * w,
        y: (h / lanes) * lane + h / lanes / 2 + (rnd() - 0.5) * 4,
        vy: 0,
        lane,
        seed: rnd(),
        // The gate turns roughly one in eight away, so the refusal is visible as attrition.
        dead: rnd() < 0.12,
      })
    }
    dotsRef.current = dots
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let w = 0
    let h = 0
    let live = true
    let handle = 0
    let t = 0

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas.width = Math.round(w * dpr)
      canvas.height = Math.round(h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      build(w, h)
      drawRef.current?.()
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      const s = stageRef.current
      const hex = TONE_HEX[SIM_STAGES[s].tone]
      const lanes = 9
      const laneH = h / lanes

      for (const d of dotsRef.current) {
        // Stage 1 removes the refused rows. Everything after keeps them gone.
        if (d.dead && s >= 1) continue

        let x = d.x
        let y = (laneH * d.lane) + laneH / 2

        if (s >= 3) {
          // Noise: scatter off the lane. Stays scattered from here on, because the whole
          // point is that the downstream steps only ever see blurred values.
          const n = Math.sin(t * 1.1 + d.seed * 21) * laneH * 0.85
          const n2 = Math.cos(t * 0.9 + d.seed * 13) * 7
          y += n
          x += n2
        }
        if (s >= 4) {
          // Rebuilt into tidy rows again — a new table, not the original one.
          const target = laneH * ((Math.floor(d.seed * lanes) + 0.5))
          y += (target - y) * 0.55
        }

        const flagged = s === 5 && d.seed > 0.86
        ctx.beginPath()
        ctx.arc(x, y, flagged ? 2.6 : 1.7, 0, Math.PI * 2)
        ctx.fillStyle = flagged ? 'rgba(232,59,74,0.95)' : hex
        ctx.globalAlpha = flagged ? 1 : 0.72
        ctx.fill()
        ctx.globalAlpha = 1
      }

      // A sweep line during the attack stage: something is combing the output.
      if (s === 5) {
        const sweep = ((t * 150) % (w + 80)) - 40
        ctx.fillStyle = 'rgba(232,59,74,0.16)'
        ctx.fillRect(sweep - 22, 0, 44, h)
      }
    }

    const frame = () => {
      t += 0.016
      draw()
      if (live) handle = requestAnimationFrame(frame)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    drawRef.current = draw
    draw()
    handle = requestAnimationFrame(frame)

    const onVisible = () => {
      if (!document.hidden) draw()
    }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      live = false
      cancelAnimationFrame(handle)
      ro.disconnect()
      document.removeEventListener('visibilitychange', onVisible)
      drawRef.current = null
    }
  }, [build])

  // Advance on a timer, not on frames, so the run completes even when nothing is compositing.
  useEffect(() => {
    if (!playing) return
    const id = setInterval(() => {
      const next = stageRef.current + 1
      if (next >= SIM_STAGES.length) {
        setPlaying(false)
        return
      }
      stageRef.current = next
      setStage(next)
      drawRef.current?.()
    }, 1900)
    return () => clearInterval(id)
  }, [playing])

  const go = (n: number) => {
    stageRef.current = n
    setStage(n)
    drawRef.current?.()
  }

  const cur = SIM_STAGES[stage]
  const done = stage === SIM_STAGES.length - 1

  return (
    <div style={{ display: 'grid', gap: '0.6rem' }}>
      <div className="sim-strip">
        {SIM_STAGES.map((s, n) => (
          <button
            key={s.key}
            className="sim-step"
            data-state={n === stage ? 'here' : n < stage ? 'done' : 'ahead'}
            style={{ ['--tone' as string]: TONE_HEX[s.tone] }}
            onClick={() => {
              setPlaying(false)
              go(n)
            }}
          >
            {s.name}
          </button>
        ))}
      </div>

      <canvas
        ref={canvasRef}
        className="sim-canvas"
        style={{ display: 'block', width: '100%', height: 'clamp(120px, 20vh, 210px)' }}
        role="img"
        aria-label={`Pipeline simulation, stage ${stage + 1} of ${SIM_STAGES.length}: ${cur.name}`}
      />

      <div style={{ display: 'flex', gap: '0.7rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          className="btn btn-hot"
          data-on="1"
          onClick={() => {
            if (done) go(0)
            setPlaying((p) => !p)
          }}
        >
          {playing ? '❚❚ pause' : done ? '↻ play again' : '▶ play the whole thing'}
        </button>
        <p style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600, flex: 1, minWidth: '20ch' }}>
          <strong>{cur.name}.</strong> {cur.line}
        </p>
      </div>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span className="flag flag-illustrative">illustration</span>
        <span>A drawing of the design, not a recording of a run.</span>
      </p>
    </div>
  )
}
