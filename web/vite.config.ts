import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// The console talks to the FastAPI service. Proxying /api in dev keeps the browser on one
// origin, so nothing here depends on the server's CORS policy being permissive.

// Preload the latin web fonts the first screen uses. Without this they are discovered only once
// the CSS is parsed, arrive after React's first render, and the swap re-wraps the KPI labels:
// every card grew 15 px and Lighthouse measured a 0.54 layout shift. KaTeX's fonts and the
// cyrillic / latin-ext subsets are left to load on demand.
const FIRST_SCREEN_FONTS = /^assets\/(geist-sans-latin-(400|500|600)|geist-mono-latin-(400|500)|instrument-serif-latin-400)-normal-[\w-]+\.woff2$/

function preloadFonts(): Plugin {
  return {
    name: 'synthproof-preload-fonts',
    apply: 'build',
    transformIndexHtml(_html, ctx) {
      return Object.keys(ctx.bundle ?? {})
        .filter((f) => FIRST_SCREEN_FONTS.test(f))
        .sort()
        .map((f) => ({
          tag: 'link',
          attrs: { rel: 'preload', as: 'font', type: 'font/woff2', href: `/${f}`, crossorigin: '' },
          injectTo: 'head' as const,
        }))
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), preloadFonts()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Server-sent events must not be buffered by the proxy or the pipeline log
        // arrives all at once when the run finishes, which defeats the point.
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const contentType = String(proxyRes.headers['content-type'] ?? '')
            if (contentType.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache, no-transform'
            }
          })
        },
      },
    },
  },
  // Built assets land where the FastAPI service already mounts static files, so a
  // production build is served by the same process as the API.
  // Its own directory, not `api/static/`. That folder holds the hand-written legacy console
  // as a tracked source file, and a build with `emptyOutDir` would silently delete it.
  build: {
    outDir: '../synthproof/api/console',
    emptyOutDir: true,
    // The one chunk over the default 500 kB is three.js itself (~980 kB), a single library that
    // is now loaded only when the 3D chamber renders (React.lazy in App.tsx), never on first paint.
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Vendor chunks, each cacheable across deploys. A function, not the object form: the
        // object form let rollup put React (a dependency three/fiber shares) INSIDE the three
        // chunk, so the entry imported React from it and three.js (~980 kB) was preloaded on
        // first paint even though the chamber is lazy.
        manualChunks(id) {
          // Vite's own dynamic-import helper. Left to rollup, it landed in the three chunk (drei
          // uses dynamic imports), and every lazy import then pulled three.js in with it.
          if (id.includes('vite/preload-helper')) return 'react'
          if (!id.includes('node_modules')) return undefined
          if (/node_modules[\/](react|react-dom|scheduler)[\/]/.test(id)) return 'react'
          if (/node_modules[\/](three|@react-three|three-stdlib)[\/]/.test(id)) return 'three'
          if (/node_modules[\/](framer-motion|motion-dom|motion-utils)[\/]/.test(id)) return 'motion'
          if (/node_modules[\/](echarts|echarts-for-react|zrender)[\/]/.test(id)) return 'echarts'
          if (/node_modules[\/]katex[\/]/.test(id)) return 'katex'
          return undefined
        },
      },
    },
  },
})
