import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Bundled, never fetched. 800/900 are load-bearing: the title rasterises the word to a
// canvas at weight 900, and without the real face the browser falls back and the letters
// never form.
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/500.css'
import '@fontsource/geist-sans/700.css'
import '@fontsource/geist-sans/800.css'
import '@fontsource/geist-sans/900.css'
import '@fontsource/geist-mono/400.css'
import '@fontsource/geist-mono/500.css'
import './styles.css'

import { Deck } from './Deck'

createRoot(document.getElementById('pitch-root')!).render(
  <StrictMode>
    <Deck />
  </StrictMode>,
)
