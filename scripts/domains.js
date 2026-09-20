/**
 * Cybermancy Domain registration for Daggerheart 1.2.7.
 *
 * Daggerheart exposes custom Domains through its world-scoped Homebrew setting.
 * CONFIG.DH.DOMAIN.allDomains() merges those Homebrew Domains with the core
 * Daggerheart Domains, so Cybermancy registers Circuit, Maker, and Bullet
 * through that supported interface rather than patching the Daggerheart system.
 */

export const CYBERMANCY_DOMAINS = Object.freeze({
  circuit: Object.freeze({
    id: "circuit",
    label: "Circuit",
    src: "modules/cybermancy/assets/icons/domains/circuit.svg",
    description:
      "<p>This is the domain of the Matrix. Those who chose this domain surf the digital spaces that overlay and often control the physical world. They use their digital mastery to control the battlefield, disable their enhanced opponents, and lay waste to the corporate data fortresses.</p>"
  }),
  maker: Object.freeze({
    id: "maker",
    label: "Maker",
    src: "modules/cybermancy/assets/icons/domains/maker.svg",
    description: "<p>This is the domain of the Makers.</p>"
  }),
  bullet: Object.freeze({
    id: "bullet",
    label: "Bullet",
    src: "modules/cybermancy/assets/icons/domains/bullet.svg",
    description: "<p>This is the domain of those that shoot bullets.</p>"
  })
});

const comparableDomain = domain => ({
  id: domain?.id ?? "",
  label: domain?.label ?? "",
  src: domain?.src ?? "",
  description: domain?.description ?? ""
});

const domainEquals = (a, b) =>
  JSON.stringify(comparableDomain(a)) === JSON.stringify(comparableDomain(b));

/**
 * Pure merge planner used by runtime registration and build validation.
 * Existing unrelated Homebrew Domains are preserved. Cybermancy never silently
 * overwrites a same-ID Homebrew Domain whose definition differs.
 */
export function planDomainRegistration({
  coreDomains = {},
  homebrewDomains = {}
} = {}) {
  const nextDomains = Object.fromEntries(
    Object.entries(homebrewDomains).map(([id, value]) => [id, { ...value }])
  );
  const added = [];
  const unchanged = [];
  const conflicts = [];
  const coreConflicts = [];

  for (const [id, expected] of Object.entries(CYBERMANCY_DOMAINS)) {
    if (Object.prototype.hasOwnProperty.call(coreDomains, id)) {
      coreConflicts.push(id);
      continue;
    }

    const existing = homebrewDomains[id];
    if (!existing) {
      nextDomains[id] = { ...expected };
      added.push(id);
      continue;
    }

    if (domainEquals(existing, expected)) {
      unchanged.push(id);
      continue;
    }

    conflicts.push({
      id,
      expected: comparableDomain(expected),
      existing: comparableDomain(existing)
    });
  }

  return {
    nextDomains,
    added,
    unchanged,
    conflicts,
    coreConflicts,
    changed: added.length > 0
  };
}

export function auditCybermancyDomains(allDomains = {}) {
  const missing = [];
  const mismatched = [];

  for (const [id, expected] of Object.entries(CYBERMANCY_DOMAINS)) {
    const actual = allDomains[id];
    if (!actual) {
      missing.push(id);
      continue;
    }
    if (!domainEquals(actual, expected)) mismatched.push(id);
  }

  return {
    valid: missing.length === 0 && mismatched.length === 0,
    missing,
    mismatched
  };
}

/**
 * Persist Cybermancy Domains into Daggerheart's native world-scoped Homebrew
 * setting. A GM is required to make the world-level setting change.
 */
export async function registerCybermancyDomains({ notify = true } = {}) {
  if (!globalThis.game || !globalThis.CONFIG?.DH) {
    throw new Error("Cybermancy Domains require an initialized Daggerheart world.");
  }

  const settingNamespace = CONFIG.DH.id;
  const settingKey = CONFIG.DH.SETTINGS.gameSettings.Homebrew;
  const currentModel = game.settings.get(settingNamespace, settingKey);
  const current = currentModel?.toObject
    ? currentModel.toObject()
    : structuredClone(currentModel ?? {});
  const homebrewDomains = current.domains ?? {};
  const coreDomains = CONFIG.DH.DOMAIN.domains ?? {};

  const plan = planDomainRegistration({ coreDomains, homebrewDomains });

  if (plan.coreConflicts.length) {
    const message =
      `Cybermancy | Cannot register Domains because IDs collide with Daggerheart core domains: ${plan.coreConflicts.join(", ")}. Restore an unmodified Daggerheart installation before enabling Cybermancy.`;
    console.error(message);
    if (notify && game.user?.isGM) ui.notifications?.error(message);
    return { status: "core-conflict", ...plan };
  }

  if (plan.conflicts.length) {
    const ids = plan.conflicts.map(entry => entry.id);
    const message =
      `Cybermancy | Existing Homebrew Domains conflict with Cybermancy: ${ids.join(", ")}. Existing world data was preserved.`;
    console.warn(message, plan.conflicts);
    if (notify && game.user?.isGM) ui.notifications?.warn(message);
    return { status: "homebrew-conflict", ...plan };
  }

  if (!game.user?.isGM) {
    const audit = auditCybermancyDomains(CONFIG.DH.DOMAIN.allDomains());
    if (!audit.valid) {
      console.warn(
        "Cybermancy | Domains are not fully registered. A GM must enter the world with Cybermancy enabled.",
        audit
      );
    }
    return {
      status: audit.valid ? "already-registered" : "gm-required",
      ...plan,
      audit
    };
  }

  if (plan.changed) {
    await game.settings.set(settingNamespace, settingKey, {
      ...current,
      domains: plan.nextDomains
    });
  }

  const audit = auditCybermancyDomains(CONFIG.DH.DOMAIN.allDomains());
  if (!audit.valid) {
    const message =
      `Cybermancy | Domain registration did not validate. Missing: ${audit.missing.join(", ") || "none"}; mismatched: ${audit.mismatched.join(", ") || "none"}.`;
    console.error(message, audit);
    if (notify) ui.notifications?.error(message);
    return { status: "validation-failed", ...plan, audit };
  }

  console.info(
    `Cybermancy | Domains ready (${Object.keys(CYBERMANCY_DOMAINS).length}); added ${plan.added.length}, unchanged ${plan.unchanged.length}.`
  );

  return {
    status: plan.changed ? "registered" : "already-registered",
    ...plan,
    audit
  };
}
