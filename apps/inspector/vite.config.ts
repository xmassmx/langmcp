import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [viteSingleFile()],
  root,
  build: {
    outDir: path.resolve(root, "../../src/langmcp/apps"),
    emptyOutDir: false,
    rollupOptions: {
      input: path.resolve(root, "inspector.html"),
    },
  },
});
