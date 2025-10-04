import { registerCybermancyHooks } from "./hooks.js";
import { CybermancyWeaponSheet } from "./sheets/CybermancyWeaponSheet.js";
import { CybermancyRunnerSheet } from "./sheets/CybermancyRunnerSheet.js";

Hooks.once("init", function () {
  console.log("Cybermancy | init");

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

Hooks.once("ready", function () {
  console.log("Cybermancy | ready");
  registerCybermancyHooks();
});
