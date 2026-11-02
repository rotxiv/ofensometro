import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// El navegador siempre llama a /api (mismo origen). Quién atiende esa ruta depende de cómo corras:
//   npm run dev / npm run preview  -> Vite la reenvía a VITE_API_TARGET (este archivo)
//   Docker                         -> nginx la reenvía a API_UPSTREAM (ver nginx.conf.template)
// VITE_API_TARGET se puede definir en el entorno o en un archivo .env (ver .env.example).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // 127.0.0.1 y no "localhost": evita que Node pruebe primero IPv6 (::1) y falle si la API solo
  // escucha en IPv4, que es lo habitual con uvicorn.
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8000";
  const proxy = { "/api": { target: apiTarget, changeOrigin: true } };

  return {
    plugins: [react()],
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/setupTests.js"],
      css: false,
    },
  };
});
