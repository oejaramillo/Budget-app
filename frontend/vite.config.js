import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The backend allows http://localhost:5173 in CORS_ALLOWED_ORIGINS, so keep
    // the port predictable. Remove strictPort if you need Vite to pick another.
    strictPort: true,
    open: false,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
