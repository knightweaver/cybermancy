#!/usr/bin/env node
// Foundry → Portable

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, basename } from "node:path";
import { randomUUID, createHash } from "node:crypto";

const [, , inPath, outDir, docClass = "Item"] = process.argv;
if (!inPath || !outDir) {
  console.error("Usage: node scripts/etl-import.mjs <portable.json> <outDir> [Item|Actor]");
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });
const input = JSON.parse(readFileSync(inPath, "utf8"));
const arr = Array.isArray(input) ? input : [input];

function stableKey(name) {
  return createHash("sha1").update(name).digest("base64url").slice(0, 12);
}

const outDocs = arr.map(p => {
  const { meta, ...rest } = p;
  const name = rest.name || meta?.name || "Unnamed";
  return {
    ...rest,
    _id: randomUUID(),
    _key: stableKey(`${docClass}:${rest.type || ""}:${name}`),
    _documentClass: docClass
  };
});

const out = join(outDir, basename(inPath).replace(/\.portable\.json$/i, ".foundry.json"));
writeFileSync(out, JSON.stringify(outDocs.length === 1 ? outDocs[0] : outDocs, null, 2));
console.log("Wrote", out);
