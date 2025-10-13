// Cybermancy - Safe Loader: validate a JSON Item before importing it
// Works for Daggerheart Item subtypes: weapon, armor, consumable, loot
// Usage: run macro → choose a JSON file → see validation report → (optionally) import

(async () => {
  // --- helpers ---------------------------------------------------------------
  const isStr = (v) => typeof v === "string" && v.trim().length > 0;
  const isNum = (v) => typeof v === "number" && Number.isFinite(v);
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);

  function validateItem(doc) {
    const errors = [];
    const warnings = [];

    // Basic shape
    if (!isStr(doc?.name)) errors.push(`Missing or invalid "name" (string required).`);
    if (!isStr(doc?.type)) errors.push(`Missing or invalid "type" (string required).`);

    // Subtype check
    const subtype = String(doc?.type || "").toLowerCase();
    const allowed = new Set(["weapon", "armor", "consumable", "loot"]);
    if (!allowed.has(subtype)) {
      errors.push(`Unsupported item subtype "${doc?.type}". Allowed: weapon, armor, consumable, loot.`);
    }

    // System object
    if (!isObj(doc?.system)) errors.push(`Missing or invalid "system" (object required).`);

    // Subtype-specific checks
    if (subtype === "weapon") {
      const atk = doc?.system?.attack;
      if (!isObj(atk)) errors.push(`weapon: missing "system.attack" object.`);
      const dmg = atk?.damage;
      if (!isObj(dmg)) warnings.push(`weapon: missing "system.attack.damage" (no damage parts defined).`);
      if (dmg && !Array.isArray(dmg.parts)) warnings.push(`weapon: "system.attack.damage.parts" should be an array.`);
      if (!isNum(doc?.system?.tier)) warnings.push(`weapon: "system.tier" should be a number (e.g., 1).`);
    }

    if (subtype === "armor") {
      if (!isNum(doc?.system?.baseScore)) errors.push(`armor: "system.baseScore" (number) is required.`);
      const bt = doc?.system?.baseThresholds;
      if (!isObj(bt)) errors.push(`armor: "system.baseThresholds" (object) is required.`);
      if (bt && (!isNum(bt.major) || !isNum(bt.severe))) {
        errors.push(`armor: "system.baseThresholds.major" and ".severe" must be numbers.`);
      }
      if (!isNum(doc?.system?.tier)) warnings.push(`armor: "system.tier" should be a number (e.g., 1).`);
    }

    if (subtype === "consumable") {
      // Very flexible; just nudge for something actionable
      if (!("actions" in (doc.system || {})) && !("effect" in (doc.system || {}))) {
        warnings.push(`consumable: consider adding "system.actions" or "system.effect".`);
      }
    }

    if (subtype === "loot") {
      if (!isStr(doc?.system?.description) && !isStr(doc?.system?.text)) {
        warnings.push(`loot: add "system.description" or "system.text" for clarity.`);
      }
    }

    // Friendly guidance about pack-only fields (not errors for world import)
    for (const k of ["_key"]) {
      if (k in (doc || {})) {
        warnings.push(`"${k}" is pack metadata (fine to include, but not required for world import).`);
      }
    }

    // Effects sanity checks (optional)
    if (Array.isArray(doc?.effects)) {
      for (let i = 0; i < doc.effects.length; i++) {
        const e = doc.effects[i];
        if (!isObj(e)) { warnings.push(`effects[${i}] is not an object.`); continue; }
        if (!isStr(e.name)) warnings.push(`effects[${i}]: missing "name".`);
        if (!Array.isArray(e.changes)) warnings.push(`effects[${i}]: "changes" should be an array.`);
        // For armor “Heavy” pattern, a gentle check:
        if (e.transfer !== true) {
          warnings.push(`effects[${i}]: consider "transfer: true" if this should apply when item is equipped.`);
        }
      }
    }

    return { errors, warnings };
  }

  function htmlReport({ errors, warnings }, filename) {
    const errList = errors.map(e => `<li>❌ ${foundry.utils.escapeHTML(e)}</li>`).join("");
    const warnList = warnings.map(w => `<li>⚠️ ${foundry.utils.escapeHTML(w)}</li>`).join("");
    return `
      <h2 style="margin:0 0 .5rem 0;">Validation: ${filename ? foundry.utils.escapeHTML(filename) : "(untitled)"} </h2>
      <div style="max-height: 300px; overflow:auto; border:1px solid #444; padding:.5rem; border-radius:6px;">
        ${errors.length ? `<h3>Errors</h3><ul>${errList}</ul>` : `<p>No errors.</p>`}
        ${warnings.length ? `<h3>Warnings</h3><ul>${warnList}</ul>` : `<p>No warnings.</p>`}
      </div>
      <p style="margin-top:.5rem; font-size: 0.9em; opacity:.85;">
        This validator checks common Daggerheart Item fields (weapon, armor, consumable, loot).
      </p>
    `;
  }

  async function pickFile() {
    return new Promise((resolve) => {
      const fp = new FilePicker({
        type: "any",
        current: "modules/",
        callback: (path) => resolve(path)
      });
      fp.render(true);
    });
  }

  async function showReportAndConfirm(reportHtml, canProceed) {
    return Dialog.prompt({
      title: "Cybermancy – Item Validation",
      content: reportHtml,
      label: canProceed ? "Import" : "Close",
      rejectClose: true,
      callback: () => canProceed
    });
  }

  // --- flow ------------------------------------------------------------------
  // 1) Let the user pick a JSON file (you can hardcode a path if you prefer)
  const filePath = await pickFile(); // e.g., "modules/cybermancy/src-data/items/weapons/fvtt-battleaxe.json"
  if (!filePath) return;

  let data, rawName = filePath.split("/").pop();
  try {
    const res = await fetch(filePath);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    data = await res.json();
  } catch (err) {
    ui.notifications.error(`Failed to fetch/parse JSON: ${err.message}`);
    console.error(err);
    return;
  }

  // 2) Validate
  const { errors, warnings } = validateItem(data);
  const canProceed = errors.length === 0;
  const reportHtml = htmlReport({ errors, warnings }, rawName);

  const proceed = await showReportAndConfirm(reportHtml, canProceed);
  if (!proceed) return;

  // 3) Import (world-level Item)
  try {
    const [created] = await Item.createDocuments([data], { renderSheet: true });
    ui.notifications.info(`Imported item: ${created?.name ?? data.name}`);
    // Optional: open sheet
    if (created?.sheet) created.sheet.render(true);
  } catch (err) {
    ui.notifications.error(`Import failed: ${err.message}`);
    console.error(err);
  }
})();