import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.API_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        '/api': apiTarget,
        '/outputs': apiTarget,
      },
    },
    build: {
      outDir: '../backend/static',
      emptyOutDir: true,
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/setupTests.ts',
    },
  }
})
