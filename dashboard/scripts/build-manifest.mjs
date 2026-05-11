// Cross-platform shim for the predictor manifest builder. Runs the Python
// script that aggregates training runs + feature registry + paper-bet
// counters into `public/predictor_manifest.json`. Invoked by the `prebuild`
// npm hook so Vercel and local builds always ship a fresh manifest.
//
// Tries `python3` first (Vercel / Linux / macOS) and falls back to `python`
// (Windows default). Exits non-zero if no interpreter is found or the script
// itself fails — fail-loud beats shipping a stale dashboard.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const scriptPath = path.resolve(
  here,
  "..",
  "..",
  "predictor",
  "scripts",
  "build_dashboard_manifest.py"
);

if (!existsSync(scriptPath)) {
  console.error(`[manifest] predictor script not found at ${scriptPath}`);
  process.exit(1);
}

const candidates =
  process.platform === "win32" ? ["python", "py", "python3"] : ["python3", "python"];

let lastError = null;
for (const cmd of candidates) {
  const result = spawnSync(cmd, [scriptPath], { stdio: "inherit", shell: false });
  if (result.error && result.error.code === "ENOENT") {
    lastError = result.error;
    continue;
  }
  process.exit(result.status ?? 0);
}

console.error(
  `[manifest] no python interpreter found (tried: ${candidates.join(", ")}). ` +
    `Install python3 or set it on PATH. Last error: ${lastError?.message ?? "unknown"}.`
);
process.exit(1);
