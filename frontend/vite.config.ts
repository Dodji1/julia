import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // 127.0.0.1 plutôt que localhost : sous Windows, localhost tente d'abord IPv6.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
    // Partage du serveur de développement par un tunnel ngrok.
    allowedHosts: ['.ngrok-free.app', '.ngrok.app'],
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
