import {
  registerCybermancyDomains,
  auditCybermancyDomains,
  auditCybermancyRuntime,
  CYBERMANCY_DOMAINS
} from "./domains.js";
import { registerCybermancyHooks } from "./hooks.js";
import { CybermancyWeaponSheet } from "./sheets/CybermancyWeaponSheet.js";
import { CybermancyRunnerSheet } from "./sheets/CybermancyRunnerSheet.js";

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

  game.settings.register("cybermancy", "enableSmartlink", {
    name: "Enable Smartlink Edge Bonus",
    hint: "Apply +1 Edge on qualifying attacks when Smartlink flag is set.",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });

  Items.registerSheet("cybermancy", CybermancyWeaponSheet, {
    types: ["weapon"],
    makeDefault: false,
    label: "Cybermancy Weapon Sheet"
  });

  Actors.registerSheet("cybermancy", CybermancyRunnerSheet, {
    types: ["character"],
    makeDefault: false,
    label: "Cybermancy Runner Sheet"
  });
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
