import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

/**
 * The pitch deck is a second, standalone Vite app rooted at `web/pitch/`.
 *
 * It deliberately does NOT extend the console's config. The console proxies `/api` to a live
 * FastAPI service; a deck that depends on a running backend is a deck that dies in the room
 * when the laptop has no server up. Every number here is baked in at build time from
 * `data.ts`, so this app makes no network request of any kind once loaded — which is also
 * what makes it safe to present offline.
 *
 * Dependencies (react, framer-motion, @fontsource/*) resolve from `web/node_modules` by
 * Node's normal upward lookup, so there is nothing extra to install.
 */
export default defineConfig({
  root: __dirname,
  plugins: [react()],
  resolve: { alias: { '@pitch': path.resolve(__dirname) } },
  server: { port: 5174 },
  build: {
    // Its own directory. The console builds to `synthproof/api/console` with
    // `emptyOutDir`, so sharing an output folder would have one build delete the other.
    outDir: path.resolve(__dirname, '../../synthproof/api/pitch'),
    emptyOutDir: true,
    // Fonts and the results payload are inlined where small enough; nothing is fetched
    // from a CDN, so the built deck runs from a file server with no internet at all.
    //
    // `SYNTHPROOF_INLINE_ALL=1` raises the limit far enough to swallow every font file as a
    // data: URI. That is how `build_standalone.py` produces the single-file deck: a woff2
    // referenced by a relative URL is blocked by CORS when the page is opened over file://,
    // so a double-clickable build has to carry its fonts inside the stylesheet.
    assetsInlineLimit: process.env.SYNTHPROOF_INLINE_ALL === '1' ? 512_000 : 4096,
    // For the single-file build, emit a CLASSIC script rather than an ES module. Chrome
    // applies CORS to module scripts and treats a file:// page as an opaque origin, so a
    // double-clicked module deck is at the mercy of how the browser classifies an inline
    // module. An IIFE has no module semantics at all and simply runs. `modulePreload` is
    // disabled with it because a preload link would be a fetch, and fetches are the one
    // thing a file:// page cannot do.
    modulePreload: process.env.SYNTHPROOF_INLINE_ALL === '1' ? false : undefined,
    rollupOptions:
      process.env.SYNTHPROOF_INLINE_ALL === '1'
        ? { output: { format: 'iife', inlineDynamicImports: true } }
        : undefined,
  },
})
