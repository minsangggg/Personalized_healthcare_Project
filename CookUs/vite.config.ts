import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_URL || 'http://localhost:8600'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/auth': { target, changeOrigin: true },
        '/me': { target, changeOrigin: true },
        '/recipes': { target, changeOrigin: true },
        '/recommendations': { target, changeOrigin: true },
        '/fridge': { target, changeOrigin: true },
        '/ingredients': { target, changeOrigin: true },
        '/shorts': { target, changeOrigin: true },
        '/faq': { target, changeOrigin: true },
        '/nutrition': { target, changeOrigin: true },
        // CookTest (events & posts)
        '/events': { target, changeOrigin: true },
        '/posts': { target, changeOrigin: true },
        '/users': { target, changeOrigin: true },
      },
    },
  }
})
