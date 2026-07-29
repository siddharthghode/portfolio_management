import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    // Tailwind v4 uses a Vite plugin instead of a PostCSS config.
    // This replaces the old tailwind.config.js + postcss.config.js setup.
    tailwindcss(),
  ],

  // Proxy /api/* requests to Django during development.
  // This avoids CORS issues — the browser talks to Vite (port 5173),
  // Vite forwards /api/* to Django (port 8000) server-side.
  // In production, Nginx or a reverse proxy handles this instead.
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
