import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Développement uniquement : relaie /api et /media vers le backend Django (même origine,
// donc ni CORS ni cookie tiers). Sans VITE_API_BASE_URL, le site n'appelle jamais /api.
const target = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';
const proxy = { '/api': { target }, '/media': { target } };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
});
