import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { mockBackendPlugin } from './e2e/mock-backend';

// The deterministic mock backend is mounted ONLY for E2E runs
// (playwright.config.ts sets ULTRONE_MOCK_BACKEND=1 on its webServer).
// Normal `npm run dev` keeps proxying /api to the real FastAPI backend.
const e2eMock = process.env.ULTRONE_MOCK_BACKEND === '1';

export default defineConfig({
  plugins: [react(), ...(e2eMock ? [mockBackendPlugin()] : [])],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
