import { useEffect, useRef } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface EChartProps {
  option: EChartsOption
  style?: React.CSSProperties
  className?: string
  loading?: boolean
  onEvents?: Record<string, (params: any) => void>
}

export function EChart({ option, style, className, loading = false, onEvents }: EChartProps) {
  const chartRef = useRef<ReactECharts>(null)

  // Listen for dark mode / theme changes on <html>
  useEffect(() => {
    const observer = new MutationObserver(() => {
      chartRef.current?.getEchartsInstance().resize()
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] })
    return () => observer.disconnect()
  }, [])

  return (
    <div className={`relative w-full ${className || ''}`} style={style}>
      <ReactECharts
        ref={chartRef}
        option={option}
        notMerge={true}
        lazyUpdate={true}
        showLoading={loading}
        loadingOption={{
          text: '',
          color: '#8A5A2B',
          maskColor: 'transparent',
        }}
        style={{ height: '100%', width: '100%' }}
        onEvents={onEvents}
      />
    </div>
  )
}
