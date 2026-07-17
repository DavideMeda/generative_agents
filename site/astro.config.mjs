import { defineConfig } from "astro/config";

// GitHub Pages: https://davidemeda.github.io/new-gen-agent/
export default defineConfig({
  site: "https://davidemeda.github.io",
  base: "/new-gen-agent",
  outDir: "dist",
  trailingSlash: "always",
});
