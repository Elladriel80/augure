import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0d10",
        panel: "#13171c",
        border: "#1f262e",
        muted: "#6b7480",
        text: "#e4e8ec",
        accent: "#5fa8d3",
        accent2: "#a48dff",
        ok: "#3fb27f",
        warn: "#e2b341",
        err: "#e25b5b",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
