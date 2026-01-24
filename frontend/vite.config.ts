import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// API URL: Use env var for local dev, fall back to Docker service name
const apiTarget = process.env.VITE_API_URL || 'http://backend:18080'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 15173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
