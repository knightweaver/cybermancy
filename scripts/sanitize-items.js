// scripts/sanitize-items.js
// Usage: node scripts/sanitize-items.js

const fs = require("fs");
const path = require("path");

const SRC_ROOT = path.resolve("src-data", "items");
const STRIP_KEYS = new Set(["folder", "effects", "ownership", "flags", "_stats", "_id"]);

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? walk(p) : p.endsWith(".json") ? [p] : [];
  });
}

function stripVolatile(obj) {
  if (Array.isArray(obj)) return obj.map(stripVolatile);
  if (obj && typeof obj === "object") {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (STRIP_KEYS.has(k)) continue;
      out[k] = stripVolatile(v);
    }
    return out;
  }
  return obj;
}

function main() {
  const files = walk(SRC_ROOT);
  let count = 0;
  for (const file of files) {
    const raw = fs.readFileSync(file, "utf8");
    const json = JSON.parse(raw);
    const cleaned = stripVolatile(json);
    fs.writeFileSync(file, JSON.stringify(cleaned, null, 2), "utf8");
    count++;
  }
  console.log(`Sanitized ${count} item files under ${SRC_ROOT}`);
}

main();
