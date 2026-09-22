#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const manifestPath = path.join(ROOT, "module.json");
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const errors = [];

const requireCompatibility = (label, value, expected) => {
  if (!value || typeof value !== "object") {
    errors.push(`${label}: compatibility object is missing`);
    return;
  }
  for (const key of ["minimum", "verified", "maximum"]) {
    if (String(value[key] ?? "") !== String(expected[key] ?? "")) {
      errors.push(
        `${label}: ${key} must be ${JSON.stringify(expected[key])}, got ${JSON.stringify(value[key])}`
      );
    }
  }
};

if (manifest.id !== "cybermancy") {
  errors.push(`module id must be "cybermancy", got ${JSON.stringify(manifest.id)}`);
}
if (!/^\d+\.\d+\.\d+$/.test(String(manifest.version ?? ""))) {
  errors.push(`module version must be semantic x.y.z, got ${JSON.stringify(manifest.version)}`);
}

requireCompatibility("Foundry", manifest.compatibility, { minimum: "13", verified: "13", maximum: "13" });

const daggerheart = (manifest.relationships?.systems ?? []).find(
  system => system?.id === "daggerheart"
);
if (!daggerheart) {
  errors.push("Daggerheart system relationship is missing");
} else {
  if (daggerheart.type !== "system") {
    errors.push(`Daggerheart relationship type must be "system", got ${JSON.stringify(daggerheart.type)}`);
  }
  requireCompatibility("Daggerheart", daggerheart.compatibility, { minimum: "1.2", verified: "1.2", maximum: "1.9" });
}

const esmodules = manifest.esmodules ?? [];
if (!esmodules.includes("scripts/main.js")) {
  errors.push('module must load Cybermancy runtime entry point via esmodules: ["scripts/main.js"]');
}

const declaredPacks = new Map();
const declaredPackPaths = new Set();
for (const pack of manifest.packs ?? []) {
  if (!pack?.name) {
    errors.push("declared pack is missing a name");
    continue;
  }
  if (declaredPacks.has(pack.name)) {
    errors.push(`duplicate pack declaration: ${pack.name}`);
  }
  declaredPacks.set(pack.name, pack);

  const packPath = String(pack.path ?? "");
  if (!packPath) {
    errors.push(`${pack.name}: pack path is missing`);
    continue;
  }
  if (packPath.endsWith(".db")) {
    errors.push(`${pack.name}: pack path must name the LevelDB directory without a legacy .db suffix: ${JSON.stringify(packPath)}`);
  }
  if (packPath.includes("\\")) {
    errors.push(`${pack.name}: pack path must use forward slashes: ${JSON.stringify(packPath)}`);
  }
  if (!packPath.startsWith("packs/")) {
    errors.push(`${pack.name}: pack path must be under packs/: ${JSON.stringify(packPath)}`);
  }
  const normalizedPath = path.posix.normalize(packPath);
  if (normalizedPath !== packPath || normalizedPath.startsWith("../") || normalizedPath === "..") {
    errors.push(`${pack.name}: pack path must be normalized and repository-relative: ${JSON.stringify(packPath)}`);
  }
  if (declaredPackPaths.has(packPath)) {
    errors.push(`${pack.name}: duplicate pack path: ${packPath}`);
  }
  declaredPackPaths.add(packPath);

  if ((pack.type === "Actor" || pack.type === "Item") && pack.system !== "daggerheart") {
    errors.push(`${pack.name}: ${pack.type} pack must declare system "daggerheart", got ${JSON.stringify(pack.system)}`);
  }

  const sourceRel = path.join("src", packPath);
  try {
    const stat = await fs.stat(path.join(ROOT, sourceRel));
    if (!stat.isDirectory()) errors.push(`${pack.name}: source pack is not a directory: ${sourceRel}`);
  } catch {
    errors.push(`${pack.name}: source pack is missing: ${sourceRel}`);
  }
}

for (const group of manifest.packFolders ?? []) {
  for (const folder of group.folders ?? []) {
    for (const packName of folder.packs ?? []) {
      if (!declaredPacks.has(packName)) {
        errors.push(`packFolders references undeclared pack: ${packName}`);
      }
    }
  }
}

const runtimeReferences = [
  ...(manifest.esmodules ?? []),
  ...(manifest.styles ?? []),
  ...(manifest.languages ?? []).map(language => language?.path).filter(Boolean)
];
for (const rel of runtimeReferences) {
  try {
    const stat = await fs.stat(path.join(ROOT, rel));
    if (!stat.isFile()) errors.push(`runtime reference is not a file: ${rel}`);
  } catch {
    errors.push(`runtime reference is missing: ${rel}`);
  }
}

const expectedManifest =
  "https://github.com/knightweaver/cybermancy/releases/latest/download/module.json";
const expectedArchive = `cybermancy-v${manifest.version}.zip`;
const expectedDownload =
  `https://github.com/knightweaver/cybermancy/releases/download/v${manifest.version}/${expectedArchive}`;

if (manifest.manifest !== expectedManifest) {
  errors.push(`manifest URL mismatch: ${JSON.stringify(manifest.manifest)}`);
}
if (manifest.download !== expectedDownload) {
  errors.push(`download URL mismatch: expected ${expectedDownload}, got ${JSON.stringify(manifest.download)}`);
}

if (errors.length) {
  console.error("Cybermancy release manifest validation FAILED");
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}

console.log("Cybermancy release manifest validation PASS");
console.log(` - version: ${manifest.version}`);
console.log(" - Foundry compatibility: 13 / 13 / 13");
console.log(" - Daggerheart compatibility: 1.2 / 1.2 / 1.9");
console.log(` - declared Compendia: ${declaredPacks.size}`);
console.log(" - scripts/main.js runtime entry point: declared");
