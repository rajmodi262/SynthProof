import { useMemo } from 'react'
import { EChart } from './charts/EChart'
import type { Histogram } from '@/types'
import type { EChartsOption } from 'echarts'

function HistogramSpark({ hist, name }: { hist: Histogram; name: string }) {
  const real = Array.isArray(hist.real) ? hist.real : []
  const synthetic = Array.isArray(hist.synthetic) ? hist.synthetic : []
  const edges = Array.isArray(hist.edges) ? hist.edges : []

  const labels = useMemo(() => {
    if (edges.length < 2) return []
    return edges.slice(0, -1).map((e, idx) => {
      const next = edges[idx + 1]
      return `${Math.round(e)}-${Math.round(next)}`
    })
  }, [edges])

  const option: EChartsOption = useMemo(() => {
    return {
      grid: {
        left: 2,
        right: 2,
        top: 6,
        bottom: 18,
        containLabel: false,
      },
      tooltip: {
        trigger: 'axis',
        textStyle: {
          fontFamily: 'Geist Mono, monospace',
          fontSize: 11,
          color: '#1A1712',
        },
        backgroundColor: '#FBFAF6',
        borderColor: '#DED6C7',
        borderWidth: 1,
        padding: [4, 8],
      },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#DED6C7' } },
        axisTick: { show: false },
        axisLabel: {
          show: true,
          interval: 'auto',
          fontSize: 8,
          color: '#9A8F7E',
          fontFamily: 'Geist Mono, monospace',
        },
      },
      yAxis: {
        type: 'value',
        show: false,
      },
      series: [
        {
          name: 'Real',
          type: 'bar',
          data: real,
          barGap: '-100%',
          itemStyle: {
            color: 'transparent',
            borderColor: '#1A1712',
            borderWidth: 1,
          },
          z: 2,
        },
        {
          name: 'Synthetic',
          type: 'bar',
          data: synthetic,
          itemStyle: {
            color: 'rgba(138, 90, 43, 0.45)', // Brass 45% fill
            borderColor: '#8A5A2B',
            borderWidth: 1,
          },
          z: 1,
        },
      ],
    }
  }, [labels, real, synthetic])

  if (!real.length || synthetic.length !== real.length) {
    return (
      <div className="py-2">
        <span className="font-mono text-[11px] font-medium text-ink">{name}</span>
        <p className="font-mono text-[10px] text-faint">histogram unavailable</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-line/70 bg-paper-2/40 p-2">
      <div className="mb-1 flex items-baseline justify-between font-mono text-[11px]">
        <span className="font-medium text-ink">{name}</span>
        <span className="text-[10px] text-faint">
          {edges[0]?.toFixed(0)} → {edges[edges.length - 1]?.toFixed(0)}
        </span>
      </div>
      <div className="h-16 w-full">
        <EChart option={option} className="h-full w-full" />
      </div>
      {typeof hist.synthetic_out_of_range === 'number' && hist.synthetic_out_of_range > 0.005 && (
        <p className="mt-0.5 font-mono text-[9px] text-brass">
          {(hist.synthetic_out_of_range * 100).toFixed(1)}% outside real range
        </p>
      )}
    </div>
  )
}

export function Marginals({
  histograms,
  maxColumns = 3,
  onOpenExplainer,
}: {
  histograms: Record<string, Histogram>
  maxColumns?: number
  onOpenExplainer?: () => void
}) {
  const entries = Object.entries(histograms).slice(0, maxColumns)
  if (!entries.length) return null

  return (
    <div className="relative rounded-xl border border-line bg-card p-4 shadow-e0">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
              STATISTICAL FIDELITY
            </span>
            <span className="font-sans text-xs font-semibold text-ink">Marginal Distributions</span>
          </div>
          <p className="mt-0.5 font-sans text-[11px] text-muted">Real (outline) vs Synthetic (brass)</p>
        </div>
        {onOpenExplainer && (
          <button
            type="button"
            onClick={onOpenExplainer}
            title="Statistical fidelity and utility definition"
            className="text-faint hover:text-brass"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        )}
      </div>

      <div className="space-y-2.5">
        {entries.map(([name, hist]) => (
          <HistogramSpark key={name} name={name} hist={hist} />
        ))}
      </div>
    </div>
  )
}
