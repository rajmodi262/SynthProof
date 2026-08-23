import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Fonts are bundled, not fetched. A CDN link would make the deck depend on the venue's
// wifi, and a silent fallback to a system serif would quietly undo the whole type design.
import '@fontsource/instrument-serif/400.css'
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/500.css'
// 700/800/900 are used by headings and by the particle title, which rasterises the word to a
// canvas at weight 900. Without the real faces the browser synthesises bold for CSS and falls
// back outright in canvas, and the letters never form.
import '@fontsource/geist-sans/700.css'
import '@fontsource/geist-sans/800.css'
import '@fontsource/geist-sans/900.css'
import '@fontsource/geist-mono/400.css'
import './styles.css'

import { Deck } from './Deck'

createRoot(document.getElementById('pitch-root')!).render(
  <StrictMode>
    <Deck />
  </StrictMode>,
)
