import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_URL || 'http://localhost:8600'

  console.log(target)

  return {
    plugins: [react()],
    server: {
      proxy: {
        // '/auth/.*': { target, changeOrigin: true },
        '/auth/login': { target, changeOrigin: true },
        '/auth/logout': { target, changeOrigin: true },
        '/auth/signup': { target, changeOrigin: true },
        '/auth/refresh': { target, changeOrigin: true },
        '/auth/find-id': { target, changeOrigin: true },
        '/auth/find-id/verify': { target, changeOrigin: true },
        '/auth/find-password': { target, changeOrigin: true },
        '/auth/password-set': { target, changeOrigin: true },
        '/me': { target, changeOrigin: true },
        '/recipes': { target, changeOrigin: true },
        '/recommendations': { target, changeOrigin: true },
        '/fridge': { target, changeOrigin: true },
        '/ingredients': { target, changeOrigin: true },
        '/faq': { target, changeOrigin: true },
      },
    },
  }
})
