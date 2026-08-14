import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// The console talks to the FastAPI service. Proxying /api in dev keeps the browser on one
// origin, so nothing here depends on the server's CORS policy being permissive.
export default defineConfig({
  plugins: [react()],
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
    rollupOptions: {
      output: {
        // Three.js is ~700 kB of the bundle and never changes between our builds. Splitting
        // it out lets the browser cache it across deploys instead of re-fetching the whole
        // app every time a component changes.
        manualChunks: {
          three: ['three', '@react-three/fiber', '@react-three/drei'],
          motion: ['framer-motion'],
        },
      },
    },
  },
})
