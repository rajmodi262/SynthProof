import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import katex from 'katex'
import { AnimatePresence, motion } from 'framer-motion'
import { EChart } from './charts/EChart'
import { EXPLAINERS } from '@/explainers/explainers'
import type { Cloud, Point3 } from '@/types'
import type { EChartsOption } from 'echarts'

export type CloudLayer = 'both' | 'real' | 'synthetic'
export type CameraView = 'orbit' | 'top' | 'side' | 'cinematic'
export type InspectionMode = 'both' | 'real' | 'synthetic' | 'canaries' | 'split'

interface PrivacyChamberProps {
  cloud: Cloud | null
  layer: CloudLayer
  showCanaries: boolean
  showLinks: boolean
  running: boolean
  currentStage?: string | null
  onLayerChange?: (layer: CloudLayer) => void
  onToggleCanaries?: (show: boolean) => void
  onToggleLinks?: (show: boolean) => void
  onPointClick?: (pointType: 'real' | 'synthetic' | 'canary') => void
}

/** Theme-Adaptive High-Contrast Color Palette for Unmistakable Distinction */
export const PALETTE = {
  dark: {
    real: new THREE.Color('#38BDF8'),       // Electric Sky Blue (#38BDF8)
    realHex: '#38BDF8',
    realGlow: 'rgba(56, 189, 248, 0.4)',
    synth: new THREE.Color('#FACC15'),      // Radiant Bright Yellow (#FACC15)
    synthHex: '#FACC15',
    synthGlow: 'rgba(250, 204, 21, 0.4)',
    canary: new THREE.Color('#FF2E55'),     // Laser Crimson Red (#FF2E55)
    canaryHex: '#FF2E55',
    canaryGlow: 'rgba(255, 46, 85, 0.5)',
    grid: '#8A5A2B',
    gridFloor: '#2A241B',
    beam: '#FF2E55',
    scanner: new THREE.Color('#38BDF8'),
  },
  light: {
    real: new THREE.Color('#0284C7'),       // Rich Cobalt Blue
    realHex: '#0284C7',
    realGlow: 'rgba(2, 132, 199, 0.3)',
    synth: new THREE.Color('#EAB308'),      // Bright Golden Yellow
    synthHex: '#EAB308',
    synthGlow: 'rgba(234, 179, 8, 0.3)',
    canary: new THREE.Color('#DC2626'),     // Vivid Crimson Red
    canaryHex: '#DC2626',
    canaryGlow: 'rgba(220, 38, 38, 0.4)',
    grid: '#8A5A2B',
    gridFloor: '#DED6C7',
    beam: '#DC2626',
    scanner: new THREE.Color('#C08A4E'),
  },
}

const CAPACITY = 6000

/** Hook to detect active dark mode */
function useIsDarkMode() {
  const [isDark, setIsDark] = useState(() => {
    if (typeof document === 'undefined') return true
    return document.documentElement.getAttribute('data-theme') !== 'light'
  })

  useEffect(() => {
    const checkTheme = () => {
      setIsDark(document.documentElement.getAttribute('data-theme') !== 'light')
    }
    const observer = new MutationObserver(checkTheme)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] })
    return () => observer.disconnect()
  }, [])

  return isDark
}

/** Generates smooth circular antialiased point particle texture */
function useCircleParticleTexture() {
  return useMemo(() => {
    if (typeof document === 'undefined') return null
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 64
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.clearRect(0, 0, 64, 64)
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 30)
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)')
    gradient.addColorStop(0.85, 'rgba(255, 255, 255, 0.95)')
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')
    ctx.fillStyle = gradient
    ctx.beginPath()
    ctx.arc(32, 32, 30, 0, Math.PI * 2)
    ctx.fill()
    const tex = new THREE.CanvasTexture(canvas)
    tex.needsUpdate = true
    return tex
  }, [])
}

/** Reliably projected point cloud layer with direct buffer allocation */
function PointCloudLayer({
  points,
  color,
  size,
  opacity,
  visible,
  offsetX = 0,
  texture,
  onClick,
}: {
  points: Point3[]
  color: THREE.Color
  size: number
  opacity: number
  visible: boolean
  offsetX?: number
  texture?: THREE.Texture | null
  onClick?: () => void
}) {
  const geomRef = useRef<THREE.BufferGeometry>(null)
  const count = Math.min(points.length, CAPACITY)

  const positions = useMemo(() => {
    const out = new Float32Array(count * 3)
    if (!points || !points.length) return out
    for (let i = 0; i < count; i++) {
      const p = points[i % points.length]
      out[i * 3] = p[0] + offsetX
      out[i * 3 + 1] = p[1]
      out[i * 3 + 2] = p[2]
    }
    return out
  }, [points, count, offsetX])

  useEffect(() => {
    if (geomRef.current && count > 0) {
      geomRef.current.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      geomRef.current.computeBoundingSphere()
    }
  }, [positions, count])

  if (!visible || count === 0) return null

  return (
    <points
      visible={visible}
      onClick={(e) => {
        e.stopPropagation()
        onClick?.()
      }}
    >
      <bufferGeometry ref={geomRef}>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        color={color}
        map={texture || undefined}
        transparent
        opacity={Math.max(0.75, Math.min(1, opacity))}
        sizeAttenuation={true}
        depthWrite={false}
      />
    </points>
  )
}

/** Sweeping volumetric audit laser scanning the coordinate space */
function LaserAuditScanner({ active, color }: { active: boolean; color: THREE.Color }) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const t = clock.getElapsedTime()
    meshRef.current.position.y = Math.sin(t * 1.5) * 2.2
  })

  if (!active) return null

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[10, 10]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.09}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}

/** 3D Adversarial Canary Probes with Solid Core, Vertical Drop Stem, and Concentric Radar Pulses */
function CanaryProbes({
  points,
  color,
  visible,
  offsetX = 0,
  onClick,
}: {
  points: Point3[]
  color: THREE.Color
  visible: boolean
  offsetX?: number
  onClick?: () => void
}) {
  const groupRef = useRef<THREE.Group>(null)

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    const pulseScale = 1 + Math.sin(t * 4.0) * 0.35
    groupRef.current.children.forEach((child) => {
      const ring = child.getObjectByName('radarRing')
      if (ring) {
        ring.scale.set(pulseScale, pulseScale, pulseScale)
      }
    })
  })

  if (!visible || !points.length) return null

  return (
    <group ref={groupRef}>
      {points.slice(0, 50).map((p, idx) => {
        const x = p[0] + offsetX
        const y = p[1]
        const z = p[2]
        return (
          <group
            key={idx}
            position={[x, y, z]}
            onClick={(e) => {
              e.stopPropagation()
              onClick?.()
            }}
          >
            {/* Solid glowing central core sphere */}
            <mesh>
              <sphereGeometry args={[0.095, 16, 16]} />
              <meshBasicMaterial color={color} />
            </mesh>

            {/* Glowing outer halo */}
            <mesh>
              <sphereGeometry args={[0.13, 16, 16]} />
              <meshBasicMaterial color={color} transparent opacity={0.3} depthWrite={false} />
            </mesh>

            {/* Concentric pulsing radar sonar ring */}
            <mesh name="radarRing" rotation={[-Math.PI / 2, 0, 0]}>
              <ringGeometry args={[0.16, 0.22, 32]} />
              <meshBasicMaterial
                color={color}
                side={THREE.DoubleSide}
                transparent
                opacity={0.75}
                depthWrite={false}
              />
            </mesh>

            {/* Vertical laser drop line down to the chamber floor */}
            <lineSegments>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  count={2}
                  array={new Float32Array([0, 0, 0, 0, -2.4 - y, 0])}
                  itemSize={3}
                />
              </bufferGeometry>
              <lineBasicMaterial color={color} transparent opacity={0.35} linewidth={1} />
            </lineSegments>

            {/* Floor landing reticle */}
            <mesh position={[0, -2.39 - y, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <ringGeometry args={[0.08, 0.12, 16]} />
              <meshBasicMaterial color={color} transparent opacity={0.4} side={THREE.DoubleSide} />
            </mesh>
          </group>
        )
      })}
    </group>
  )
}

/** Nearest-neighbor attack affinity lines connecting each canary to its nearest synthetic record */
function NearestMatchLinks({
  cloud,
  visible,
  color,
  offsetXCanary = 0,
  offsetXSynth = 0,
}: {
  cloud: Cloud | null
  visible: boolean
  color: string
  offsetXCanary?: number
  offsetXSynth?: number
}) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    if (!cloud?.canaries.length || !cloud.synthetic.length) return g

    const positions: number[] = []
    const canaries = cloud.canaries.slice(0, 50)
    for (const c of canaries) {
      let best = Infinity
      let closest: Point3 = cloud.synthetic[0]
      for (const s of cloud.synthetic) {
        const d = (c[0] - s[0]) ** 2 + (c[1] - s[1]) ** 2 + (c[2] - s[2]) ** 2
        if (d < best) {
          best = d
          closest = s
        }
      }
      positions.push(
        c[0] + offsetXCanary,
        c[1],
        c[2],
        closest[0] + offsetXSynth,
        closest[1],
        closest[2]
      )
    }

    g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return g
  }, [cloud, offsetXCanary, offsetXSynth])

  if (!visible || !cloud?.canaries.length || !cloud.synthetic.length) return null

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color={color} transparent opacity={0.65} linewidth={1.5} />
    </lineSegments>
  )
}

/** Side-by-Side Split Divider Hologram */
function SplitDividerPlane({ visible }: { visible: boolean }) {
  if (!visible) return null

  return (
    <group position={[0, 0, 0]}>
      {/* Translucent partition plane */}
      <mesh rotation={[0, Math.PI / 2, 0]}>
        <planeGeometry args={[10, 5]} />
        <meshBasicMaterial
          color="#38BDF8"
          transparent
          opacity={0.06}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      {/* Central glowing vertical laser divider */}
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([0, -2.4, -4, 0, 2.5, -4])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#38BDF8" transparent opacity={0.6} />
      </lineSegments>
    </group>
  )
}

/** Engineered coordinate stage bounding box & measurement axes */
function MeasurementBoundingBox({ gridSubColor }: { gridSubColor: string }) {
  return (
    <group>
      {/* Floor Grid */}
      <group position={[0, -2.4, 0]}>
        <gridHelper args={[14, 28, '#8A5A2B', gridSubColor]} />
      </group>
      {/* Measurement Cage */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(12, 4.8, 8)]} />
        <lineBasicMaterial color="#8A5A2B" transparent opacity={0.16} />
      </lineSegments>
    </group>
  )
}

function CameraRig({
  view,
  orbitActive,
}: {
  view: CameraView
  orbitActive: boolean
}) {
  const { camera } = useThree()

  useEffect(() => {
    if (view === 'top') {
      camera.position.set(0, 11, 0)
      camera.lookAt(0, 0, 0)
    } else if (view === 'side') {
      camera.position.set(11, 0, 0)
      camera.lookAt(0, 0, 0)
    } else if (view === 'cinematic') {
      camera.position.set(6.5, 3.2, 7.5)
      camera.lookAt(0, 0, 0)
    } else {
      camera.position.set(5.2, 3.4, 6.2)
      camera.lookAt(0, 0, 0)
    }
  }, [view, camera])

  return (
    <OrbitControls
      minDistance={2}
      maxDistance={22}
      autoRotate={orbitActive || view === 'cinematic'}
      autoRotateSpeed={view === 'cinematic' ? 0.75 : 0.3}
      enableDamping
      dampingFactor={0.05}
    />
  )
}

/** 2D Fallback Scatter Chart via ECharts with High-Contrast Colors */
function Fallback2DScatter({
  cloud,
  layer,
  showCanaries,
  palette,
  onPointClick,
}: {
  cloud: Cloud | null
  layer: CloudLayer
  showCanaries: boolean
  palette: typeof PALETTE['dark']
  onPointClick?: (type: 'real' | 'synthetic' | 'canary') => void
}) {
  const option: EChartsOption = useMemo(() => {
    const series: any[] = []

    if (cloud && (layer === 'both' || layer === 'real')) {
      series.push({
        name: 'Real sensitive record',
        type: 'scatter',
        symbolSize: 6,
        data: cloud.real.map((p) => [p[0], p[1]]),
        itemStyle: { color: palette.realHex, opacity: 0.8 },
      })
    }

    if (cloud && (layer === 'both' || layer === 'synthetic')) {
      series.push({
        name: 'DP synthetic cloud',
        type: 'scatter',
        symbolSize: 6,
        data: cloud.synthetic.map((p) => [p[0], p[1]]),
        itemStyle: { color: palette.synthHex, opacity: 0.85 },
      })
    }

    if (cloud && showCanaries) {
      series.push({
        name: 'Adversarial canary decoy',
        type: 'scatter',
        symbolSize: 12,
        data: cloud.canaries.map((p) => [p[0], p[1]]),
        itemStyle: { color: palette.canaryHex, opacity: 1.0 },
      })
    }

    return {
      grid: { left: 40, right: 30, top: 40, bottom: 40 },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => `<strong>${params.seriesName}</strong><br/>PCA: [${params.value[0]?.toFixed(2)}, ${params.value[1]?.toFixed(2)}]`,
      },
      legend: {
        textStyle: { color: '#8A5A2B', fontFamily: 'monospace' },
        top: 10,
      },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: palette.gridFloor } } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: palette.gridFloor } } },
      series,
    }
  }, [cloud, layer, showCanaries, palette])

  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-4">
      <div className="mb-2 font-mono text-xs text-muted">
        2D Dimensionality Projection (Orthogonal PCA)
      </div>
      <div className="h-full w-full">
        <EChart
          option={option}
          className="h-full w-full"
          onEvents={{
            click: (params: any) => {
              if (params.seriesName?.includes('Real')) onPointClick?.('real')
              else if (params.seriesName?.includes('synthetic')) onPointClick?.('synthetic')
              else if (params.seriesName?.includes('canary')) onPointClick?.('canary')
            },
          }}
        />
      </div>
    </div>
  )
}

export type PresentationChapter = 1 | 2 | 3 | 4 | 5

interface ChapterInfo {
  num: PresentationChapter
  title: string
  blurb: string
  explainerKey: string
  layer: CloudLayer
  canaries: boolean
  links: boolean
  scanner: boolean
  blend: number // 0 = 100% real, 1 = 100% synth
}

const CHAPTERS: ChapterInfo[] = [
  {
    num: 1,
    title: '1. The Sensitive Manifold',
    blurb: 'High-dimensional geometry of sensitive training records projected via fitted PCA (Cyan points).',
    explainerKey: 'boundary',
    layer: 'real',
    canaries: false,
    links: false,
    scanner: false,
    blend: 0,
  },
  {
    num: 2,
    title: '2. Adversarial Canaries',
    blurb: 'Extreme outlier decoy records (Crimson probes) planted into training data to calibrate empirical leakage bounds.',
    explainerKey: 'canary',
    layer: 'real',
    canaries: true,
    links: false,
    scanner: false,
    blend: 0,
  },
  {
    num: 3,
    title: '3. Differential Privacy Dissolve',
    blurb: 'Calibrated noise dissolves private data points while preserving statistical interactions in the synthetic cloud (Amber points).',
    explainerKey: 'aim',
    layer: 'both',
    canaries: true,
    links: false,
    scanner: false,
    blend: 0.5,
  },
  {
    num: 4,
    title: '4. Leakage Verification Vectors',
    blurb: 'Testing whether nearest-neighbor attack vectors (Crimson laser beams) can distinguish decoys from synthetic records.',
    explainerKey: 'ceiling',
    layer: 'both',
    canaries: true,
    links: true,
    scanner: true,
    blend: 0.8,
  },
  {
    num: 5,
    title: '5. Certified Equilibrium',
    blurb: 'Tamper-evident release state with bounded leakage proof and certified audit ceiling.',
    explainerKey: 'epsilon',
    layer: 'both',
    canaries: true,
    links: true,
    scanner: false,
    blend: 1,
  },
]

export function PrivacyChamber({
  cloud,
  layer,
  showCanaries,
  showLinks,
  running,
  currentStage,
  onLayerChange,
  onToggleCanaries,
  onToggleLinks,
  onPointClick,
}: PrivacyChamberProps) {
  const isDarkMode = useIsDarkMode()
  const palette = isDarkMode ? PALETTE.dark : PALETTE.light
  const circleTexture = useCircleParticleTexture()

  const [view, setView] = useState<CameraView>('orbit')
  const [orbitActive, setOrbitActive] = useState(true)
  const [webGlSupported, setWebGlSupported] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [scannerActive, setScannerActive] = useState(false)
  const [show3dBadges, setShow3dBadges] = useState(true)

  // Inspection mode: 'both' | 'real' | 'synthetic' | 'canaries' | 'split'
  const [inspectionMode, setInspectionMode] = useState<InspectionMode>('both')

  // Interactive Density Crossfader: 0 = 100% Real, 1 = 100% Synthetic
  const [blendRatio, setBlendRatio] = useState<number>(0.5)

  // Presentation Chapter Walkthrough State
  const [activeChapter, setActiveChapter] = useState<PresentationChapter | null>(null)

  // Inspected point state for tooltip
  const [inspectedDetail, setInspectedDetail] = useState<{
    type: 'real' | 'synthetic' | 'canary'
    title: string
    color: string
    count: number
    description: string
  } | null>(null)

  // Keyboard shortcut: ESC to exit fullscreen, F to toggle fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false)
      } else if ((e.key === 'f' || e.key === 'F') && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        setIsFullscreen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isFullscreen])

  function selectChapter(ch: ChapterInfo) {
    setActiveChapter(ch.num)
    setInspectionMode('both')
    onLayerChange?.(ch.layer)
    onToggleCanaries?.(ch.canaries)
    onToggleLinks?.(ch.links)
    setScannerActive(ch.scanner)
    setBlendRatio(ch.blend)
  }

  function handleInspectionModeChange(mode: InspectionMode) {
    setInspectionMode(mode)
    if (mode === 'real') {
      onLayerChange?.('real')
      onToggleCanaries?.(false)
    } else if (mode === 'synthetic') {
      onLayerChange?.('synthetic')
      onToggleCanaries?.(false)
    } else if (mode === 'canaries') {
      onLayerChange?.('both')
      onToggleCanaries?.(true)
      onToggleLinks?.(true)
    } else if (mode === 'split') {
      onLayerChange?.('both')
      onToggleCanaries?.(true)
      onToggleLinks?.(false)
    } else {
      // 'both'
      onLayerChange?.('both')
      onToggleCanaries?.(true)
    }
  }

  const explainedVariance = useMemo(() => {
    if (!cloud?.explained_variance) return null
    return Math.round(cloud.explained_variance.reduce((a, b) => a + b, 0) * 100)
  }, [cloud])

  // Coordinate X offsets for Side-by-Side Split mode
  const isSplit = inspectionMode === 'split'
  const realOffsetX = isSplit ? -3.0 : 0
  const synthOffsetX = isSplit ? 3.0 : 0
  const canaryOffsetX = isSplit ? -3.0 : 0

  // Compute live point opacities based on inspection mode and blendRatio
  const realOpacity = useMemo(() => {
    if (inspectionMode === 'synthetic') return 0
    if (inspectionMode === 'real' || inspectionMode === 'split') return 0.95
    if (layer === 'synthetic') return 0
    if (layer === 'real') return 0.95
    return (1 - blendRatio * 0.7) * 0.85
  }, [inspectionMode, layer, blendRatio])

  const synthOpacity = useMemo(() => {
    if (inspectionMode === 'real') return 0
    if (inspectionMode === 'synthetic' || inspectionMode === 'split') return 0.95
    if (layer === 'real') return 0
    if (layer === 'synthetic') return 0.95
    return (0.25 + blendRatio * 0.7) * 0.95
  }, [inspectionMode, layer, blendRatio])

  const canariesVisible = useMemo(() => {
    if (inspectionMode === 'synthetic') return false
    if (inspectionMode === 'canaries') return true
    return showCanaries
  }, [inspectionMode, showCanaries])

  // Current active explainer for the presentation tray
  const currentChapterInfo = activeChapter ? CHAPTERS.find((c) => c.num === activeChapter) : null
  const currentExplainer = currentChapterInfo ? EXPLAINERS[currentChapterInfo.explainerKey] : null
  const renderedFormula = useMemo(() => {
    if (!currentExplainer?.katex) return ''
    try {
      return katex.renderToString(currentExplainer.katex, { displayMode: true, throwOnError: false })
    } catch {
      return currentExplainer.katex
    }
  }, [currentExplainer])

  const handleInspect = (type: 'real' | 'synthetic' | 'canary') => {
    if (type === 'real') {
      setInspectedDetail({
        type: 'real',
        title: 'Sensitive Training Records (Ground Truth)',
        color: palette.realHex,
        count: cloud?.real.length ?? 0,
        description:
          'Original sensitive records from the source training distribution. Under differential privacy, individual record presence is mathematically obscured.',
      })
    } else if (type === 'synthetic') {
      setInspectedDetail({
        type: 'synthetic',
        title: 'DP Synthetic Cloud (AIM Generative Output)',
        color: palette.synthHex,
        count: cloud?.synthetic.length ?? 0,
        description:
          'Calibrated synthetic samples generated under strict DP bounds (ε). Captures joint column correlations while guaranteeing zero exact training memorization.',
      })
    } else {
      setInspectedDetail({
        type: 'canary',
        title: 'Adversarial Canary Decoys (Audit Probes)',
        color: palette.canaryHex,
        count: cloud?.canaries.length ?? 0,
        description:
          'High-dimensional outlier decoys planted during generation. The empirical distance to the nearest synthetic sample establishes the verified privacy ceiling.',
      })
    }
    onPointClick?.(type)
  }

  return (
    <div
      className={`transition-all duration-300 ${
        isFullscreen
          ? 'fixed inset-0 z-50 flex h-screen w-screen flex-col bg-paper text-ink overflow-hidden p-6'
          : 'well relative flex h-full min-h-[580px] w-full flex-col overflow-hidden rounded-2xl'
      }`}
    >
      {/* ------------------------------------------------ Top Toolbar & Presentation Deck */}
      <div className="z-20 flex flex-wrap items-center justify-between gap-3 border-b border-line/70 bg-card/90 px-4 py-2.5 shadow-sm backdrop-blur-md">
        {/* Left: Stage Title & PCA Metrics */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span className="h-2.5 w-2.5 rounded-full bg-brass animate-pulse" />
            <span className="font-semibold text-ink">
              {running ? (currentStage ? `Executing: ${currentStage}` : 'Synthesizing...') : '3D Privacy Chamber'}
            </span>
            {explainedVariance !== null && (
              <span className="text-muted">
                · Fitted PCA ({explainedVariance}% variance)
              </span>
            )}
          </div>

          {cloud && (cloud.real.length > CAPACITY || cloud.synthetic.length > CAPACITY) && (
            <span className="hidden sm:inline-block rounded bg-paper-2 px-2 py-0.5 font-mono text-[10px] text-faint border border-line">
              Subsampled to 6,000 instances
            </span>
          )}
        </div>

        {/* Center: Presentation Chapters (Engineered Storytelling Deck) */}
        <div className="hidden 2xl:flex items-center gap-1 rounded-lg border border-line bg-paper-2 p-1">
          <span className="px-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-muted">
            Story Deck:
          </span>
          {CHAPTERS.map((ch) => (
            <button
              key={ch.num}
              type="button"
              onClick={() => selectChapter(ch)}
              className={`rounded px-2.5 py-1 font-mono text-[10px] font-medium transition-all ${
                activeChapter === ch.num
                  ? 'bg-brass text-white shadow-xs font-semibold'
                  : 'text-muted hover:text-ink hover:bg-card'
              }`}
            >
              {ch.num}. {ch.title.split('. ')[1]}
            </button>
          ))}
          {activeChapter !== null && (
            <button
              type="button"
              onClick={() => {
                setActiveChapter(null)
                setScannerActive(false)
                setInspectionMode('both')
                onLayerChange?.('both')
                onToggleCanaries?.(true)
                onToggleLinks?.(true)
                setBlendRatio(0.5)
              }}
              className="px-1.5 py-0.5 text-faint hover:text-seal font-mono text-[10px]"
              title="Reset presentation step"
            >
              ✕
            </button>
          )}
        </div>

        {/* Right: Camera Views, Scanner Toggle & Fullscreen Button */}
        <div className="flex items-center gap-2">
          {/* Camera Angles */}
          <div className="flex rounded-md bg-paper-2 p-0.5 border border-line">
            <button
              type="button"
              onClick={() => setView('orbit')}
              className={`rounded px-2 py-0.5 font-mono text-[10px] font-medium transition-all ${
                view === 'orbit' ? 'bg-brass text-white shadow-xs' : 'text-muted hover:text-ink'
              }`}
            >
              Orbit
            </button>
            <button
              type="button"
              onClick={() => setView('top')}
              className={`rounded px-2 py-0.5 font-mono text-[10px] font-medium transition-all ${
                view === 'top' ? 'bg-brass text-white shadow-xs' : 'text-muted hover:text-ink'
              }`}
            >
              2D PCA
            </button>
            <button
              type="button"
              onClick={() => setView('side')}
              className={`rounded px-2 py-0.5 font-mono text-[10px] font-medium transition-all ${
                view === 'side' ? 'bg-brass text-white shadow-xs' : 'text-muted hover:text-ink'
              }`}
            >
              Side
            </button>
            <button
              type="button"
              onClick={() => setView('cinematic')}
              className={`rounded px-2 py-0.5 font-mono text-[10px] font-medium transition-all ${
                view === 'cinematic' ? 'bg-brass text-white shadow-xs' : 'text-muted hover:text-ink'
              }`}
            >
              Turntable
            </button>
          </div>

          {/* 3D Badges toggle */}
          <button
            type="button"
            onClick={() => setShow3dBadges(!show3dBadges)}
            className={`rounded-md border px-2 py-1 font-mono text-[10px] transition-all ${
              show3dBadges
                ? 'border-brass bg-brass/10 text-brass'
                : 'border-line bg-card text-muted hover:text-ink'
            }`}
            title="Toggle floating 3D cluster badges"
          >
            🏷️ Badges
          </button>

          {/* Audit Scanner Plane Toggle */}
          <button
            type="button"
            onClick={() => setScannerActive(!scannerActive)}
            className={`rounded-md border px-2 py-1 font-mono text-[10px] transition-all ${
              scannerActive
                ? 'border-brass bg-brass text-white'
                : 'border-line bg-card text-muted hover:border-brass hover:text-ink'
            }`}
            title="Toggle volumetric laser audit scanner"
          >
            ⚡ Scanner
          </button>

          {/* Auto-Rotation Toggle */}
          <button
            type="button"
            onClick={() => setOrbitActive(!orbitActive)}
            className="rounded-md border border-line bg-card px-2 py-1 font-mono text-[10px] text-muted hover:border-brass hover:text-ink"
            title="Toggle auto-orbit camera rotation"
          >
            {orbitActive ? '🌀 Auto' : '⏸️ Fixed'}
          </button>

          {/* Primary Fullscreen / Presentation Studio Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wider transition-all shadow-xs ${
              isFullscreen
                ? 'border border-line bg-card text-ink hover:bg-paper-2'
                : 'border border-brass bg-brass text-white shadow-brass hover:bg-[#966330]'
            }`}
            title={isFullscreen ? 'Exit Fullscreen Presentation Studio (ESC)' : 'Expand Fullscreen Presentation Studio (F)'}
          >
            <span>{isFullscreen ? '✕ Exit Studio' : '⛶ Studio Focus'}</span>
            <span className="text-[10px] opacity-70">({isFullscreen ? 'ESC' : 'F'})</span>
          </button>
        </div>
      </div>

      {/* ------------------------------------------------ Primary Manifold Inspection Bar */}
      <div className="z-10 flex flex-wrap items-center justify-between gap-2 border-b border-line/60 bg-card/70 px-4 py-1.5 backdrop-blur-sm">
        <div className="flex items-center gap-1.5 font-mono text-xs text-muted">
          <span className="font-semibold uppercase text-[10px] tracking-wider text-muted">Filter View:</span>
          <div className="flex rounded-lg border border-line bg-paper-2 p-0.5">
            <button
              type="button"
              onClick={() => handleInspectionModeChange('both')}
              className={`rounded px-2.5 py-1 font-mono text-[11px] font-semibold transition-all ${
                inspectionMode === 'both'
                  ? 'bg-card text-ink shadow-xs border border-line'
                  : 'text-muted hover:text-ink'
              }`}
            >
              ⚡ All Superimposed
            </button>
            <button
              type="button"
              onClick={() => handleInspectionModeChange('real')}
              className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[11px] font-semibold transition-all ${
                inspectionMode === 'real'
                  ? 'bg-[#38BDF8]/20 text-[#38BDF8] shadow-xs border border-[#38BDF8]/50'
                  : 'text-muted hover:text-ink'
              }`}
            >
              <span className="h-2 w-2 rounded-full bg-[#38BDF8] shadow-[0_0_8px_#38BDF8]" />
              <span>Solo Real ({cloud?.real.length ?? 0})</span>
            </button>
            <button
              type="button"
              onClick={() => handleInspectionModeChange('synthetic')}
              className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[11px] font-semibold transition-all ${
                inspectionMode === 'synthetic'
                  ? 'bg-[#F59E0B]/20 text-[#F59E0B] shadow-xs border border-[#F59E0B]/50'
                  : 'text-muted hover:text-ink'
              }`}
            >
              <span className="h-2 w-2 rounded-full bg-[#FACC15] shadow-[0_0_8px_#FACC15]" />
              <span>Solo Synthetic ({cloud?.synthetic.length ?? 0})</span>
            </button>
            <button
              type="button"
              onClick={() => handleInspectionModeChange('canaries')}
              className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[11px] font-semibold transition-all ${
                inspectionMode === 'canaries'
                  ? 'bg-[#FF2E55]/20 text-[#FF2E55] shadow-xs border border-[#FF2E55]/50'
                  : 'text-muted hover:text-ink'
              }`}
            >
              <span className="h-2 w-2 rounded-full bg-[#FF2E55] shadow-[0_0_8px_#FF2E55]" />
              <span>Solo Canaries ({cloud?.canaries.length ?? 0})</span>
            </button>
            <button
              type="button"
              onClick={() => handleInspectionModeChange('split')}
              className={`flex items-center gap-1.5 rounded px-3 py-1 font-mono text-[11px] font-bold transition-all ${
                inspectionMode === 'split'
                  ? 'bg-brass text-white shadow-brass'
                  : 'text-muted hover:text-ink hover:bg-card'
              }`}
              title="Separates Real and Synthetic clouds side-by-side with an illuminated divider"
            >
              <span>↔ Split Comparison</span>
              <span className="rounded bg-black/20 px-1 text-[9px] uppercase">Zero Overlap</span>
            </button>
          </div>
        </div>

        {/* Quick hint banner */}
        <div className="hidden lg:flex items-center gap-2 font-mono text-[10px] text-faint">
          <span className="text-muted">Click any cluster point to inspect differential privacy properties.</span>
        </div>
      </div>

      {/* ------------------------------------------------ Main Stage Area */}
      <div className="relative flex-1 w-full h-full min-h-[460px]">
        {webGlSupported ? (
          <Canvas
            dpr={[1, 2]}
            camera={{ fov: 42, position: [5.2, 3.4, 6.2], near: 0.1, far: 100 }}
            gl={{ antialias: true, alpha: true }}
            onCreated={({ gl }) => {
              if (!gl) setWebGlSupported(false)
            }}
          >
            <ambientLight intensity={1.1} />
            <directionalLight position={[5, 8, 4]} intensity={1.4} color="#FFF8EE" />
            <directionalLight position={[-5, -4, -3]} intensity={0.6} color="#BEE3F8" />
            
            <MeasurementBoundingBox gridSubColor={palette.gridFloor} />
            <LaserAuditScanner active={scannerActive || running} color={palette.scanner} />
            <SplitDividerPlane visible={isSplit} />

            {/* Real record point cloud (Electric Sky Blue / Cyan) */}
            <PointCloudLayer
              points={cloud?.real ?? []}
              color={palette.real}
              size={0.16}
              opacity={realOpacity}
              offsetX={realOffsetX}
              texture={circleTexture}
              visible={realOpacity > 0 && !!cloud}
              onClick={() => handleInspect('real')}
            />

            {/* Synthetic record point cloud (Radiant Bright Yellow) */}
            <PointCloudLayer
              points={cloud?.synthetic ?? []}
              color={palette.synth}
              size={0.16}
              opacity={synthOpacity}
              offsetX={synthOffsetX}
              texture={circleTexture}
              visible={synthOpacity > 0 && !!cloud}
              onClick={() => handleInspect('synthetic')}
            />

            {/* Canary adversarial decoys (Glowing 3D Crimson Probes) */}
            <CanaryProbes
              points={cloud?.canaries ?? []}
              color={palette.canary}
              visible={canariesVisible && !!cloud}
              offsetX={canaryOffsetX}
              onClick={() => handleInspect('canary')}
            />

            {/* Canary nearest match attack lines */}
            <NearestMatchLinks
              cloud={cloud}
              visible={showLinks && canariesVisible}
              color={palette.beam}
              offsetXCanary={canaryOffsetX}
              offsetXSynth={synthOffsetX}
            />

            {/* Floating 3D Cluster Labels */}
            {show3dBadges && cloud && (
              <group>
                {/* Real Data Cluster Badge */}
                {realOpacity > 0 && (
                  <Html
                    center
                    position={[realOffsetX - 0.5, 2.7, 0]}
                    distanceFactor={11}
                  >
                    <div
                      onClick={() => handleInspect('real')}
                      className="cursor-pointer select-none rounded-md border border-[#38BDF8]/60 bg-slate-950/90 px-3 py-1 font-mono text-[11px] font-bold text-[#38BDF8] shadow-[0_0_15px_rgba(56,189,248,0.4)] backdrop-blur transition-transform hover:scale-105"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-[#38BDF8] animate-pulse" />
                        <span>SENSITIVE REAL MANIFOLD</span>
                      </div>
                      <div className="text-[9px] font-normal text-slate-300">
                        N = {cloud.real.length.toLocaleString()} records · Protected Ground Truth
                      </div>
                    </div>
                  </Html>
                )}

                {/* Synthetic Data Cluster Badge */}
                {synthOpacity > 0 && (
                  <Html
                    center
                    position={[synthOffsetX + 0.5, 2.7, 0]}
                    distanceFactor={11}
                  >
                    <div
                      onClick={() => handleInspect('synthetic')}
                      className="cursor-pointer select-none rounded-md border border-[#F59E0B]/60 bg-slate-950/90 px-3 py-1 font-mono text-[11px] font-bold text-[#F59E0B] shadow-[0_0_15px_rgba(245,158,11,0.4)] backdrop-blur transition-transform hover:scale-105"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-[#F59E0B] animate-pulse" />
                        <span>DP SYNTHETIC CLOUD</span>
                      </div>
                      <div className="text-[9px] font-normal text-amber-200/80">
                        N = {cloud.synthetic.length.toLocaleString()} records · AIM (ε=1.0)
                      </div>
                    </div>
                  </Html>
                )}

                {/* Split Center Boundary Badge */}
                {isSplit && (
                  <Html center position={[0, 3.1, 0]} distanceFactor={11}>
                    <div className="select-none rounded-md border border-line bg-card/90 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-brass shadow-sm backdrop-blur">
                      ↔ PRIVACY BARRIER
                    </div>
                  </Html>
                )}
              </group>
            )}

            <CameraRig view={view} orbitActive={orbitActive} />
          </Canvas>
        ) : (
          <Fallback2DScatter
            cloud={cloud}
            layer={layer}
            showCanaries={showCanaries}
            palette={palette}
            onPointClick={onPointClick}
          />
        )}

        {/* Empty state when no run has happened */}
        {!cloud && !running && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-brass/40 bg-brass/10 text-brass shadow-brass">
              <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
              </svg>
            </div>
            <p className="font-display text-3xl text-ink">
              Privacy Chamber at Rest
            </p>
            <p className="mt-1.5 max-w-md font-sans text-xs text-muted">
              Select a dataset and privacy budget above, then click <strong>Run release</strong>. Real sensitive records (Cyan), synthetic points (Gold), and adversarial decoys (Crimson) will project into this 3D manifold.
            </p>
          </div>
        )}

        {/* ------------------------------------------------ Inspected Point Info Floating Card */}
        <AnimatePresence>
          {inspectedDetail && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="absolute top-4 left-4 z-20 max-w-sm rounded-xl border border-line bg-card/95 p-4 shadow-e2 backdrop-blur-md"
            >
              <div className="flex items-center justify-between border-b border-line/60 pb-2">
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: inspectedDetail.color, boxShadow: `0 0 8px ${inspectedDetail.color}` }}
                  />
                  <span className="font-mono text-xs font-bold text-ink">
                    {inspectedDetail.title}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setInspectedDetail(null)}
                  className="text-faint hover:text-ink font-mono text-xs"
                >
                  ✕
                </button>
              </div>

              <div className="mt-2 text-xs text-muted leading-relaxed">
                {inspectedDetail.description}
              </div>

              <div className="mt-3 flex items-center justify-between border-t border-line/50 pt-2 font-mono text-[10px]">
                <span className="text-faint">Total Population:</span>
                <span className="font-semibold text-ink">{inspectedDetail.count.toLocaleString()} instances</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ------------------------------------------------ Floating Bottom Left Legend & Crossfader */}
        <div className="absolute bottom-4 left-4 z-20 flex flex-col gap-2.5 rounded-2xl border border-line bg-card/95 p-4 shadow-e2 backdrop-blur-md max-w-xs md:max-w-sm">
          {/* Header Title */}
          <div className="flex items-center justify-between border-b border-line/60 pb-2">
            <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-ink">
              Manifold Identification
            </span>
            <span className="font-mono text-[10px] text-brass">
              {isSplit ? 'Side-by-Side' : `${Math.round((1 - blendRatio) * 100)}% Real / ${Math.round(blendRatio * 100)}% Synth`}
            </span>
          </div>

          {/* Real vs Synthetic Density Crossfader */}
          {!isSplit && (
            <div className="pb-1">
              <div className="flex items-center justify-between font-mono text-[10px] text-muted mb-1">
                <span className="font-semibold text-[#38BDF8]">Real Sensitive (Blue)</span>
                <span className="text-faint font-semibold">DP Noise Dissolve</span>
                <span className="font-semibold text-[#FACC15]">DP Synthetic (Yellow)</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.02}
                value={blendRatio}
                onChange={(e) => setBlendRatio(Number(e.target.value))}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-paper-2 accent-[#8A5A2B]"
                title="Crossfade between pure real records and pure DP synthetic cloud"
              />
            </div>
          )}

          {/* Three Unmistakable Legend Rows with Swatches & Direct Solo Buttons */}
          <div className="space-y-2">
            {/* 1. Real Records */}
            <div className="flex items-center justify-between rounded-lg border border-line/60 bg-paper-2/60 p-2">
              <div
                className="flex items-center gap-2 cursor-pointer"
                onClick={() => handleInspect('real')}
              >
                <span className="h-3.5 w-3.5 rounded-full bg-[#38BDF8] shadow-[0_0_8px_#38BDF8]" />
                <div>
                  <div className="font-mono text-xs font-bold text-ink flex items-center gap-1.5">
                    <span>Real Sensitive Data</span>
                    <span className="rounded bg-[#38BDF8]/10 px-1 py-0.2 text-[10px] text-[#38BDF8]">
                      {cloud?.real.length.toLocaleString() ?? '—'}
                    </span>
                  </div>
                  <div className="text-[10px] text-muted">Original sensitive training distribution (Blue)</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleInspectionModeChange(inspectionMode === 'real' ? 'both' : 'real')}
                className={`rounded px-1.5 py-0.5 font-mono text-[10px] border transition-all ${
                  inspectionMode === 'real'
                    ? 'border-[#38BDF8] bg-[#38BDF8] text-white font-bold'
                    : 'border-line text-muted hover:text-ink'
                }`}
              >
                {inspectionMode === 'real' ? 'Solo ✓' : 'Solo'}
              </button>
            </div>

            {/* 2. Synthetic Cloud */}
            <div className="flex items-center justify-between rounded-lg border border-line/60 bg-paper-2/60 p-2">
              <div
                className="flex items-center gap-2 cursor-pointer"
                onClick={() => handleInspect('synthetic')}
              >
                <span className="h-3.5 w-3.5 rounded-full bg-[#FACC15] shadow-[0_0_8px_#FACC15]" />
                <div>
                  <div className="font-mono text-xs font-bold text-ink flex items-center gap-1.5">
                    <span>DP Synthetic Cloud</span>
                    <span className="rounded bg-[#FACC15]/10 px-1 py-0.2 text-[10px] text-[#FACC15]">
                      {cloud?.synthetic.length.toLocaleString() ?? '—'}
                    </span>
                  </div>
                  <div className="text-[10px] text-muted">Generative release with provable (ε, δ) bounds (Yellow)</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleInspectionModeChange(inspectionMode === 'synthetic' ? 'both' : 'synthetic')}
                className={`rounded px-1.5 py-0.5 font-mono text-[10px] border transition-all ${
                  inspectionMode === 'synthetic'
                    ? 'border-[#FACC15] bg-[#FACC15] text-black font-bold'
                    : 'border-line text-muted hover:text-ink'
                }`}
              >
                {inspectionMode === 'synthetic' ? 'Solo ✓' : 'Solo'}
              </button>
            </div>

            {/* 3. Adversarial Canaries */}
            <div className="flex items-center justify-between rounded-lg border border-line/60 bg-paper-2/60 p-2">
              <div
                className="flex items-center gap-2 cursor-pointer"
                onClick={() => handleInspect('canary')}
              >
                <span className="h-3.5 w-3.5 rounded-full bg-[#FF2E55] shadow-[0_0_8px_#FF2E55]" />
                <div>
                  <div className="font-mono text-xs font-bold text-ink flex items-center gap-1.5">
                    <span>Adversarial Canaries</span>
                    <span className="rounded bg-[#FF2E55]/10 px-1 py-0.2 text-[10px] text-[#FF2E55]">
                      {cloud?.canaries.length ?? '—'}
                    </span>
                  </div>
                  <div className="text-[10px] text-muted">Extreme outlier decoys for empirical audit</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleInspectionModeChange(inspectionMode === 'canaries' ? 'both' : 'canaries')}
                className={`rounded px-1.5 py-0.5 font-mono text-[10px] border transition-all ${
                  inspectionMode === 'canaries'
                    ? 'border-[#FF2E55] bg-[#FF2E55] text-white font-bold'
                    : 'border-line text-muted hover:text-ink'
                }`}
              >
                {inspectionMode === 'canaries' ? 'Solo ✓' : 'Solo'}
              </button>
            </div>
          </div>

          {/* Quick Canary Controls */}
          <div className="flex items-center justify-between border-t border-line/60 pt-2 text-muted">
            <label className="flex cursor-pointer items-center gap-1.5 font-mono text-[10px]">
              <input
                type="checkbox"
                checked={showCanaries}
                onChange={(e) => onToggleCanaries?.(e.target.checked)}
                className="accent-[#FF2E55]"
              />
              <span>Render Canary Probes</span>
            </label>
            <label className="flex cursor-pointer items-center gap-1.5 font-mono text-[10px]">
              <input
                type="checkbox"
                checked={showLinks}
                disabled={!showCanaries}
                onChange={(e) => onToggleLinks?.(e.target.checked)}
                className="accent-[#FF2E55]"
              />
              <span>Affinity Rays</span>
            </label>
          </div>
        </div>

        {/* ------------------------------------------------ Fullscreen Presentation Sidebar Overlay */}
        <AnimatePresence>
          {isFullscreen && currentChapterInfo && currentExplainer && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="absolute right-6 top-6 bottom-6 z-30 flex w-96 flex-col justify-between rounded-2xl border border-line bg-card/95 p-5 shadow-e2 backdrop-blur-lg"
            >
              <div>
                <div className="flex items-center justify-between border-b border-line pb-2.5">
                  <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-brass">
                    Presentation Explainer
                  </span>
                  <span className="font-mono text-[10px] text-faint">
                    Step {currentChapterInfo.num} of 5
                  </span>
                </div>

                <h3 className="mt-3 font-display text-2xl text-ink">
                  {currentChapterInfo.title}
                </h3>
                <p className="mt-1 font-sans text-xs leading-relaxed text-muted">
                  {currentChapterInfo.blurb}
                </p>

                {/* Formula Block */}
                <div className="mt-4 rounded-lg border border-line bg-paper-2 p-3 shadow-inset overflow-x-auto text-center">
                  <div
                    className="text-sm text-ink"
                    dangerouslySetInnerHTML={{ __html: renderedFormula }}
                  />
                </div>

                {/* Rigorous Plain Words */}
                <div className="mt-4 rounded-r border-l-2 border-brass bg-paper-2/50 py-2 pl-3 pr-2 text-xs leading-relaxed text-ink font-sans">
                  {currentExplainer.plain}
                </div>
              </div>

              {/* Source verification footer */}
              <div className="border-t border-line pt-3 font-mono text-[10px] text-faint flex items-center gap-1.5">
                <span className="text-brass">Source:</span>
                <code className="truncate">{currentExplainer.source}</code>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// Re-export as RecordCloud for backward compatibility
export const RecordCloud = PrivacyChamber

