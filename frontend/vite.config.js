import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Dev: proxy API + WebSocket to the FastAPI backend on :8765.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/api": "http://127.0.0.1:8765",
            "/ws": { target: "ws://127.0.0.1:8765", ws: true },
            "/health": "http://127.0.0.1:8765",
        },
    },
});
