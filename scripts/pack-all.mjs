// scripts/pack-all.mjs
// Packs all item subtypes under src-data/items/* into packs/* using Foundry CLI.
// Usage: node scripts/pack-all.mjs

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const SRC = join(ROOT, "src-data", "items");
const OUT = join(ROOT, "packs");

// Map subfolder -> pack name in module.json
const PACK_MAP = {
  weapons: "items-weapons",
  armors: "items-armors",
  consumables: "items-consumables",
  loot: "items-loot"
};

if (!existsSync(SRC)) {
  console.error(`Source folder not found: ${SRC}`);
  process.exit(1);
}
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });

const subdirs = readdirSync(SRC).filter(d => statSync(join(SRC, d)).isDirectory());

let failures = 0;
for (const dir of subdirs) {
  const packName = PACK_MAP[dir];
  if (!packName) {
    console.warn(`Skipping unknown subtype folder: ${dir}`);
    continue;
  }
  const inputDir = join(SRC, dir);
  console.log(`\n👉 Packing ${dir} -> ${packName}`);
  const res = spawnSync("fvtt", [
    "package", "pack",
    packName,
    "--inputDirectory", inputDir,
    "--outputDirectory", OUT
  ], { stdio: "inherit", shell: true });

  if (res.status !== 0) {
    console.error(`❌ Failed packing ${dir}`);
    failures++;
  } else {
    console.log(`✅ Packed ${dir}`);
  }
}

if (failures) {
  console.error(`\nDone with ${failures} failure(s).`);
  process.exit(1);
}
console.log("\n🎉 All packs built.");
