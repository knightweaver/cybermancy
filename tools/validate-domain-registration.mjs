#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import {
  CYBERMANCY_DOMAINS,
  planDomainRegistration
} from "../scripts/domains.js";

const ROOT = process.cwd();
const EXPECTED_IDS = ["circuit", "maker", "bullet"];
const CORE_DAGGERHEART_2105_DOMAINS = {
  arcana: {}, blade: {}, bone: {}, codex: {}, dread: {}, grace: {},
  midnight: {}, sage: {}, splendor: {}, valor: {}
};

const errors = [];
const assert = (condition, message) => {
  if (!condition) errors.push(message);
};

async function loadJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function sourceDocuments(directory) {
  const names = await fs.readdir(directory);
  const docs = [];
  for (const name of names.sort()) {
    if (!name.endsWith(".json")) continue;
    const doc = await loadJson(path.join(directory, name));
    if (String(doc._key ?? "").startsWith("!folders!")) continue;
    docs.push({ name, doc });
  }
  return docs;
}

const ids = Object.keys(CYBERMANCY_DOMAINS);
assert(
  JSON.stringify(ids) === JSON.stringify(EXPECTED_IDS),
  `Domain IDs/order differ from accepted contract: ${ids.join(", ")}`
);

for (const id of EXPECTED_IDS) {
  const domain = CYBERMANCY_DOMAINS[id];
  assert(Boolean(domain), `missing Domain definition: ${id}`);
  if (!domain) continue;

  assert(domain.id === id, `${id}: definition.id mismatch`);
  assert(Boolean(domain.label), `${id}: empty label`);
  assert(Boolean(domain.description), `${id}: empty description`);
  assert(
    domain.src === `modules/cybermancy/assets/icons/domains/${id}.svg`,
    `${id}: Homebrew Domain src must use Cybermancy SVG glyph`
  );
  assert(
    !Object.prototype.hasOwnProperty.call(CORE_DAGGERHEART_2105_DOMAINS, id),
    `${id}: collides with a Daggerheart 2.10.5 core Domain`
  );

  try {
    await fs.access(path.join(ROOT, "assets", "icons", "domains", `${id}.svg`));
  } catch {
    errors.push(`${id}: SVG glyph is missing from assets/icons/domains`);
  }
}

const domainDocs = await sourceDocuments(path.join(ROOT, "src", "packs", "system", "domains"));
const cardCounts = Object.fromEntries(EXPECTED_IDS.map(id => [id, 0]));
for (const { name, doc } of domainDocs) {
  assert(doc.type === "domainCard", `${name}: expected domainCard document`);
  const domain = doc.system?.domain;
  assert(
    Object.prototype.hasOwnProperty.call(cardCounts, domain),
    `${name}: unknown Cybermancy Domain "${domain}"`
  );
  if (Object.prototype.hasOwnProperty.call(cardCounts, domain)) cardCounts[domain] += 1;
}
for (const [id, count] of Object.entries(cardCounts)) {
  assert(count > 0, `${id}: expected at least one Domain Card`);
}

const classDocs = await sourceDocuments(path.join(ROOT, "src", "packs", "system", "classes"));
const customClassUsage = Object.fromEntries(EXPECTED_IDS.map(id => [id, 0]));
for (const { name, doc } of classDocs) {
  for (const domain of doc.system?.domains ?? []) {
    const isCore = Object.prototype.hasOwnProperty.call(CORE_DAGGERHEART_2105_DOMAINS, domain);
    const isCybermancy = Object.prototype.hasOwnProperty.call(CYBERMANCY_DOMAINS, domain);
    assert(isCore || isCybermancy, `${name}: references unknown Domain "${domain}"`);
    if (isCybermancy) customClassUsage[domain] += 1;
  }
}
for (const [id, count] of Object.entries(customClassUsage)) {
  assert(count > 0, `${id}: no Cybermancy class references this custom Domain`);
}

const unrelatedDomain = {
  id: "custom-domain",
  label: "Custom Domain",
  src: "icons/svg/portal.svg",
  description: "<p>Unrelated homebrew.</p>"
};

const firstPlan = planDomainRegistration({
  coreDomains: CORE_DAGGERHEART_2105_DOMAINS,
  homebrewDomains: { "custom-domain": unrelatedDomain }
});
assert(firstPlan.added.length === 3, "first registration should add all 3 Domains");
assert(firstPlan.conflicts.length === 0, "first registration should have no Homebrew conflicts");
assert(firstPlan.coreConflicts.length === 0, "first registration should have no core conflicts");
assert(
  firstPlan.nextDomains["custom-domain"]?.label === "Custom Domain",
  "registration must preserve unrelated Homebrew Domains"
);

const secondPlan = planDomainRegistration({
  coreDomains: CORE_DAGGERHEART_2105_DOMAINS,
  homebrewDomains: firstPlan.nextDomains
});
assert(secondPlan.added.length === 0, "second registration must be idempotent");
assert(secondPlan.unchanged.length === 3, "second registration should recognize all 3 unchanged");
assert(secondPlan.changed === false, "second registration must not rewrite world settings");

const conflictingDomains = {
  ...firstPlan.nextDomains,
  circuit: {
    id: "circuit",
    label: "Existing Circuit",
    src: "icons/svg/portal.svg",
    description: "<p>Existing world-owned data.</p>"
  }
};
const conflictPlan = planDomainRegistration({
  coreDomains: CORE_DAGGERHEART_2105_DOMAINS,
  homebrewDomains: conflictingDomains
});
assert(
  conflictPlan.conflicts.map(entry => entry.id).includes("circuit"),
  "same-ID differing Homebrew Domain must be reported as a conflict"
);
assert(
  conflictPlan.nextDomains.circuit.label === "Existing Circuit",
  "same-ID differing Homebrew Domain must not be silently overwritten"
);

const coreConflictPlan = planDomainRegistration({
  coreDomains: { ...CORE_DAGGERHEART_2105_DOMAINS, circuit: { id: "circuit" } },
  homebrewDomains: {}
});
assert(coreConflictPlan.coreConflicts.includes("circuit"), "core collisions must be rejected");
assert(
  !Object.prototype.hasOwnProperty.call(coreConflictPlan.nextDomains, "circuit"),
  "core collisions must not be inserted into Homebrew Domains"
);

const mainSource = await fs.readFile(path.join(ROOT, "scripts", "main.js"), "utf8");
assert(mainSource.includes('from "./domains.js"'), "scripts/main.js must import Domain registration");
assert(mainSource.includes('Hooks.once("ready"'), "Domain registration must run after settings initialize");
assert(mainSource.includes("registerCybermancyDomains"), "main.js must invoke Domain registration");

if (errors.length) {
  console.error("Cybermancy native Homebrew Domain validation FAILED");
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}

console.log("Cybermancy native Homebrew Domain validation PASS");
console.log(` - Domains: ${EXPECTED_IDS.join(", ")}`);
console.log(` - Domain Cards: ${domainDocs.length} (${Object.entries(cardCounts).map(([id, count]) => `${id}=${count}`).join(", ")})`);
console.log(` - Classes checked: ${classDocs.length} (${Object.entries(customClassUsage).map(([id, count]) => `${id}=${count}`).join(", ")})`);
console.log(" - unrelated Homebrew preservation: PASS");
console.log(" - idempotence: PASS");
console.log(" - same-ID conflict preservation: PASS");
console.log(" - core-domain collision guard: PASS");
