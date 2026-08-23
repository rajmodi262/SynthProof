import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Bundled, never fetched. 900 is load-bearing: slide 1 rasterises the wordmark to a canvas at
// that weight, and without the real face it falls back and the letters never form.
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/500.css'
import '@fontsource/geist-sans/600.css'
import '@fontsource/geist-sans/700.css'
import '@fontsource/geist-sans/800.css'
import '@fontsource/geist-sans/900.css'
import '@fontsource/geist-mono/400.css'
import '@fontsource/geist-mono/500.css'
import './styles.css'

import { Deck } from './Deck'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Deck />
  </StrictMode>,
)
