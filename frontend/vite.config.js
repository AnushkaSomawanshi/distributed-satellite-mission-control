import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In Docker Compose, backend service is 'http://mission-control:8000'.
// When running locally outside Docker, backend host is 'http://127.0.0.1:8000'.
const backendTarget = process.env.VITE_BACKEND_TARGET || process.env.BACKEND_URL || 'http://mission-control:8000';
const wsTarget = backendTarget.replace('http://', 'ws://').replace('https://', 'wss://');

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: wsTarget,
        ws: true,
        changeOrigin: true
      }
    }
  }
})
