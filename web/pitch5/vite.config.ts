import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

/**
 * The cinematic deck — a second, independent pitch app.
 *
 * Deliberately separate from `web/pitch/` in every way that matters: its own root, its own
 * port, its own build output. Editing one cannot break the other, and both can be presented
 * from the same machine on the same day.
 */
export default defineConfig({
  root: __dirname,
  plugins: [react()],
  server: { port: 5178 },
  build: {
    outDir: path.resolve(__dirname, '../../synthproof/api/pitch5'),
    emptyOutDir: true,
    // See build_standalone.py: the single-file build inlines fonts as data URIs and emits a
    // classic script, because a page opened from disk cannot fetch anything and CORS applies
    // to module scripts.
    assetsInlineLimit: process.env.SYNTHPROOF_INLINE_ALL === '1' ? 512_000 : 4096,
    modulePreload: process.env.SYNTHPROOF_INLINE_ALL === '1' ? false : undefined,
    rollupOptions:
      process.env.SYNTHPROOF_INLINE_ALL === '1'
        ? { output: { format: 'iife', inlineDynamicImports: true } }
        : undefined,
  },
})
