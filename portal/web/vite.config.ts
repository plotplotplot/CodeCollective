import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'serve' ? '/dev/' : (process.env.VITE_PUBLIC_BASE || '/'),
  optimizeDeps: {
    exclude: ['pg']
  },
  server: {
    allowedHosts: ['ballot-vm.local', 'ballot.arkavo.org', 'portal.arkavo.org', 'localhost'],
    host: true,
    hmr: {
      // Use the actual host from the browser, not localhost
      host: 'portal.arkavo.org',
      protocol: 'wss',
      clientPort: 443,
    },
    proxy: {
      '/pidp': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/pidp/, ''),
      },
      '/api/governance': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
}))
