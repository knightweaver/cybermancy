#!/usr/bin/env node
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const PACKS = [
  { label: "Cybermancy Items",   src: "stage/items",   dest: "packs/cybermancy-items",   type: "Item"  },
  { label: "Cybermancy Domains", src: "stage/domains", dest: "packs/cybermancy-domains", type: "Item"  },
  { label: "Cybermancy Actors",  src: "stage/actors",  dest: "packs/cybermancy-actors",  type: "Actor" }
];

function hasJson(dir) {
  let found = false;
  const walk = (d) => {
    for (const name of readdirSync(d)) {
      const p = join(d, name);
      const st = statSync(p);
      if (st.isDirectory()) walk(p);
      else if (st.isFile() && extname(p) === ".json") found = true;
    }
  };
  try { walk(dir); } catch { /* missing dir is fine */ }
  return found;
}

for (const { label, src, dest, type } of PACKS) {
  if (!hasJson(src)) {
    console.log(`(skip) no docs in ${src}`);
    continue;
  }
  console.log(`Packing ${label} (${type}) → ${dest}`);
  await compilePack(src, dest, {
    recursive: true,
    log: true,
    // Optional sanity check: ensure Item vs Actor types match your target pack.
    validateDocumentType: type
  });
}

console.log("Pack complete.");
