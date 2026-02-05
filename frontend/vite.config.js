import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        classic: resolve(__dirname, 'classic.html'),
        enhanced: resolve(__dirname, 'enhanced.html'),
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // Proxy all API endpoints to backend
      '^/(health|score|batch-score|metrics|history|analytics|upload-and-analyze|analyze-transactions|fraud-rings)': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
