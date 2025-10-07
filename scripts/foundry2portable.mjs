#!/usr/bin/env node
// Portable → Foundry

// Normalize Foundry exports to a portable web-friendly JSON
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, basename } from "node:path";

const [, , inPath, outDir] = process.argv;
if (!inPath || !outDir) {
  console.error("Usage: node scripts/etl-export.mjs <foundry.json> <outDir>");
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });

const raw = JSON.parse(readFileSync(inPath, "utf8"));
function toPortable(doc) {
  const { _id, _key, _documentClass, flags, ...rest } = doc;
  return {
    ...rest,
    meta: {
      source: "foundry",
      class: _documentClass || null,
      name: rest.name
    }
  };
}
const portable = Array.isArray(raw) ? raw.map(toPortable) : toPortable(raw);
const out = join(outDir, basename(inPath).replace(/\.json$/i, ".portable.json"));
writeFileSync(out, JSON.stringify(portable, null, 2));
console.log("Wrote", out);
