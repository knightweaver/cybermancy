// Cybermancy – Folder Loader with Validation (recursive)
// - Pick a folder via FilePicker
// - Recursively find all .json files
// - Validate each against pragmatic Daggerheart Item rules (weapon, armor, consumable, loot)
// - Show a report (errors/warnings) and let you import All Valid or Selected rows
//
// Tested on Foundry v11–v13.

(async () => {
  // ---------------- helpers ----------------
  const isStr = (v) => typeof v === "string" && v.trim().length > 0;
  const isNum = (v) => typeof v === "number" && Number.isFinite(v);
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);

  function validateItem(doc) {
    const errors = [];
    const warnings = [];

    // Basic
    if (!isStr(doc?.name)) errors.push(`Missing or invalid "name" (string required).`);
    if (!isStr(doc?.type)) errors.push(`Missing or invalid "type" (string required).`);
    const subtype = String(doc?.type || "").toLowerCase();
    const allowed = new Set(["weapon", "armor", "consumable", "loot"]);
    if (!allowed.has(subtype)) errors.push(`Unsupported item subtype "${doc?.type}". Allowed: weapon, armor, consumable, loot.`);
    if (!isObj(doc?.system)) errors.push(`Missing or invalid "system" (object required).`);

    // Subtype specifics
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
      if (bt && (!isNum(bt.major) || !isNum(bt.severe))) errors.push(`armor: "system.baseThresholds.major" and ".severe" must be numbers.`);
      if (!isNum(doc?.system?.tier)) warnings.push(`armor: "system.tier" should be a number (e.g., 1).`);
    }
    if (subtype === "consumable") {
      if (!("actions" in (doc.system || {})) && !("effect" in (doc.system || {}))) {
        warnings.push(`consumable: consider adding "system.actions" or "system.effect".`);
      }
    }
    if (subtype === "loot") {
      if (!isStr(doc?.system?.description) && !isStr(doc?.system?.text)) {
        warnings.push(`loot: add "system.description" or "system.text" for clarity.`);
      }
    }

    // Effects hints
    if (Array.isArray(doc?.effects)) {
      for (let i = 0; i < doc.effects.length; i++) {
        const e = doc.effects[i];
        if (!isObj(e)) { warnings.push(`effects[${i}] is not an object.`); continue; }
        if (!isStr(e.name)) warnings.push(`effects[${i}]: missing "name".`);
        if (!Array.isArray(e.changes)) warnings.push(`effects[${i}]: "changes" should be an array.`);
        if (e.transfer !== true) warnings.push(`effects[${i}]: consider "transfer: true" if equipping should apply it.`);
      }
    }
    return { errors, warnings };
  }

  function fileRowHtml(idx, path, name, status, messages) {
    const esc = foundry.utils.escapeHTML;
    const msgList = messages.map(m => `<div>${esc(m)}</div>`).join("");
    const color = status === "OK" ? "#3bb273" : status === "WARN" ? "#f0ad4e" : "#d9534f";
    return `
      <tr data-index="${idx}">
        <td><input type="checkbox" name="sel" value="${idx}" ${status!=="ERR" ? "checked" : "disabled"}></td>
        <td title="${esc(path)}"><code>${esc(name)}</code></td>
        <td style="color:${color}; font-weight:600;">${esc(status)}</td>
        <td>${msgList || "<span style='opacity:.7'>(none)</span>"}</td>
      </tr>
    `;
  }

  function buildReportTable(results) {
    const rows = results.map((r, i) => {
      const messages = [];
      if (r.errors.length) messages.push(...r.errors.map(e => `❌ ${e}`));
      if (r.warnings.length) messages.push(...r.warnings.map(w => `⚠️ ${w}`));
      const status = r.errors.length ? "ERR" : (r.warnings.length ? "WARN" : "OK");
      return fileRowHtml(i, r.path, r.name, status, messages);
    }).join("");
    return `
      <form class="cybermancy-validate">
        <style>
          .cybermancy-validate table { width:100%; border-collapse:collapse; }
          .cybermancy-validate th, .cybermancy-validate td { border-bottom:1px solid #444; padding:.35rem .5rem; vertical-align: top; }
          .cybermancy-validate thead th { position: sticky; top: 0; background: #1e1e1e; }
          .cybermancy-validate .toolbar { display:flex; gap:.5rem; margin-bottom:.5rem; }
        </style>
        <div class="toolbar">
          <button type="button" data-action="select-all">Select All Valid</button>
          <button type="button" data-action="select-none">Select None</button>
        </div>
        <div style="max-height: 420px; overflow:auto;">
          <table>
            <thead>
              <tr>
                <th style="width: 2rem;"></th>
                <th>File</th>
                <th>Status</th>
                <th>Messages</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      </form>
    `;
  }

  async function pickFolder() {
    return new Promise((resolve) => {
      const fp = new FilePicker({
        type: "any",
        current: "modules/",
        callback: (path) => resolve(path.endsWith("/") ? path : (path + "/"))
      });
      fp.render(true);
    });
  }

  async function browseRecursive(root) {
    const out = [];
    // Guess source: use 'data' for modules/ and worlds/, otherwise default to 'data'
    const source = "data";
    async function walk(dir) {
      const res = await FilePicker.browse(source, dir, { wildcard: false });
      for (const f of res.files) {
        if (f.toLowerCase().endsWith(".json")) out.push(f);
      }
      for (const d of res.dirs) await walk(d.endsWith("/") ? d : d + "/");
    }
    await walk(root);
    return out;
  }

  async function loadJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.json();
  }

  // ---------------- flow ----------------
  // 1) Select a folder
  const folder = await pickFolder();
  if (!folder) return;

  // 2) Recursively collect .json files
  let files = [];
  try {
    files = await browseRecursive(folder);
  } catch (err) {
    ui.notifications.error(`Failed to browse folder: ${err.message}`);
    console.error(err);
    return;
  }
  if (!files.length) {
    ui.notifications.warn(`No .json files found under: ${folder}`);
    return;
  }

  // 3) Validate all files
  const results = [];
  for (const path of files) {
    const name = path.split("/").pop();
    try {
      const data = await loadJson(path);
      const { errors, warnings } = validateItem(data);
      results.push({ path, name, data, errors, warnings });
    } catch (err) {
      results.push({ path, name, data: null, errors: [`Fetch/parse failed: ${err.message}`], warnings: [] });
    }
  }

  // 4) Show report and let the user choose what to import
  const content = buildReportTable(results);
  let chosenIndexes = null;

  const dlg = new Dialog({
    title: `Cybermancy — Validate & Import (${files.length} file${files.length!==1?"s":""})`,
    content,
    buttons: {
      importSelected: {
        label: "Import Selected",
        icon: '<i class="fas fa-file-import"></i>',
        callback: html => {
          const checks = html[0].querySelectorAll('input[type="checkbox"][name="sel"]:checked');
          chosenIndexes = Array.from(checks).map(c => Number(c.value));
        }
      },
      importAllValid: {
        label: "Import All Valid",
        callback: () => {
          chosenIndexes = results
            .map((r, i) => ({r, i}))
            .filter(x => x.r.errors.length === 0)
            .map(x => x.i);
        }
      },
      cancel: { label: "Cancel" }
    },
    render: html => {
      const form = html.find("form.cybermancy-validate");
      form.on("click", 'button[data-action="select-all"]', ev => {
        ev.preventDefault();
        form.find('tbody tr').each((_, tr) => {
          const statusCell = tr.children[2]?.textContent?.trim();
          const cb = tr.querySelector('input[type="checkbox"]');
          if (cb && statusCell !== "ERR") cb.checked = true;
        });
      });
      form.on("click", 'button[data-action="select-none"]', ev => {
        ev.preventDefault();
        form.find('input[type="checkbox"]').prop("checked", false);
      });
    },
    default: "importSelected",
    close: async () => {
      if (!Array.isArray(chosenIndexes)) return;

      const docs = chosenIndexes.map(i => results[i]).filter(r => r && r.data && r.errors.length === 0).map(r => r.data);
      if (!docs.length) {
        ui.notifications.warn("No valid documents selected to import.");
        return;
      }
      try {
        const created = await Item.createDocuments(docs, { renderSheet: false });
        ui.notifications.info(`Imported ${created.length} item${created.length!==1?"s":""}.`);
        // Optionally open the first created sheet
        if (created[0]?.sheet) created[0].sheet.render(true);
      } catch (err) {
        ui.notifications.error(`Import failed: ${err.message}`);
        console.error(err);
      }
    }
  });

  dlg.render(true);
})();