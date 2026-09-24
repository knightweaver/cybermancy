#!/usr/bin/env node

import { extractPack } from "@foundryvtt/foundryvtt-cli";
import { promises as fs } from "node:fs";
import path from "node:path";
import readline from "node:readline/promises";

const ROOT = process.cwd();
const manifest = JSON.parse(
  await fs.readFile(path.join(ROOT, "module.json"), "utf8")
);
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const answer = await rl.question(
  'This overwrites canonical src/packs JSON from compiled packs. Type "Overwrite" to continue: '
);
rl.close();

if (answer.toLowerCase() !== "overwrite") {
  console.log("Cybermancy | extraction canceled");
  process.exit(0);
}

const stripDb = packPath => {
  if (!packPath.endsWith(".db")) {
    throw new Error(`Foundry 14 pack path must end in .db: ${packPath}`);
  }
  return packPath.slice(0, -3);
};

function transformName(doc) {
  const safeName = (doc.name ?? "unnamed").replace(/[^a-zA-Z0-9А-я]/g, "_");
  const keyType = doc._key?.split("!")[1];
  const prefix = ["actors", "items"].includes(keyType) ? doc.type : keyType ?? "document";
  return `${prefix}_${safeName}_${doc._id}.json`;
}

for (const pack of manifest.packs ?? []) {
  const compiledRel = stripDb(pack.path);
  const compiledAbs = path.join(ROOT, compiledRel);
  const sourceRel = path.join("src", compiledRel);
  const sourceAbs = path.join(ROOT, sourceRel);

  try {
    const stat = await fs.stat(compiledAbs);
    if (!stat.isDirectory()) throw new Error("not a directory");
  } catch {
    throw new Error(`${pack.name}: compiled pack is missing: ${compiledRel}`);
  }

  await fs.mkdir(sourceAbs, { recursive: true });
  for (const file of await fs.readdir(sourceAbs)) {
    if (file.toLowerCase().endsWith(".json")) {
      await fs.unlink(path.join(sourceAbs, file));
    }
  }

  console.log(`Cybermancy | extracting ${compiledRel} -> ${sourceRel}`);
  await extractPack(compiledAbs, sourceAbs, { yaml: false, transformName });
}
