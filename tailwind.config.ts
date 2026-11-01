import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#080b12",
        panel: "#101621",
        line: "#202b3b",
        signal: "#44e6a1",
        danger: "#ff5d70",
        warning: "#ffc857"
      },
      boxShadow: {
        glow: "0 0 32px rgba(68, 230, 161, 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
