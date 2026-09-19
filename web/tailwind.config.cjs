module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F6F3",
        surface: "#FFFFFF",
        line: "#E4E4DF",
        "line-strong": "#D5D5CE",
        ink: "#17181C",
        muted: "#6C6F77",
        faint: "#9A9CA3",
        danger: "#C8402F",
        ok: "#3E7C4F",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Space Grotesk"', "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: { DEFAULT: "8px", lg: "12px", xl: "16px" },
      boxShadow: {
        card: "0 1px 2px rgba(23,24,28,0.04)",
        pop: "0 20px 50px -20px rgba(23,24,28,0.22)",
      },
    },
  },
  plugins: [],
};
