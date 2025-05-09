// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paleta VoulezVous/Fusion (Ajuste as cores HEX reais)
        "fusion-deep": "#111827", // Quase preto para fundo principal
        "fusion-dark": "#1f2937", // Cinza escuro para menus/cards
        "fusion-medium": "#374151", // Cinza médio para bordas/hover
        "fusion-light": "#6b7280", // Cinza claro para texto secundário/ícones
        "fusion-text-primary": "#f9fafb", // Texto principal (branco suave)
        "fusion-text-secondary": "#d1d5db", // Texto secundário (cinza mais claro)
        "fusion-purple": "#8b5cf6", // Roxo principal (Vivid Violet)
        "fusion-purple-hover": "#7c3aed",
        "fusion-purple-light": "#a78bfa",
        "fusion-pink": "#ec4899", // Rosa/Magenta para acentos
        "fusion-teal": "#14b8a6", // Turquesa para acentos/sucesso
        "fusion-blue": "#3b82f6", // Azul para links/info
        "fusion-success": "#10b981", // Verde
        "fusion-warning": "#f59e0b", // Laranja/Amarelo
        "fusion-error": "#ef4444", // Vermelho
      },
      fontFamily: {
        // Exemplo: usar Inter. Instale e importe via CSS se usar.
        // sans: ['Inter', 'ui-sans-serif', 'system-ui', /* ... */],
      },
      keyframes: {
        pulseLight: {
          "0%, 100%": { opacity: 1, backgroundColor: "currentColor" }, // Usar currentColor
          "50%": { opacity: 0.7, backgroundColor: "currentColor" },
        },
      },
      animation: {
        "pulse-light": "pulseLight 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [
    // Plugin para estilizar scrollbars (opcional, mas recomendado)
    // Instalar: npm install -D tailwind-scrollbar
    require("tailwind-scrollbar")({ nocompatible: true }),
  ],
}
