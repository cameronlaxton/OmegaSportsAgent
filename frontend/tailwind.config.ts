import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        omega: {
          50: "#f0fdf4",
          500: "#22c55e",
          600: "#16a34a",
          900: "#0a1f0d",
        },
        edge: {
          positive: "#22c55e",
          negative: "#ef4444",
          neutral: "#6b7280",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
