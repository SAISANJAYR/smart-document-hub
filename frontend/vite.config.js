import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, /api and /health are proxied to FastAPI so the app runs on one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/docs': 'http://localhost:8000',
      '/openapi.json': 'http://localhost:8000',
    },
  },
})
