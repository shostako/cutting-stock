import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// http.py は CORS 無し。dev は proxy で同一オリジンに見せる（フロントは相対パスで fetch）。
const API = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/solve': API,
      '/validate': API,
      '/healthz': API,
    },
  },
})
