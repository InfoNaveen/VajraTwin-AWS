/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // VajraTwin dark aerospace palette
        gcs: {
          bg:        "#0a0e1a",   // deep navy — main background
          surface:   "#111827",   // card surface
          border:    "#1f2937",   // subtle borders
          muted:     "#374151",   // disabled / secondary elements
          text:      "#e5e7eb",   // primary text
          subtext:   "#9ca3af",   // secondary text
          accent:    "#3b82f6",   // electric blue — active elements
          accentHov: "#2563eb",
        },
        advisory: {
          go:        "#22c55e",   // green
          monitor:   "#eab308",   // yellow
          derate:    "#f97316",   // orange
          maint:     "#ef4444",   // red
        },
        telemetry: {
          rpm:  "#60a5fa",  // blue
          map:  "#a78bfa",  // violet
          egt:  "#f97316",  // orange
          cht:  "#34d399",  // emerald
          dEgt: "#fb923c",  // delta EGT line
          dCht: "#38bdf8",  // delta CHT line
        },
      },
      fontFamily: {
        mono:  ["'JetBrains Mono'", "'Courier New'", "monospace"],
        sans:  ["'Inter'", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "blink":      "blink 1s step-end infinite",
        "fade-in":    "fadeIn 0.4s ease-in-out",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
