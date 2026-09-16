import { useMemo } from 'react'
import { EChart } from './charts/EChart'
import type { EChartsOption } from 'echarts'

interface GaugeEpsilonProps {
  spent: number
  total: number
  stage: string | null
  onOpenExplainer: () => void
}

export function GaugeEpsilon({ spent, total, stage, onOpenExplainer }: GaugeEpsilonProps) {
  const safeTotal = Math.max(total, 0.01)
  const ratio = Math.min(1, Math.max(0, spent / safeTotal))

  const option: EChartsOption = useMemo(() => {
    return {
      series: [
        {
          type: 'gauge',
          startAngle: 200,
          endAngle: -20,
          min: 0,
          max: safeTotal,
          splitNumber: 4,
          radius: '95%',
          center: ['50%', '65%'],
          itemStyle: {
            color: '#8A5A2B',
          },
          progress: {
            show: true,
            roundCap: false,
            width: 10,
            itemStyle: {
              color: '#8A5A2B',
            },
          },
          pointer: {
            length: '60%',
            width: 3,
            itemStyle: {
              color: '#1A1712',
            },
          },
          axisLine: {
            roundCap: false,
            lineStyle: {
              width: 10,
              color: [[1, '#DED6C7']],
            },
          },
          axisTick: {
            distance: -14,
            splitNumber: 2,
            lineStyle: {
              width: 1,
              color: '#6B6053',
            },
          },
          splitLine: {
            distance: -16,
            length: 6,
            lineStyle: {
              width: 1.5,
              color: '#6B6053',
            },
          },
          axisLabel: {
            distance: -12,
            color: '#6B6053',
            fontSize: 9,
            fontFamily: 'Geist Mono, monospace',
            formatter: (v: number) => v.toFixed(1),
          },
          title: {
            show: false,
          },
          detail: {
            valueAnimation: true,
            fontSize: 20,
            fontFamily: 'Geist Mono, monospace',
            fontWeight: 600,
            color: '#1A1712',
            offsetCenter: [0, '25%'],
            formatter: (val: number) => `ε ${val.toFixed(3)}`,
          },
          data: [
            {
              value: Number(spent.toFixed(3)),
            },
          ],
        },
      ],
    }
  }, [spent, safeTotal])

  return (
    <div className="relative rounded-xl border border-line bg-card p-4 shadow-e0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            PRESSURE GAUGE
          </span>
          <span className="font-sans text-xs font-semibold text-ink">ε Budget</span>
        </div>
        <button
          type="button"
          onClick={onOpenExplainer}
          title="Differential privacy accounting formulation"
          className="text-faint hover:text-brass"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>

      <div className="h-36 w-full">
        <EChart option={option} className="h-full w-full" />
      </div>

      <div className="mt-1 flex items-center justify-between border-t border-line/60 pt-2 text-[11px] font-mono">
        <span className="text-muted">
          Spent / Target:
        </span>
        <span className="tnum font-medium text-ink">
          {spent.toFixed(3)} / {safeTotal.toFixed(2)} ({Math.round(ratio * 100)}%)
        </span>
      </div>
      {stage && (
        <div className="mt-1 text-center font-mono text-[10px] text-brass animate-pulse">
          Charging: {stage}
        </div>
      )}
    </div>
  )
}
