// diabetes_frontend/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { nodePolyfills } from 'vite-plugin-node-polyfills';

export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
        protocolImports: true, 
        globals: {
            Buffer: true, 
            global: true, // <-- ΣΗΜΑΝΤΙΚΟ
            process: true, 
        },
    }),
  ],
  define: {
    'global': 'globalThis', // Ορίζουμε το global ρητά
  },
   optimizeDeps: {
     esbuildOptions: {
       define: {
         global: 'globalThis' 
       },
       // plugins: [ ... αν χρειαστεί για CJS dependencies ... ]
     },
   },
   build: {
       rollupOptions: {
           plugins: [
               // nodePolyfills(), // Ίσως χρειαστεί και εδώ για το build
           ],
       },
   },
});