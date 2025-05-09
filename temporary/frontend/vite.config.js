// vite.config.js
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Adicionar configuração de teste para Vitest
  test: {
    globals: true, // Permite usar 'describe', 'it', 'expect' globalmente
    environment: "happy-dom", // Usar happy-dom (ou 'jsdom')
    setupFiles: "./src/setupTests.js", // Arquivo de setup (opcional mas recomendado)
    // Incluir arquivos de teste
    include: ["src/**/*.{test,spec}.{js,ts,jsx,tsx}"],
    // Excluir node_modules, etc.
    exclude: ["node_modules", "dist", ".idea", ".git", ".cache", "cypress"], // Exclude cypress folder too
    // Configurar coverage (opcional)
    coverage: {
      provider: "v8", // or 'istanbul'
      reporter: ["text", "json", "html"],
      reportsDirectory: "./coverage",
      include: ["src/**/*.{js,jsx,ts,tsx}"], // Specify files to include in coverage
      exclude: [
        // Specify files/patterns to exclude
        "src/main.jsx",
        "src/App.jsx", // Often App.jsx is just setup
        "src/setupTests.js",
        "src/vite-env.d.ts",
        "src/**/*.test.{js,jsx,ts,tsx}", // Exclude test files themselves
        "src/**/*.spec.{js,jsx,ts,tsx}",
        "src/hooks/useAuth.js", // Example: exclude simple hooks if needed
        "src/hooks/useWebSocket.js",
        "src/context/AuthContext.jsx", // Testing context providers can be tricky for coverage
        "src/context/WebSocketContext.jsx",
        "src/components/ProtectedRoute.jsx", // Basic component
      ],
      all: true, // Report coverage for all files included, even if untested
    },
  },
})
