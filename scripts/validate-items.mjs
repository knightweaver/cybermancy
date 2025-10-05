import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const SRC = join(process.cwd(), "src-data", "items");
const files = [];
(function walk(d){ for (const e of readdirSync(d)) {
  const p = join(d, e);
  statSync(p).isDirectory() ? walk(p) : e.endsWith(".json") && files.push(p);
}})(SRC);

const bad = [];
for (const f of files) {
  try {
    const j = JSON.parse(readFileSync(f, "utf8"));
    if (!j?.name || !j?.type) bad.push(f);
  } catch { bad.push(f); }
}
if (bad.length) {
  console.error("Invalid or missing name/type in:");
  for (const f of bad) console.error("  " + f);
  process.exit(1);
}
console.log("OK: all item JSON have name & type.");
