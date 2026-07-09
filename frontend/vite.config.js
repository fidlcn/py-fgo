import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Dev: proxy API + WebSocket to the FastAPI backend on :8765.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/api": "http://localhost:8765",
            "/ws": { target: "ws://localhost:8765", ws: true },
            "/health": "http://localhost:8765",
        },
    },
});
