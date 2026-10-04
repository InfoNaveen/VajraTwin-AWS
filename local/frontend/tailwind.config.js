/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        gcs: {
          bg:      "#0a0e1a",
          surface: "#111827",
          border:  "#1f2937",
          muted:   "#374151",
          text:    "#e5e7eb",
          sub:     "#9ca3af",
          accent:  "#3b82f6",
        },
        adv: {
          go:      "#22c55e",
          monitor: "#eab308",
          derate:  "#f97316",
          maint:   "#ef4444",
        },
        tel: {
          rpm:  "#60a5fa",
          map:  "#a78bfa",
          egt:  "#f97316",
          cht:  "#34d399",
          dEgt: "#fb923c",
          dCht: "#38bdf8",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "monospace"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-in":    "fadeIn 0.35s ease-in-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0", transform: "translateY(5px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
