import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Backend runs on :8000. Proxying in dev keeps the browser same-origin, so
    // the HttpOnly refresh cookie behaves exactly as it will in production.
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
});
