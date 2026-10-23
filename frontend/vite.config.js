import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// During development the browser talks to Vite (port 5173); Vite forwards /api calls to the
// FastAPI backend (port 8000). The frontend code therefore uses relative URLs like /api/health
// and needs no CORS or address changes when the app is deployed behind one domain.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
});
