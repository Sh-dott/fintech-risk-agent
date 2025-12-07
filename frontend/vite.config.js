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
      '/health': 'http://localhost:8000',
      '/score': 'http://localhost:8000',
      '/batch-score': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/analytics': 'http://localhost:8000',
      '/upload-and-analyze': 'http://localhost:8000',
      '/analyze-transactions': 'http://localhost:8000',
    },
  },
})
