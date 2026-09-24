#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const errors = [];
const assert = (condition, message) => {
  if (!condition) errors.push(message);
};

async function exists(rel) {
  try {
    await fs.access(path.join(ROOT, rel));
    return true;
  } catch {
    return false;
  }
}

async function walkJson(root) {
  const out = [];
  const entries = await fs.readdir(root, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) out.push(...await walkJson(full));
    else if (entry.isFile() && entry.name.endsWith(".json")) out.push(full);
  }
  return out;
}

const manifest = JSON.parse(await fs.readFile(path.join(ROOT, "module.json"), "utf8"));
const main = await fs.readFile(path.join(ROOT, "scripts", "main.js"), "utf8");
const packager = await fs.readFile(path.join(ROOT, "tools", "build-runtime-package.py"), "utf8");

const retiredFiles = [
  "scripts/sheets/CybermancyRunnerSheet.js",
  "scripts/sheets/CybermancyWeaponSheet.js",
  "templates/actor-runner-sheet.hbs",
  "templates/item-weapon-sheet.hbs",
  "styles/cybermancy.css"
];

for (const rel of retiredFiles) {
  assert(!(await exists(rel)), `retired legacy sheet artifact still exists: ${rel}`);
  assert(!packager.includes(rel), `runtime packager still includes retired artifact: ${rel}`);
}

assert(
  Array.isArray(manifest.styles) && manifest.styles.length === 0,
  "module.json must not declare the retired Cybermancy sheet stylesheet"
);
assert(!main.includes("CybermancyWeaponSheet"), "main.js still references CybermancyWeaponSheet");
assert(!main.includes("CybermancyRunnerSheet"), "main.js still references CybermancyRunnerSheet");
assert(!main.includes("Items.registerSheet"), "Cybermancy must not register an Item sheet in v0.2.0");
assert(!main.includes("Actors.registerSheet"), "Cybermancy must not register an Actor sheet in v0.2.0");
assert(!main.includes("enableSmartlink"), "retired custom-sheet Smartlink setting remains registered");

const activeRuntime = [
  path.join(ROOT, "scripts", "main.js"),
  path.join(ROOT, "scripts", "domains.js"),
  path.join(ROOT, "scripts", "hooks.js")
];
const forbiddenRuntimePatterns = [
  ["extends ActorSheet", "legacy ActorSheet inheritance"],
  ["extends ItemSheet", "legacy ItemSheet inheritance"],
  ["system.abilities.agi.mod", "legacy agility modifier path"],
  ["system.proficiency.attack", "legacy attack proficiency path"],
  ["1d20 +", "manual d20 attack workflow"],
  ["weapon.smartlink", "retired custom Smartlink weapon flag"],
  ["weapon.burst", "retired custom burst weapon flag"],
  ["weapon.cybergrade", "retired custom cybergrade weapon flag"]
];
for (const file of activeRuntime) {
  const source = await fs.readFile(file, "utf8");
  for (const [needle, label] of forbiddenRuntimePatterns) {
    assert(!source.includes(needle), `${path.relative(ROOT, file)} still contains ${label}: ${needle}`);
  }
}

// Confirm the retired sheet flags were prototype-only runtime metadata and were
// never part of canonical Compendium source.
const packJson = await walkJson(path.join(ROOT, "src", "packs"));
for (const file of packJson) {
  const raw = await fs.readFile(file, "utf8");
  assert(
    !raw.includes('"weapon":{"smartlink"') &&
      !raw.includes('"weapon": {"smartlink"') &&
      !raw.includes('"weapon.smartlink"') &&
      !raw.includes('"weapon.burst"') &&
      !raw.includes('"weapon.cybergrade"'),
    `${path.relative(ROOT, file)} contains a retired custom-sheet weapon flag`
  );
}

// The canonical weapon implementation must remain in Daggerheart item data,
// including the representative Smartpistol native attack plus its Cybermancy
// Smartlink action. This is the supported v0.2.0 path; no manual sheet roll is
// allowed to replace it.
const weaponDir = path.join(ROOT, "src", "packs", "items", "weapons");
const weaponFiles = (await fs.readdir(weaponDir)).filter(name => name.endsWith(".json")).sort();
let weaponDocs = 0;
let smartpistol = null;
for (const name of weaponFiles) {
  const doc = JSON.parse(await fs.readFile(path.join(weaponDir, name), "utf8"));
  if (String(doc._key ?? "").startsWith("!folders!")) continue;
  weaponDocs += 1;
  assert(doc.type === "weapon", `${name}: expected weapon document`);
  assert(doc.system?.attack?.type === "attack", `${name}: missing native Daggerheart system.attack`);
  if (doc._id === "41U5oyL5z2gAkerd") smartpistol = doc;
}
assert(weaponDocs === 47, `expected frozen 47 weapon documents, got ${weaponDocs}`);
assert(Boolean(smartpistol), "Smartpistol regression fixture 41U5oyL5z2gAkerd is missing");
if (smartpistol) {
  assert(
    smartpistol.system?.attack?.roll?.trait === "finesse",
    "Smartpistol native attack trait changed"
  );
  assert(
    Object.values(smartpistol.system?.actions ?? {}).some(action => action?.name === "Smartlink"),
    "Smartpistol canonical Smartlink action is missing"
  );
}

if (errors.length) {
  console.error("Cybermancy Foundry 14/DH2 sheet retirement validation FAILED");
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}

console.log("Cybermancy Foundry 14/DH2 sheet retirement validation PASS");
console.log(" - legacy ActorSheet/ItemSheet classes: retired");
console.log(" - empty custom sheet templates/style: retired");
console.log(" - custom sheet registration: absent");
console.log(" - manual 1d20 attack workflow: absent");
console.log(" - retired Smartlink/burst/cybergrade flags in canonical packs: absent");
console.log(` - native Daggerheart weapon documents checked: ${weaponDocs}`);
console.log(" - Smartpistol native attack + canonical Smartlink action: PASS");
