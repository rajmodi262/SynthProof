import { GaugeEpsilon } from './GaugeEpsilon'
import { AuditRange } from './AuditRange'
import { Marginals } from './Marginals'
import { PipelineLog } from './PipelineLog'
import type { Histogram, RunResult, StageEvent } from '@/types'

interface RightRailProps {
  spent: number
  targetEps: number
  currentStage: string | null
  result: RunResult | null
  stages: StageEvent[]
  running: boolean
  onOpenExplainer: (key: string) => void
}

export function RightRail({
  spent,
  targetEps,
  currentStage,
  result,
  stages,
  running,
  onOpenExplainer,
}: RightRailProps) {
  const histograms = (result?.histograms ?? {}) as Record<string, Histogram>

  return (
    <div className="flex flex-col gap-4">
      {/* 1. Semicircular brass pressure gauge */}
      <GaugeEpsilon
        spent={spent}
        total={targetEps}
        stage={currentStage}
        onOpenExplainer={() => onOpenExplainer('epsilon')}
      />

      {/* 2. MIQE 2.0 verifiable audit range */}
      <AuditRange
        measurements={result?.measurements ?? null}
        audit={result?.audit ?? null}
        targetEps={targetEps}
        onOpenExplainer={() => onOpenExplainer('ceiling')}
      />

      {/* 3. Real vs synthetic overlaid marginal histograms */}
      {Object.keys(histograms).length > 0 && (
        <Marginals
          histograms={histograms}
          maxColumns={3}
          onOpenExplainer={() => onOpenExplainer('faithfulness')}
        />
      )}

      {/* 4. Streamed stage timeline log */}
      <div className="min-h-[260px] flex-1">
        <PipelineLog stages={stages} running={running} />
      </div>
    </div>
  )
}
