import { useState } from 'react'
import type { ReactNode } from 'react'

/**
 * Two views of one idea, on one slide.
 *
 * Used where a claim needs both an explanation and a thing the panel can break themselves.
 * Splitting those into separate slides would push the deck past ten; stacking them would
 * push the second one below the fold on a 720p projector.
 */
export function Tabs({ tabs }: { tabs: Array<{ label: string; node: ReactNode }> }) {
  const [i, setI] = useState(0)
  return (
    <div style={{ display: 'grid', gap: '0.85rem' }}>
      <div role="tablist" style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
        {tabs.map((t, n) => (
          <button
            key={t.label}
            role="tab"
            aria-selected={i === n}
            className="btn"
            data-on={i === n ? '1' : '0'}
            onClick={() => setI(n)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">{tabs[i].node}</div>
    </div>
  )
}
