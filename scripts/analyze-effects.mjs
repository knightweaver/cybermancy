#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
const arg = process.argv[2];
if (!arg) { console.error("Usage: node analyze-effects.mjs <items.zip | items_dir>"); process.exit(1); }

async function listJsonFiles(root) {
  const out = [];
  async function walk(p) {
    const st = await fs.promises.stat(p);
    if (st.isDirectory()) {
      for (const e of await fs.promises.readdir(p)) await walk(path.join(p, e));
    } else if (p.toLowerCase().endsWith(".json")) out.push(p);
  }
  await walk(root);
  return out;
}

// Minimal ZIP reader (no deps): supports STORE/DEFLATE via native unzip on OS.
async function unzipToTemp(zipPath) {
  const tmp = fs.mkdtempSync(path.join(fs.realpathSync("."), "items-"));
  // Prefer OS unzip if available
  try {
    await new Promise((res, rej) => {
      const cp = require("node:child_process").spawn("unzip", ["-qq", zipPath, "-d", tmp]);
      cp.on("exit", (code) => code === 0 ? res() : rej(new Error("unzip failed")));
    });
    return tmp;
  } catch {
    console.error("No 'unzip' found. Please extract the ZIP manually and pass the folder path.");
    process.exit(2);
  }
}

function typeTag(v) {
  if (v === null) return "null";
  if (Array.isArray(v)) return "array";
  return typeof v; // "string","number","boolean","object","undefined"
}

// build a stable, comparable “shape signature” for an effect object
function shapeSignature(obj) {
  // Flatten to dotted keys with type tags; sort for stability
  const flat = [];
  (function walk(node, prefix) {
    if (node && typeof node === "object" && !Array.isArray(node)) {
      const keys = Object.keys(node).sort();
      for (const k of keys) walk(node[k], prefix ? `${prefix}.${k}` : k);
    } else if (Array.isArray(node)) {
      // arrays: record as "<prefix>[]:<elementShape>" using first element structure if present
      if (node.length === 0) flat.push(`${prefix}[]:empty`);
      else {
        const el = node[0];
        flat.push(`${prefix}[]:${typeTag(el)}`);
        if (el && typeof el === "object") walk(el, `${prefix}[]`);
      }
    } else {
      flat.push(`${prefix}:${typeTag(node)}`);
    }
  })(obj, "");
  return flat.sort().join("|");
}

function stableId(sig) {
  return crypto.createHash("sha1").update(sig).digest("hex").slice(0, 12);
}

function get(obj, pathStr) {
  return pathStr.split(".").reduce((a, k) => (a ? a[k] : undefined), obj);
}

function collectEffects(itemJson, fileRel) {
  const out = [];
  const acts = get(itemJson, "system.actions");
  if (!Array.isArray(acts)) return out;
  acts.forEach((a, idx) => {
    const eff = a?.effect;
    if (eff && typeof eff === "object") {
      out.push({ effect: eff, type: a?.base?.identity?.type || null, file: `${fileRel}#${idx}` });
    }
  });
  return out;
}

async function main() {
  let root = arg;
  const st = fs.existsSync(root) ? fs.statSync(root) : null;
  if (!st) { console.error("Path not found:", root); process.exit(1); }
  if (st.isFile() && root.toLowerCase().endsWith(".zip")) {
    root = await unzipToTemp(root);
  }

  const files = await listJsonFiles(root);
  const shapes = new Map();         // id -> { sig, keys, example, count, paths }
  const byType = new Map();         // type -> Set<id>

  for (const f of files) {
    let doc;
    try { doc = JSON.parse(await fs.promises.readFile(f, "utf8")); }
    catch { continue; }
    const rel = path.relative(root, f).replaceAll("\\", "/");
    const effects = collectEffects(doc, rel);
    for (const e of effects) {
      const sig = shapeSignature(e.effect);
      const id = stableId(sig);
      if (!shapes.has(id)) {
        const keys = sig.split("|").map(s => s.split(":")[0]).filter(Boolean);
        shapes.set(id, { sig, keys, example: e.effect, count: 0, paths: [] });
      }
      const rec = shapes.get(id);
      rec.count += 1;
      if (rec.paths.length < 20) rec.paths.push(e.file);
      const t = e.type || "unknown";
      if (!byType.has(t)) byType.set(t, new Set());
      byType.get(t).add(id);
    }
  }

  const catalog = {
    shapes: Object.fromEntries([...shapes.entries()].map(([id, r]) => [id, {
      keys: r.keys,
      example: r.example,
      count: r.count,
      paths: r.paths
    }])),
    byType: Object.fromEntries([...byType.entries()].map(([t, set]) => [t, [...set]]))
  };

  const outPath = path.resolve("effect-catalog.json");
  await fs.promises.writeFile(outPath, JSON.stringify(catalog, null, 2));
  console.log("Wrote", outPath);

  // quick tabular view (first 100)
  const rows = [...Object.entries(catalog.shapes)].slice(0, 100).map(([id, r]) => ({
    id, count: r.count, keys: r.keys.join(", ")
  }));
  const tsv = ["id\tcount\tkeys", ...rows.map(r => `${r.id}\t${r.count}\t${r.keys}`)].join("\n");
  await fs.promises.writeFile("effect-catalog.tsv", tsv, "utf8");
}
main().catch(e => { console.error(e); process.exit(1); });
