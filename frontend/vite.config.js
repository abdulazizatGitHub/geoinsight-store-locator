import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy /stores/* → FastAPI on port 8000
      // Eliminates CORS issues during development
      '/stores': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
