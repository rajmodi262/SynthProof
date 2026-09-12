import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import type { Cloud, Point3 } from '@/types'

/**
 * Cinema-Grade 3D Manifold: Real records, DP synthetic records, and planted adversarial
 * canaries projected into a shared 3D coordinate space with volumetric laser scanners,
 * canary radar rings, and interactive camera views.
 */

const PROVED_COLOR = new THREE.Color('#6366F1')   // Electric Indigo
const AUDITED_COLOR = new THREE.Color('#F59E0B')  // Solar Amber
const CANARY_COLOR = new THREE.Color('#FF1E56')   // Laser Crimson Neon
const SCANNER_COLOR = new THREE.Color('#06B6D4')  // Electric Cyan

export type CloudLayer = 'both' | 'real' | 'synthetic'
export type CameraView = 'orbit' | 'top' | 'side'

interface CloudProps {
  cloud: Cloud | null
  layer: CloudLayer
  showCanaries: boolean
  showLinks: boolean
  running: boolean
}

/** Pads or trims a point list to a fixed length so buffers can be reused across runs. */
function fixed(points: Point3[], size: number): Float32Array {
  const out = new Float32Array(size * 3)
  if (!points.length) return out
  for (let i = 0; i < size; i++) {
    const p = points[i % points.length]
    out[i * 3] = p[0]
    out[i * 3 + 1] = p[1]
    out[i * 3 + 2] = p[2]
  }
  return out
}

const CAPACITY = 750

function PointLayer({
  points,
  color,
  size,
  visible,
  opacity,
  jitter,
}: {
  points: Point3[]
  color: THREE.Color
  size: number
  visible: boolean
  opacity: number
  jitter: number
}) {
  const ref = useRef<THREE.Points>(null)
  const target = useMemo(() => fixed(points, CAPACITY), [points])
  const current = useRef<Float32Array>(new Float32Array(CAPACITY * 3))
  const geom = useRef<THREE.BufferGeometry>(null)

  useFrame((_, delta) => {
    if (!geom.current) return
    const attr = geom.current.getAttribute('position') as THREE.BufferAttribute
    const arr = current.current
    const k = Math.min(1, delta * 3.6)
    for (let i = 0; i < arr.length; i++) {
      arr[i] += (target[i] - arr[i]) * k
    }
    attr.array = arr
    attr.needsUpdate = true

    if (ref.current && jitter > 0) {
      ref.current.rotation.y += delta * 0.02
    }
  })

  return (
    <points ref={ref} visible={visible}>
      <bufferGeometry ref={geom}>
        <bufferAttribute
          attach="attributes-position"
          count={CAPACITY}
          array={current.current}
          itemSize={3}
          usage={THREE.DynamicDrawUsage}
        />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        color={color}
        transparent
        opacity={opacity}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

/** Pulsating radar rings marking each planted canary in 3D coordinate space. */
function CanaryPulsars({ points, visible }: { points: Point3[]; visible: boolean }) {
  const groupRef = useRef<THREE.Group>(null)

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    const scale = 1 + Math.sin(t * 3.5) * 0.25
    groupRef.current.children.forEach((child) => {
      child.scale.set(scale, scale, scale)
    })
  })

  if (!visible || !points.length) return null

  return (
    <group ref={groupRef}>
      {points.slice(0, 40).map((p, idx) => (
        <mesh key={idx} position={[p[0], p[1], p[2]]}>
          <ringGeometry args={[0.07, 0.09, 24]} />
          <meshBasicMaterial
            color={CANARY_COLOR}
            side={THREE.DoubleSide}
            transparent
            opacity={0.75}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  )
}

/** Draws canary -> nearest-synthetic-record connectors with glowing thermal gradient. */
function CanaryLinks({ cloud, visible }: { cloud: Cloud | null; visible: boolean }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    if (!cloud?.canaries.length || !cloud.synthetic.length) return g

    const positions: number[] = []
    const colors: number[] = []
    const hot = new THREE.Color('#FF1E56')
    const cold = new THREE.Color('#06B6D4')

    for (const c of cloud.canaries) {
      let best = Infinity
      let bestPoint = cloud.synthetic[0]
      for (const s of cloud.synthetic) {
        const d = (c[0] - s[0]) ** 2 + (c[1] - s[1]) ** 2 + (c[2] - s[2]) ** 2
        if (d < best) {
          best = d
          bestPoint = s
        }
      }
      const t = Math.min(1, Math.sqrt(best) / 0.85)
      const col = cold.clone().lerp(hot, 1 - t)
      positions.push(c[0], c[1], c[2], bestPoint[0], bestPoint[1], bestPoint[2])
      colors.push(col.r, col.g, col.b, col.r, col.g, col.b)
    }

    g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    return g
  }, [cloud])

  useEffect(() => () => geometry.dispose(), [geometry])

  return (
    <lineSegments geometry={geometry} visible={visible}>
      <lineBasicMaterial vertexColors transparent opacity={0.65} linewidth={1.5} />
    </lineSegments>
  )
}

/** Holographic laser scanner ring that oscillates vertically through the dataset. */
function LaserScanner({ active }: { active: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const t = clock.getElapsedTime()
    meshRef.current.position.y = Math.sin(t * 1.2) * 1.9
  })

  return (
    <group>
      <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.2, 2.3, 48]} />
        <meshBasicMaterial
          color={SCANNER_COLOR}
          side={THREE.DoubleSide}
          transparent
          opacity={active ? 0.28 : 0.12}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  )
}

/** Ambient cosmic particle dust for depth perception. */
function CosmicDust() {
  const points = useMemo(() => {
    const pts: Point3[] = []
    for (let i = 0; i < 200; i++) {
      pts.push([
        (Math.random() - 0.5) * 8.5,
        (Math.random() - 0.5) * 8.5,
        (Math.random() - 0.5) * 8.5,
      ])
    }
    return pts
  }, [])

  return (
    <PointLayer
      points={points}
      color={new THREE.Color('#818CF8')}
      size={0.02}
      visible={true}
      opacity={0.2}
      jitter={0.3}
    />
  )
}

/** Ambient Fibonacci constellation when idle. */
function IdleConstellation() {
  const points = useMemo(() => {
    const pts: Point3[] = []
    const count = 360
    const phi = Math.PI * (3 - Math.sqrt(5))
    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2
      const radius = Math.sqrt(1 - y * y) * 1.95
      const theta = phi * i
      pts.push([Math.cos(theta) * radius, y * 1.95, Math.sin(theta) * radius])
    }
    return pts
  }, [])

  return (
    <PointLayer
      points={points}
      color={new THREE.Color('#4F46E5')}
      size={0.038}
      visible={true}
      opacity={0.45}
      jitter={0.6}
    />
  )
}

/** Cybernetic grid frame with coordinate markers. */
function CyberFrame() {
  return (
    <group>
      <mesh>
        <boxGeometry args={[4.6, 4.6, 4.6]} />
        <meshBasicMaterial color="#312E81" wireframe transparent opacity={0.2} />
      </mesh>
      <gridHelper args={[4.6, 12, '#4F46E5', '#1E1B4B']} position={[0, -2.3, 0]} />
      <gridHelper args={[4.6, 12, '#312E81', '#0F172A']} position={[0, 2.3, 0]} />
    </group>
  )
}

function CameraRig({
  running,
  view,
  orbitSpeed,
}: {
  running: boolean
  view: CameraView
  orbitSpeed: number
}) {
  const { camera } = useThree()
  const controlsRef = useRef<any>(null)

  useEffect(() => {
    if (view === 'orbit') {
      camera.position.set(3.8, 2.5, 4.4)
    } else if (view === 'top') {
      camera.position.set(0, 5.5, 0.01)
    } else if (view === 'side') {
      camera.position.set(5.5, 0, 0)
    }
    controlsRef.current?.target.set(0, 0, 0)
  }, [view, camera])

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan={true}
      minDistance={2.5}
      maxDistance={14}
      autoRotate={orbitSpeed > 0}
      autoRotateSpeed={running ? orbitSpeed * 2.2 : orbitSpeed}
      enableDamping
      dampingFactor={0.05}
    />
  )
}

export function RecordCloud({ cloud, layer, showCanaries, showLinks, running }: CloudProps) {
  const showReal = layer === 'both' || layer === 'real'
  const showSynth = layer === 'both' || layer === 'synthetic'

  const [view, setView] = useState<CameraView>('orbit')
  const [orbitSpeed, setOrbitSpeed] = useState<number>(0.6)
  const [pointSizeBoost, setPointSizeBoost] = useState(false)

  const pSize = pointSizeBoost ? 0.065 : 0.045
  const canarySize = pointSizeBoost ? 0.16 : 0.13

  return (
    <div className="relative h-full w-full">
      {/* On-Canvas Cybernetic HUD Toolbar */}
      <div className="absolute right-3 top-3 z-10 flex flex-wrap items-center gap-1.5 rounded-lg border border-white/10 bg-stage/80 p-1.5 shadow-lg backdrop-blur-md">
        <div className="flex rounded-md bg-stage-deep/80 p-0.5">
          <button
            onClick={() => setView('orbit')}
            title="3D Perspective Orbit"
            className={`rounded px-2 py-1 font-mono text-[10px] font-medium transition-all ${
              view === 'orbit' ? 'bg-proved text-white shadow-sm' : 'text-graphite-faint hover:text-bone'
            }`}
          >
            3D Orbit
          </button>
          <button
            onClick={() => setView('top')}
            title="Top-Down 2D Projection (PC1 x PC2)"
            className={`rounded px-2 py-1 font-mono text-[10px] font-medium transition-all ${
              view === 'top' ? 'bg-proved text-white shadow-sm' : 'text-graphite-faint hover:text-bone'
            }`}
          >
            2D PCA
          </button>
          <button
            onClick={() => setView('side')}
            title="Side Cross-Section"
            className={`rounded px-2 py-1 font-mono text-[10px] font-medium transition-all ${
              view === 'side' ? 'bg-proved text-white shadow-sm' : 'text-graphite-faint hover:text-bone'
            }`}
          >
            Side
          </button>
        </div>

        <button
          onClick={() => setOrbitSpeed((s) => (s === 0 ? 0.6 : s === 0.6 ? 1.5 : 0))}
          className="rounded-md border border-stage-line bg-stage-deep/80 px-2 py-1 font-mono text-[10px] text-bone transition-all hover:border-proved"
          title="Toggle Auto-Orbit Speed"
        >
          {orbitSpeed === 0 ? '⏸️ Paused' : orbitSpeed === 0.6 ? '🌀 Orbit: 1×' : '⚡ Orbit: 2.5×'}
        </button>

        <button
          onClick={() => setPointSizeBoost((b) => !b)}
          className={`rounded-md border px-2 py-1 font-mono text-[10px] transition-all ${
            pointSizeBoost
              ? 'border-cyber-neon/50 bg-cyber-neon/10 text-cyber-neon'
              : 'border-stage-line bg-stage-deep/80 text-graphite-faint hover:text-bone'
          }`}
          title="Particle Density Bloom"
        >
          ✨ Glow
        </button>
      </div>

      <Canvas
        dpr={[1, 2]}
        camera={{ fov: 42, near: 0.1, far: 100 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <CyberFrame />
        <CosmicDust />
        <LaserScanner active={running} />
        {!cloud && <IdleConstellation />}

        <PointLayer
          points={cloud?.real ?? []}
          color={PROVED_COLOR}
          size={pSize}
          visible={showReal && !!cloud}
          opacity={layer === 'both' ? 0.75 : 0.95}
          jitter={0}
        />
        <PointLayer
          points={cloud?.synthetic ?? []}
          color={AUDITED_COLOR}
          size={pSize}
          visible={showSynth && !!cloud}
          opacity={layer === 'both' ? 0.75 : 0.95}
          jitter={running ? 1 : 0}
        />
        <PointLayer
          points={cloud?.canaries ?? []}
          color={CANARY_COLOR}
          size={canarySize}
          visible={showCanaries && !!cloud}
          opacity={1}
          jitter={0}
        />
        <CanaryPulsars
          points={cloud?.canaries ?? []}
          visible={showCanaries && !!cloud}
        />
        <CanaryLinks cloud={cloud} visible={showLinks && showCanaries} />
        <CameraRig running={running} view={view} orbitSpeed={orbitSpeed} />
      </Canvas>
    </div>
  )
}

