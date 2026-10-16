import { Suspense, lazy } from 'react'
import type { EChartProps } from './EChartImpl'

// ECharts (~570 kB) is fetched only when a chart first renders, so it is off the critical path
// to first paint. On Lighthouse's mobile profile it was the largest script blocking the
// first render of the console.
const EChartImpl = lazy(() => import('./EChartImpl'))

export function EChart(props: EChartProps) {
  return (
    <Suspense fallback={<div className={`relative w-full ${props.className || ''}`} style={props.style} />}>
      <EChartImpl {...props} />
    </Suspense>
  )
}
