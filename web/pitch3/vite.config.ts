import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

/** Six-slide deck. Independent of the other two: own root, own port, own build output. */
export default defineConfig({
  root: __dirname,
  plugins: [react()],
  server: { port: 5176 },
  build: {
    outDir: path.resolve(__dirname, '../../synthproof/api/pitch3'),
    emptyOutDir: true,
    // The single-file build inlines fonts as data URIs and emits a classic script: a page
    // opened from disk cannot fetch anything, and CORS applies to module scripts.
    assetsInlineLimit: process.env.SYNTHPROOF_INLINE_ALL === '1' ? 512_000 : 4096,
    modulePreload: process.env.SYNTHPROOF_INLINE_ALL === '1' ? false : undefined,
    rollupOptions:
      process.env.SYNTHPROOF_INLINE_ALL === '1'
        ? { output: { format: 'iife', inlineDynamicImports: true } }
        : undefined,
  },
})
