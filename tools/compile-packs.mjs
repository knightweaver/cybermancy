#!/usr/bin/env node

import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { promises as fs } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const manifest = JSON.parse(
  await fs.readFile(path.join(ROOT, "module.json"), "utf8")
);

const stripDb = packPath => {
  if (!packPath.endsWith(".db")) {
    throw new Error(`Foundry 14 pack path must end in .db: ${packPath}`);
  }
  return packPath.slice(0, -3);
};

for (const pack of manifest.packs ?? []) {
  const compiledRel = stripDb(pack.path);
  const sourceRel = path.join("src", compiledRel);
  const sourceAbs = path.join(ROOT, sourceRel);
  const compiledAbs = path.join(ROOT, compiledRel);

  let entries;
  try {
    entries = await fs.readdir(sourceAbs);
  } catch (error) {
    throw new Error(`${pack.name}: declared source pack is missing: ${sourceRel}`, { cause: error });
  }

  const jsonFiles = entries.filter(name => name.toLowerCase().endsWith(".json"));
  if (jsonFiles.length === 0) {
    throw new Error(`${pack.name}: declared source pack contains no JSON documents: ${sourceRel}`);
  }

  await fs.rm(compiledAbs, { recursive: true, force: true });
  await fs.mkdir(path.dirname(compiledAbs), { recursive: true });

  console.log(`Cybermancy | compiling ${sourceRel} -> ${compiledRel}`);
  await compilePack(sourceAbs, compiledAbs, { yaml: false });
}
