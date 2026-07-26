import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(__dirname, "..", "backend");
const dst = path.resolve(__dirname, "backend");

if (!fs.existsSync(dst)) {
  fs.cpSync(src, dst, {
    recursive: true,
    filter: (srcPath) => {
      const rel = path.relative(src, srcPath);
      const parts = rel.split(path.sep);
      const skip = ["venv", "venv_win", "__pycache__", ".git", "node_modules"];
      return !skip.some((s) => parts.includes(s));
    },
  });
}
