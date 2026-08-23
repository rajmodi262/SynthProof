/**
 * The particle field — the one idea this deck is built on.
 *
 * Roughly 2,600 gold particles exist for the whole talk and are never destroyed. They
 * REARRANGE: they spell the project name, scatter into a crowd, condense into two tables,
 * stream through the pipeline, compact into a certificate, and finally settle into the
 * closing line.
 *
 * So the transitions are not decoration. The same points the room watched become a person,
 * become a leak, become the product. The data is a character in the story, and the audience
 * follows it without being told to.
 *
 * Everything is deliberately plain Canvas 2D and plain arithmetic:
 *   - No WebGL, so there is no GPU context to lose on an unfamiliar projector.
 *   - Physics is separate from painting, so an interaction can settle the system to its final
 *     state and paint once. requestAnimationFrame is throttled to nothing whenever the page
 *     is not compositing, and a deck whose centrepiece freezes half-formed is a lost viva.
 */

export type Shape =
  | { kind: 'word'; text: string; clarity: number }
  | { kind: 'crowd'; survivorsFrac: number; found: boolean }
  | { kind: 'tables'; leakRow: number | null }
  | { kind: 'pipeline'; stage: number }
  | { kind: 'label' }
  | { kind: 'close'; text: string }

export type Particle = {
  x: number
  y: number
  /** Target. */
  tx: number
  ty: number
  /** 0..1 personal randomness, stable for the whole talk. */
  seed: number
  /** 0 = normal gold, 1 = flagged crimson. */
  hot: number
  /** 0 = fully present, 1 = dimmed out (filtered away, refused, etc). */
  faded: number
}

export const COUNT = 2600

export function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

/** Samples the lit pixels of rendered text, so particles can spell something. */
function textPoints(text: string, w: number, h: number, fill = 0.62): Array<[number, number]> {
  const off = document.createElement('canvas')
  off.width = Math.max(1, Math.floor(w))
  off.height = Math.max(1, Math.floor(h))
  const c = off.getContext('2d')!
  let size = Math.floor(h * fill)
  c.textBaseline = 'middle'
  for (; size > 8; size -= 2) {
    c.font = `900 ${size}px "Geist Sans", system-ui, sans-serif`
    if (c.measureText(text).width <= w * 0.92) break
  }
  const tw = c.measureText(text).width
  c.fillStyle = '#fff'
  c.fillText(text, (w - tw) / 2, h / 2)

  const img = c.getImageData(0, 0, off.width, off.height).data
  const pts: Array<[number, number]> = []
  const step = Math.max(2, Math.round(Math.sqrt((w * h * 0.15) / COUNT)))
  for (let y = 0; y < off.height; y += step) {
    for (let x = 0; x < off.width; x += step) {
      if (img[(y * off.width + x) * 4 + 3] > 128) pts.push([x, y])
    }
  }
  return pts
}

/** Points laid out as `rows` tidy table rows inside a box — used for the tables shape. */
function tableRows(x0: number, y0: number, bw: number, bh: number, rows: number, n: number) {
  const pts: Array<[number, number]> = []
  const perRow = Math.max(1, Math.floor(n / rows))
  const rowH = bh / rows
  for (let r = 0; r < rows; r++) {
    for (let i = 0; i < perRow; i++) {
      pts.push([x0 + (i / perRow) * bw, y0 + rowH * (r + 0.5)])
    }
  }
  return pts
}

/**
 * Assigns every particle a target for the given shape. Targets are assigned by INDEX rather
 * than by nearest-neighbour: it is cheap, deterministic, and the resulting criss-cross as the
 * field re-forms reads better than a tidy radial collapse.
 */
export function retarget(ps: Particle[], shape: Shape, w: number, h: number) {
  const rnd = mulberry(20260818)

  const assign = (pts: Array<[number, number]>) => {
    if (!pts.length) return
    for (let i = 0; i < ps.length; i++) {
      const [x, y] = pts[i % pts.length]
      // A little jitter so repeated points in a short list do not stack into a hard dot.
      ps[i].tx = x + (rnd() - 0.5) * 2.5
      ps[i].ty = y + (rnd() - 0.5) * 2.5
    }
  }

  switch (shape.kind) {
    case 'word': {
      const pts = textPoints(shape.text, w, h * 0.62, 0.78)
      const dy = h * 0.16
      assign(pts.map(([x, y]) => [x, y + dy] as [number, number]))
      // Clarity 0 blows the word apart into noise; 1 leaves it crisp.
      const spread = (1 - shape.clarity) * (1 - shape.clarity) * Math.min(w, h) * 0.6
      for (const p of ps) {
        const a = p.seed * Math.PI * 2
        p.tx += Math.cos(a) * spread
        p.ty += Math.sin(a) * spread * 0.7
        p.hot = 0
        p.faded = 0
      }
      break
    }

    case 'crowd': {
      for (let i = 0; i < ps.length; i++) {
        const p = ps[i]
        const r = mulberry(i * 7919 + 13)
        p.tx = r() * w
        p.ty = h * 0.12 + r() * h * 0.76
        const survives = p.seed < shape.survivorsFrac
        p.faded = survives ? 0 : 1
        p.hot = 0
      }
      // The survivor: one particle, centre-right, burning.
      const hero = ps[ps.length - 1]
      hero.tx = w * 0.5
      hero.ty = h * 0.46
      hero.faded = 0
      hero.hot = shape.found ? 1 : 0
      break
    }

    case 'tables': {
      const bw = w * 0.36
      const gap = w * 0.1
      const x0 = (w - (bw * 2 + gap)) / 2
      const left = tableRows(x0, h * 0.2, bw, h * 0.56, 6, ps.length / 2)
      const right = tableRows(x0 + bw + gap, h * 0.2, bw, h * 0.56, 6, ps.length / 2)
      const all = [...left, ...right]
      assign(all)
      const rowH = (h * 0.56) / 6
      for (const p of ps) {
        p.faded = 0
        // Light the leaking row on the right-hand table.
        const inRight = p.tx > x0 + bw + gap * 0.5
        const row = Math.floor((p.ty - h * 0.2) / rowH)
        p.hot = shape.leakRow !== null && inRight && row === shape.leakRow ? 1 : 0
      }
      break
    }

    case 'pipeline': {
      const lanes = 7
      const laneH = (h * 0.62) / lanes
      const top = h * 0.19
      for (let i = 0; i < ps.length; i++) {
        const p = ps[i]
        const r = mulberry(i * 104729 + 7)
        const lane = i % lanes
        p.tx = r() * w
        p.ty = top + laneH * (lane + 0.5)
        p.hot = 0
        // Stage 1 is the gate: roughly one row in eight is refused and dims out.
        p.faded = shape.stage >= 1 && p.seed > 0.88 ? 1 : 0
        // Stage 2 is the noise: the tidy lanes break up.
        if (shape.stage >= 2) {
          p.ty += (r() - 0.5) * laneH * 4.2
          p.tx += (r() - 0.5) * 26
        }
        // Stage 3 rebuilds a NEW table — tidy again, but not the rows we started with.
        if (shape.stage >= 3) {
          const newLane = Math.floor(r() * lanes)
          p.ty = top + laneH * (newLane + 0.5)
        }
        // Stage 4 is the self-attack: a few get flagged and inspected.
        if (shape.stage >= 4 && p.seed > 0.93) p.hot = 1
      }
      break
    }

    case 'label': {
      // A dense block, like a printed panel.
      const bw = w * 0.3
      const bh = h * 0.62
      const x0 = w * 0.08
      const y0 = h * 0.19
      for (let i = 0; i < ps.length; i++) {
        const p = ps[i]
        const r = mulberry(i * 15486071 + 3)
        p.tx = x0 + r() * bw
        p.ty = y0 + r() * bh
        p.hot = 0
        p.faded = 0
      }
      break
    }

    case 'close': {
      const pts = textPoints(shape.text, w, h * 0.5, 0.5)
      assign(pts.map(([x, y]) => [x, y + h * 0.22] as [number, number]))
      for (const p of ps) {
        p.hot = 0
        p.faded = 0
      }
      break
    }
  }
}

export function makeParticles(w: number, h: number): Particle[] {
  const rnd = mulberry(90210)
  const ps: Particle[] = []
  for (let i = 0; i < COUNT; i++) {
    const x = rnd() * w
    const y = rnd() * h
    ps.push({ x, y, tx: x, ty: y, seed: rnd(), hot: 0, faded: 0 })
  }
  return ps
}

/** One physics tick. Kept separate from painting so interactions can settle instantly. */
export function step(ps: Particle[]) {
  for (const p of ps) {
    p.x += (p.tx - p.x) * 0.11
    p.y += (p.ty - p.y) * 0.11
  }
}

export function paint(ctx: CanvasRenderingContext2D, ps: Particle[], w: number, h: number, t: number) {
  ctx.clearRect(0, 0, w, h)
  for (const p of ps) {
    const drift = Math.sin(t * 0.55 + p.seed * 11) * 0.7
    const a = p.faded > 0.5 ? 0.09 : 0.72 + p.seed * 0.28
    const r = p.hot > 0.5 ? 2.6 : 1.15 + p.seed * 1.15

    if (p.hot > 0.5) {
      const pulse = 0.7 + Math.sin(t * 3.2) * 0.3
      ctx.beginPath()
      ctx.arc(p.x, p.y + drift, r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(226,88,64,${pulse})`
      ctx.shadowColor = 'rgba(226,88,64,0.95)'
      ctx.shadowBlur = 18
      ctx.fill()
      ctx.shadowBlur = 0
      continue
    }

    ctx.beginPath()
    ctx.arc(p.x, p.y + drift, r, 0, Math.PI * 2)
    ctx.fillStyle = p.faded > 0.5 ? `rgba(146,124,86,${a})` : `rgba(232,186,102,${a})`
    ctx.fill()
  }
}
