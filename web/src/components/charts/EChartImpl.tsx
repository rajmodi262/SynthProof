import { useEffect, useRef } from 'react'
import ReactECharts from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { BarChart, GaugeChart, ScatterChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

// Only what the console draws (gauge, bars, scatter). Importing 'echarts' whole pulled every
// chart type and component into the main bundle: about 1 MB of the 1.5 MB it weighed.
echarts.use([BarChart, GaugeChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

export interface EChartProps {
  option: EChartsOption
  style?: React.CSSProperties
  className?: string
  loading?: boolean
  onEvents?: Record<string, (params: any) => void>
}

export default function EChartImpl({ option, style, className, loading = false, onEvents }: EChartProps) {
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
        echarts={echarts}
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
