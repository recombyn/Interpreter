import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

const APP_URL = process.env.VITE_APP_URL || 'https://github.com/recombyn/concept-network-interpreter'
/** GitHub Pages project site: `/concept-network-interpreter/`. Local: `/`. */
const BASE = process.env.VITE_DOCS_BASE || '/'

export default defineConfig({
  base: BASE.endsWith('/') ? BASE : `${BASE}/`,
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  define: {
    __APP_URL__: JSON.stringify(APP_URL),
  },
  server: {
    host: '127.0.0.1',
    port: 5175,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
  },
})
