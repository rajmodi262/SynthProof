import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

/** Nine-slide review deck. Independent of the other three: own root, port and output. */
export default defineConfig({
  root: __dirname,
  plugins: [react()],
  server: { port: 5177 },
  build: {
    outDir: path.resolve(__dirname, '../../synthproof/api/pitch4'),
    emptyOutDir: true,
    // Single-file build: inline fonts as data URIs and emit a classic script. A page opened
    // from disk cannot fetch anything, and CORS applies to module scripts.
    assetsInlineLimit: process.env.SYNTHPROOF_INLINE_ALL === '1' ? 512_000 : 4096,
    modulePreload: process.env.SYNTHPROOF_INLINE_ALL === '1' ? false : undefined,
    rollupOptions:
      process.env.SYNTHPROOF_INLINE_ALL === '1'
        ? { output: { format: 'iife', inlineDynamicImports: true } }
        : undefined,
  },
})
