import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': process.env.BACKEND_API_URL || 'http://127.0.0.1:5000',
      '/download-attendance': process.env.BACKEND_API_URL || 'http://127.0.0.1:5000',
    },
  },
})
