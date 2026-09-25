import {
  registerCybermancyDomains,
  auditCybermancyDomains,
  auditCybermancyRuntime,
  CYBERMANCY_DOMAINS
} from "./domains.js";
import { registerCybermancyHooks } from "./hooks.js";

Hooks.once("init", function () {
  console.log("Cybermancy | init");

  const module = game.modules.get("cybermancy");
  if (module) {
    module.api = {
      domains: CYBERMANCY_DOMAINS,
      auditDomains: auditCybermancyDomains,
      auditRuntime: auditCybermancyRuntime,
      registerDomains: registerCybermancyDomains
    };
  }

  // Cybermancy v0.2.0 intentionally uses Daggerheart 2's native
  // ApplicationV2 character and weapon sheets. The retired v0.1.x custom
  // sheets used legacy ActorSheet/ItemSheet APIs and a manual d20 attack path.
});

Hooks.once("ready", async function () {
  console.log("Cybermancy | ready");
  registerCybermancyHooks();

  try {
    const runtime = auditCybermancyRuntime();
    if (!runtime.valid) {
      throw new Error(`Unsupported or incomplete Daggerheart runtime: ${JSON.stringify(runtime)}`);
    }
    if (!runtime.exactQualificationTarget) {
      console.warn(
        `Cybermancy | Running Daggerheart ${runtime.systemVersion}; v0.2.0 qualification target is Daggerheart ${runtime.qualificationTarget}.`
      );
    }

    const result = await registerCybermancyDomains();
    console.log(`Cybermancy | Domain registration status: ${result.status}`);
  } catch (error) {
    console.error("Cybermancy | Domain registration failed.", error);
    if (game.user?.isGM) {
      ui.notifications?.error(
        "Cybermancy could not initialize its Daggerheart Domains. See the console for details."
      );
    }
  }
});
