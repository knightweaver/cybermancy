/**
 * Direct Import Cybermancy Actor JSON.js
 *
 * Directly imports one or more Foundry Actor JSON files into the world.
 * Intended for Cybermancy/Daggerheart adversaries and environments.
 *
 * Based on the Actor validation/import logic from "Validate and Load w Folders.js".
 *
 * Features:
 * - Select one or more local .json files.
 * - Validates basic Actor structure and embedded Feature actions.
 * - Imports adversaries/environments directly without first creating a blank Actor.
 * - Optional target Actor folder.
 * - Existing-name behavior: Create Another / Replace Existing / Skip.
 * - Optional opening of imported Actor sheets.
 *
 * Target: Foundry VTT v13 / Daggerheart 1.2.x
 */

(async () => {
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);
  const isStr = (v) => typeof v === "string" || v instanceof String;

  function validateActionList(actions, ctx = "feature") {
    const errors = [];
    const warnings = [];

    if (!Array.isArray(actions)) {
      warnings.push(`${ctx}: "system.actions" is not an array; skipping detailed action validation.`);
      return { errors, warnings };
    }

    for (let i = 0; i < actions.length; i++) {
      const a = actions[i];
      if (!isObj(a)) {
        errors.push(`${ctx}: action[${i}] is not an object.`);
        continue;
      }

      if (!isStr(a.name)) errors.push(`${ctx}: action[${i}] missing "name" (string).`);
      if (!isStr(a.type) || !["attack", "effect"].includes(a.type))
        errors.push(`${ctx}: action[${i}] invalid "type" (attack|effect).`);

      if ("systemPath" in a && a.systemPath !== "actions")
        errors.push(`${ctx}: action[${i}] must have systemPath:"actions" when present.`);

      if ("actionType" in a && !["action", "reaction", "passive"].includes(a.actionType))
        errors.push(`${ctx}: action[${i}] invalid "actionType" (action|reaction|passive).`);
    }

    return { errors, warnings };
  }

  function validateActor(doc) {
    const errors = [];
    const warnings = [];

    if (!isObj(doc)) {
      errors.push("Top-level JSON value must be an object.");
      return { errors, warnings };
    }

    if (!isStr(doc.name) || !doc.name.trim()) errors.push(`actor: "name" (string) is required.`);
    if (!isStr(doc.type) || !doc.type.trim()) errors.push(`actor: "type" (string) is required.`);
    if (!isObj(doc.system)) errors.push(`actor: "system" (object) is required.`);

    const allowed = new Set(["adversary", "environment"]);
    if (isStr(doc.type) && !allowed.has(String(doc.type).toLowerCase())) {
      warnings.push(`Actor type "${doc.type}" is not adversary/environment. It will still be imported if Foundry accepts it.`);
    }

    if (Array.isArray(doc.items)) {
      for (let i = 0; i < doc.items.length; i++) {
        const item = doc.items[i];
        if (!isObj(item)) {
          errors.push(`items[${i}] is not an object.`);
          continue;
        }

        if (item.type === "feature" && item.system && "actions" in item.system) {
          const r = validateActionList(item.system.actions, `items[${i}](${item.name ?? "feature"})`);
          errors.push(...r.errors);
          warnings.push(...r.warnings);
        }
      }
    }

    return { errors, warnings };
  }

  function sanitizeForCreate(data) {
    const clone = foundry.utils.deepClone
      ? foundry.utils.deepClone(data)
      : foundry.utils.duplicate(data);

    // Remove top-level identity / provenance that should not be reused for a new world Actor.
    delete clone._id;
    delete clone._key;
    delete clone.folder;

    // Preserve system data and embedded Item IDs. Foundry can create embedded Items from them,
    // and Package Builder intentionally keeps their internal relationships consistent.

    return clone;
  }

  function getActorFolders() {
    return game.folders
      .filter(f => f.type === "Actor")
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  function actorFolderOptions() {
    const folders = getActorFolders();
    return [
      `<option value="">(Root)</option>`,
      ...folders.map(f => `<option value="${f.id}">${foundry.utils.escapeHTML(f.name)}</option>`)
    ].join("");
  }

  async function chooseFiles() {
    return new Promise(resolve => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".json,application/json";
      input.multiple = true;
      input.style.display = "none";

      input.addEventListener("change", () => {
        const files = Array.from(input.files ?? []);
        input.remove();
        resolve(files);
      }, { once: true });

      document.body.appendChild(input);
      input.click();
    });
  }

  async function readJsonFile(file) {
    const text = await file.text();
    try {
      return JSON.parse(text);
    } catch (err) {
      throw new Error(`Invalid JSON in "${file.name}": ${err.message ?? err}`);
    }
  }

  async function getOptions(files) {
    const fileNames = files.map(f => `<li>${foundry.utils.escapeHTML(f.name)}</li>`).join("");

    const content = `
      <form>
        <p><strong>Selected JSON files:</strong></p>
        <ul style="max-height:120px;overflow:auto">${fileNames}</ul>

        <div class="form-group">
          <label>Target Actor Folder</label>
          <select name="folder">${actorFolderOptions()}</select>
        </div>

        <div class="form-group">
          <label>When same name + type already exists</label>
          <select name="existing">
            <option value="create">Create another Actor</option>
            <option value="replace">Replace existing Actor</option>
            <option value="skip">Skip</option>
          </select>
        </div>

        <div class="form-group">
          <label class="checkbox">
            <input type="checkbox" name="openSheet" checked />
            Open imported Actor sheet
          </label>
        </div>
      </form>
    `;

    return new Promise(resolve => {
      new Dialog({
        title: "Direct Import Cybermancy Actor JSON",
        content,
        buttons: {
          import: {
            icon: '<i class="fas fa-file-import"></i>',
            label: "Import",
            callback: html => resolve({
              folderId: html.find('select[name="folder"]').val() || null,
              existing: html.find('select[name="existing"]').val(),
              openSheet: html.find('input[name="openSheet"]')[0].checked
            })
          },
          cancel: {
            icon: '<i class="fas fa-times"></i>',
            label: "Cancel",
            callback: () => resolve(null)
          }
        },
        default: "import",
        close: () => resolve(null)
      }).render(true);
    });
  }

  function findExisting(data) {
    return game.actors.find(a =>
      a.name === data.name &&
      String(a.type).toLowerCase() === String(data.type).toLowerCase()
    ) ?? null;
  }

  async function createActor(data, folderId) {
    const createData = sanitizeForCreate(data);
    if (folderId) createData.folder = folderId;

    return Actor.create(createData, {
      renderSheet: false
    });
  }

  async function replaceActor(existing, data, folderId) {
    // Foundry's importFromJSON mirrors the normal Actor "Import Data" operation,
    // but invokes it directly on the matching Actor.
    const imported = foundry.utils.deepClone
      ? foundry.utils.deepClone(data)
      : foundry.utils.duplicate(data);

    delete imported._key;
    delete imported.folder;

    // Keep the existing world's Actor identity.
    imported._id = existing.id;

    await existing.importFromJSON(JSON.stringify(imported));

    if (folderId && existing.folder?.id !== folderId) {
      await existing.update({ folder: folderId });
    }

    return existing;
  }

  // ---- Main ----

  const files = await chooseFiles();
  if (!files.length) return;

  const options = await getOptions(files);
  if (!options) return;

  const summary = {
    imported: [],
    replaced: [],
    skipped: [],
    failed: []
  };

  for (const file of files) {
    try {
      const data = await readJsonFile(file);
      const { errors, warnings } = validateActor(data);

      if (warnings.length) {
        console.warn(`[Cybermancy Import] ${file.name} warnings:`, warnings);
      }

      if (errors.length) {
        console.error(`[Cybermancy Import] ${file.name} validation failed:`, errors);
        summary.failed.push({ file: file.name, errors });
        continue;
      }

      const existing = findExisting(data);
      let actor = null;

      if (existing && options.existing === "skip") {
        console.log(`[Cybermancy Import] Skipped existing Actor: ${existing.name}`);
        summary.skipped.push(existing.name);
        continue;
      }

      if (existing && options.existing === "replace") {
        actor = await replaceActor(existing, data, options.folderId);
        summary.replaced.push(actor.name);
        console.log(`[Cybermancy Import] Replaced: ${actor.uuid}`);
      } else {
        actor = await createActor(data, options.folderId);
        summary.imported.push(actor.name);
        console.log(`[Cybermancy Import] Created: ${actor.uuid}`);
      }

      if (actor && options.openSheet) {
        actor.sheet?.render(true);
      }

    } catch (err) {
      console.error(`[Cybermancy Import] Failed "${file.name}"`, err);
      summary.failed.push({
        file: file.name,
        errors: [String(err?.message ?? err)]
      });
    }
  }

  const parts = [];
  if (summary.imported.length) parts.push(`${summary.imported.length} created`);
  if (summary.replaced.length) parts.push(`${summary.replaced.length} replaced`);
  if (summary.skipped.length) parts.push(`${summary.skipped.length} skipped`);
  if (summary.failed.length) parts.push(`${summary.failed.length} failed`);

  const msg = `Cybermancy import: ${parts.join(", ") || "nothing imported"}.`;

  if (summary.failed.length) {
    ui.notifications.error(msg + " See console for details.");
  } else {
    ui.notifications.info(msg);
  }

  console.log("[Cybermancy Import] Summary", summary);
})();
