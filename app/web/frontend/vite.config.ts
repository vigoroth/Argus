import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev: vite on :5173 proxies API to FastAPI on :8000
// prod: `npm run build` → dist/ served by FastAPI
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/chat': 'http://localhost:8000',
      '/conversations': 'http://localhost:8000',
      '/models': 'http://localhost:8000',
      '/graph': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/login': 'http://localhost:8000',
      '/logout': 'http://localhost:8000',
      '/term': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
