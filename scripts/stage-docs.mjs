#!/usr/bin/env node
import { readdirSync, statSync, readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join, resolve, dirname, extname, relative } from "node:path";
import { createHash, randomUUID } from "node:crypto";

const SOURCES = [
  { src: "src-data/items", out: "stage/items", docClass: "Item" },
  { src: "src-data/actors", out: "stage/actors", docClass: "Actor" },
  { src: "src-data/domains", out: "stage/domains", docClass: "Item" }, // modelled as Item type=domain
  { src: "src-data/folders", out: "stage/folders", docClass: "Folder" } // optional; see note in pack/direct
];

const VOLATILE_KEYS = new Set(["_stats", "folderPath", "ownership", "sort", "effects"]);
const CLEAN = (obj) => {
  if (Array.isArray(obj)) return obj.map(CLEAN);
  if (obj && typeof obj === "object") {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (VOLATILE_KEYS.has(k)) continue;
      out[k] = CLEAN(v);
    }
    return out;
  }
  return obj;
};

function stableKey(input) {
  // Deterministic 12-char key for cross-run stability; avoids Foundry complaining about missing _key
  const h = createHash("sha1").update(input).digest("base64url");
  return h.slice(0, 12);
}

function walk(inDir, cb) {
  for (const name of readdirSync(inDir)) {
    const p = join(inDir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, cb);
    else if (st.isFile() && extname(p) === ".json") cb(p);
  }
}

function stageTree({ src, out, docClass }) {
  const absSrc = resolve(src);
  const absOut = resolve(out);
  rmSync(absOut, { recursive: true, force: true });
  mkdirSync(absOut, { recursive: true });

  try {
    walk(absSrc, (p) => {
      const raw = JSON.parse(readFileSync(p, "utf8"));
      const rel = relative(absSrc, p);
      const baseName = rel.replace(/[\\/]/g, "_").replace(/\.json$/i, "");
      const id = raw._id || randomUUID();
      const keyBasis = `${docClass}:${raw.type || ""}:${raw.name}:${baseName}`;
      const key = raw._key || stableKey(keyBasis);

      const staged = CLEAN({
        ...raw,
        _id: id,
        _key: key,
        // ensure Foundry docClass for packers/importers that care
        _documentClass: docClass
      });

      const outPath = join(absOut, rel);
      mkdirSync(dirname(outPath), { recursive: true });
      writeFileSync(outPath, JSON.stringify(staged, null, 2));
      console.log(`• staged ${docClass} ${raw.name} → ${outPath}`);
    });
  } catch {
    // Optional source tree; skip if missing
  }
}

for (const cfg of SOURCES) stageTree(cfg);
console.log("Staging complete.");
