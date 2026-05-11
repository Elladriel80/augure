import fs from "node:fs/promises";
import path from "node:path";

import type { PredictorManifest } from "./manifest";

let cached: PredictorManifest | null = null;

/**
 * Read `public/predictor_manifest.json` from the build output. Server-only —
 * touches `node:fs`, must never be imported by a client component.
 */
export async function loadManifest(): Promise<PredictorManifest | null> {
  if (cached) return cached;
  const manifestPath = path.join(
    process.cwd(),
    "public",
    "predictor_manifest.json",
  );
  try {
    const raw = await fs.readFile(manifestPath, "utf-8");
    cached = JSON.parse(raw) as PredictorManifest;
    return cached;
  } catch {
    return null;
  }
}
