import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import type { Cloud, Point3 } from '@/types'

/**
 * The console's hero: real records, synthetic records and planted canaries drawn in one
 * shared 3D frame.
 *
 * Every point is an actual row projected by the server through a single transform fitted on
 * the real table (see `synthproof/api/projection.py`). Nothing here is generated for looks —
 * if the synthetic cloud sits on top of the real one, the mechanism preserved that structure;
 * if it collapses to a blob, the noise destroyed it.
 *
 * The canary connectors are the part worth explaining at a viva. Each line runs from a
 * planted canary to its nearest synthetic record, which is exactly the quantity the canary
 * auditor scores. A short, hot line means that individual is recoverable from the release.
 */

const PROVED = new THREE.Color('#8F8AF0') // real records — the formal side
const AUDITED = new THREE.Color('#E8964C') // synthetic records — the empirical side
const CANARY = new THREE.Color('#FF5C7A') // planted individuals

export type CloudLayer = 'both' | 'real' | 'synthetic'

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

const CAPACITY = 700

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

  // Positions ease toward the newest run rather than snapping. The transition itself is
  // informative: you can see how far a mechanism moved the distribution.
  useFrame((_, delta) => {
    if (!geom.current) return
    const attr = geom.current.getAttribute('position') as THREE.BufferAttribute
    const arr = current.current
    const k = Math.min(1, delta * 3.2)
    for (let i = 0; i < arr.length; i++) {
      arr[i] += (target[i] - arr[i]) * k
    }
    attr.array = arr
    attr.needsUpdate = true

    if (ref.current && jitter > 0) {
      // A faint breathing motion while a run is in flight — the mechanism is sampling.
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

/** Draws canary → nearest-synthetic-record connectors, coloured by distance. */
function CanaryLinks({ cloud, visible }: { cloud: Cloud | null; visible: boolean }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    if (!cloud?.canaries.length || !cloud.synthetic.length) return g

    const positions: number[] = []
    const colors: number[] = []
    const hot = new THREE.Color('#FF5C7A')
    const cold = new THREE.Color('#3D4152')

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
      // Near neighbour = recoverable individual = hot. Far = dissolved into the crowd.
      const t = Math.min(1, Math.sqrt(best) / 0.9)
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
      <lineBasicMaterial vertexColors transparent opacity={0.55} />
    </lineSegments>
  )
}

/** A faint reference cage, so rotation reads as depth rather than drift. */
function Frame() {
  return (
    <group>
      <mesh>
        <boxGeometry args={[4.4, 4.4, 4.4]} />
        <meshBasicMaterial color="#2A2C38" wireframe transparent opacity={0.16} />
      </mesh>
      <gridHelper args={[4.4, 8, '#2A2C38', '#1E202A']} position={[0, -2.2, 0]} />
    </group>
  )
}

function Rig({ running }: { running: boolean }) {
  const { camera } = useThree()
  useEffect(() => {
    camera.position.set(3.6, 2.4, 4.2)
  }, [camera])
  return (
    <OrbitControls
      enablePan={false}
      minDistance={3}
      maxDistance={11}
      autoRotate
      autoRotateSpeed={running ? 1.6 : 0.45}
      enableDamping
      dampingFactor={0.06}
    />
  )
}

export function RecordCloud({ cloud, layer, showCanaries, showLinks, running }: CloudProps) {
  const showReal = layer === 'both' || layer === 'real'
  const showSynth = layer === 'both' || layer === 'synthetic'

  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ fov: 42, near: 0.1, far: 100 }}
      gl={{ antialias: true, alpha: true }}
      style={{ background: 'transparent' }}
    >
      <Frame />
      <PointLayer
        points={cloud?.real ?? []}
        color={PROVED}
        size={0.045}
        visible={showReal && !!cloud}
        opacity={layer === 'both' ? 0.62 : 0.9}
        jitter={0}
      />
      <PointLayer
        points={cloud?.synthetic ?? []}
        color={AUDITED}
        size={0.045}
        visible={showSynth && !!cloud}
        opacity={layer === 'both' ? 0.62 : 0.9}
        jitter={running ? 1 : 0}
      />
      <PointLayer
        points={cloud?.canaries ?? []}
        color={CANARY}
        size={0.13}
        visible={showCanaries && !!cloud}
        opacity={1}
        jitter={0}
      />
      <CanaryLinks cloud={cloud} visible={showLinks && showCanaries} />
      <Rig running={running} />
    </Canvas>
  )
}
