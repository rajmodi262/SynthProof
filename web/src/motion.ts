/**
 * Motion system constants for SynthProof "Atelier"
 * Spec A9: Durations, easings, and spring presets.
 */

export const DURATION = {
  fast: 0.12,
  base: 0.2,
  slow: 0.32,
  stage: 0.48,
} as const

export const EASING = {
  standard: [0.2, 0, 0, 1] as const,
  decel: [0, 0, 0, 1] as const,
  accel: [0.4, 0, 1, 1] as const,
} as const

export const SPRING = {
  type: 'spring' as const,
  stiffness: 260,
  damping: 30,
} as const
