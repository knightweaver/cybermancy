#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import {
  CYBERMANCY_DOMAINS,
  auditCybermancyRuntime,
  planDomainRegistration,
  registerCybermancyDomains
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


function domainModel(value) {
  const snapshot = structuredClone(value);
  return {
    ...snapshot,
    toObject: () => structuredClone(snapshot)
  };
}

function materializeDh2105Homebrew(value) {
  const out = structuredClone(value ?? {});
  out.domains ??= {};
  for (const [id, domain] of Object.entries(out.domains)) {
    out.domains[id] = {
      color: "#000000",
      invertText: false,
      ...domain,
      id: domain.id ?? id
    };
  }
  return out;
}

function installMockRuntime({
  isGM,
  homebrewDomains = {},
  coreDomains = CORE_DAGGERHEART_2105_DOMAINS,
  systemVersion = "2.10.5"
}) {
  let stored = materializeDh2105Homebrew({
    maxFear: 12,
    maxHope: 6,
    domains: homebrewDomains
  });
  let setCalls = 0;

  globalThis.CONFIG = {
    DH: {
      id: "daggerheart",
      SETTINGS: { gameSettings: { Homebrew: "Homebrew" } },
      DOMAIN: {
        domains: coreDomains,
        allDomains: () => ({
          ...(globalThis.game?.system?.settings?.homebrew?.domains ?? {}),
          ...coreDomains
        })
      }
    }
  };

  globalThis.ui = {
    notifications: {
      error: () => {},
      warn: () => {}
    }
  };

  globalThis.game = {
    user: { isGM },
    system: {
      id: "daggerheart",
      version: systemVersion,
      settings: { homebrew: domainModel(stored) }
    },
    settings: {
      get(namespace, key) {
        if (namespace !== "daggerheart" || key !== "Homebrew") {
          throw new Error(`unexpected settings.get(${namespace}, ${key})`);
        }
        return domainModel(stored);
      },
      async set(namespace, key, value) {
        if (namespace !== "daggerheart" || key !== "Homebrew") {
          throw new Error(`unexpected settings.set(${namespace}, ${key})`);
        }
        setCalls += 1;
        stored = materializeDh2105Homebrew(value);
        globalThis.game.system.settings.homebrew = domainModel(stored);
        return globalThis.game.system.settings.homebrew;
      }
    }
  };

  return {
    get setCalls() {
      return setCalls;
    },
    snapshot: () => structuredClone(stored)
  };
}

const unrelatedPersisted = {
  id: "custom-domain",
  label: "Custom Domain",
  src: "icons/svg/portal.svg",
  description: "<p>Unrelated homebrew.</p>",
  color: "#123456",
  invertText: true
};

const gmRuntime = installMockRuntime({
  isGM: true,
  homebrewDomains: { "custom-domain": unrelatedPersisted }
});
const runtimeAudit = auditCybermancyRuntime();
assert(runtimeAudit.valid, "Daggerheart 2.10.5 runtime audit should be valid");
assert(runtimeAudit.majorCompatible, "Daggerheart 2.10.5 should satisfy the DH2 major contract");
assert(runtimeAudit.exactQualificationTarget, "2.10.5 must match the exact qualification target");

const gmFirst = await registerCybermancyDomains({ notify: false });
assert(
  gmFirst.status === "registered",
  `GM first registration status should be registered, got ${gmFirst.status}`
);
assert(gmFirst.wroteSetting === true, "GM first registration should write the Homebrew setting");
assert(gmRuntime.setCalls === 1, `GM first registration should write exactly once, got ${gmRuntime.setCalls}`);
assert(
  gmRuntime.snapshot().domains["custom-domain"]?.color === "#123456",
  "GM registration must preserve unrelated Homebrew Domain fields"
);

const gmSecond = await registerCybermancyDomains({ notify: false });
assert(
  gmSecond.status === "already-registered",
  `GM second registration should be idempotent, got ${gmSecond.status}`
);
assert(gmSecond.wroteSetting === false, "GM second registration must not rewrite the Homebrew setting");
assert(gmRuntime.setCalls === 1, "GM second registration must not add another settings write");

const persistedAfterFirstLoad = gmRuntime.snapshot();
const reloadRuntime = installMockRuntime({
  isGM: true,
  homebrewDomains: persistedAfterFirstLoad.domains
});
const gmReload = await registerCybermancyDomains({ notify: false });
assert(gmReload.status === "already-registered", "GM reload should recognize persisted Domains");
assert(gmReload.wroteSetting === false, "GM reload must not rewrite already registered Domains");
assert(reloadRuntime.setCalls === 0, "GM reload should perform zero world-setting writes");

const playerMissingRuntime = installMockRuntime({
  isGM: false,
  homebrewDomains: { "custom-domain": unrelatedPersisted }
});
const playerMissing = await registerCybermancyDomains({ notify: false });
assert(
  playerMissing.status === "gm-required",
  `non-GM missing-domain status should be gm-required, got ${playerMissing.status}`
);
assert(playerMissing.wroteSetting === false, "non-GM client must never write world settings");
assert(playerMissingRuntime.setCalls === 0, "non-GM missing-domain client performed a settings write");

const playerReadyRuntime = installMockRuntime({
  isGM: false,
  homebrewDomains: persistedAfterFirstLoad.domains
});
const playerReady = await registerCybermancyDomains({ notify: false });
assert(playerReady.status === "already-registered", "non-GM client should audit persisted Domains successfully");
assert(playerReady.wroteSetting === false, "non-GM audit must not write world settings");
assert(playerReadyRuntime.setCalls === 0, "non-GM registered-domain client performed a settings write");

const futurePatchRuntime = installMockRuntime({
  isGM: false,
  homebrewDomains: persistedAfterFirstLoad.domains,
  systemVersion: "2.11.0"
});
const futurePatchAudit = auditCybermancyRuntime();
assert(futurePatchAudit.valid, "Daggerheart 2.x patch should remain compatible with the major-only manifest");
assert(futurePatchAudit.majorCompatible, "Daggerheart 2.x patch should satisfy the major compatibility check");
assert(
  futurePatchAudit.exactQualificationTarget === false,
  "non-2.10.5 runtime must not be reported as exactly qualified"
);
const futurePatch = await registerCybermancyDomains({ notify: false });
assert(futurePatch.status === "already-registered", "supported DH2 patch should still audit registered Domains");
assert(futurePatchRuntime.setCalls === 0, "non-GM DH2 patch audit must not write settings");

installMockRuntime({
  isGM: false,
  homebrewDomains: persistedAfterFirstLoad.domains,
  systemVersion: "1.9.0"
});
const legacyAudit = auditCybermancyRuntime();
assert(legacyAudit.valid === false, "Daggerheart 1.x must fail the v0.2.0 runtime audit");
assert(legacyAudit.majorCompatible === false, "Daggerheart 1.x must fail the DH2 major compatibility check");

const mainSource = await fs.readFile(path.join(ROOT, "scripts", "main.js"), "utf8");
assert(mainSource.includes('from "./domains.js"'), "scripts/main.js must import Domain registration");
assert(mainSource.includes('Hooks.once("ready"'), "Domain registration must run after settings initialize");
assert(mainSource.includes("registerCybermancyDomains"), "main.js must invoke Domain registration");
assert(mainSource.includes("auditCybermancyRuntime"), "main.js must audit Daggerheart before Domain registration");
assert(
  mainSource.includes("exactQualificationTarget"),
  "main.js must distinguish exact 2.10.5 qualification from broader DH2 compatibility"
);

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
console.log(" - Daggerheart 2.10.5 runtime API audit: PASS");
console.log(" - GM first registration writes once: PASS");
console.log(" - same-session registration idempotence: PASS");
console.log(" - reload registration idempotence: PASS");
console.log(" - non-GM missing-domain behavior (no write): PASS");
console.log(" - non-GM registered-domain behavior (no write): PASS");
console.log(" - DH2 major compatibility vs exact 2.10.5 qualification: PASS");
console.log(" - Daggerheart 1.x activation rejection: PASS");
