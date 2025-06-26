import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vite.dev/config/
export default defineConfig({
  define: {
    // Provide a polyfill for process.nextTick, as simple-peer seems to require it directly
    'process.nextTick': '(function(callback) { setTimeout(callback, 0); })',
  },
  plugins: [
    react(),
    nodePolyfills({
      // Optionally, specify which polyfills to include or exclude
      // For example, to ensure stream, process, and buffer are polyfilled:
      protocolImports: true, // if you're using node builtins with `node:` prefix
    }),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'GGDC Patient Portal',
        short_name: 'GGDC Patient',
        description: 'Gemini Genius Diabetes Center - Patient Portal PWA',
        theme_color: '#2e7d8c',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      }
    })
  ],
})
