import path from 'node:path'
import { defineConfig } from 'vitest/config'

// Kept separate from vite.config.ts so the production build has no test dependencies in its
// graph, and so a broken test config can never affect `npm run build`.
export default defineConfig({
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
