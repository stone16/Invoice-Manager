import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Use environment variable for API target, default to localhost for local dev
const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
