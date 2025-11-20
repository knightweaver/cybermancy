/**
 * validate-and-load-folder.fixed.js (folder + Actor support)
 * - Supports Items and Actors (e.g., adversaries).
 * - Ensures domainCard compendium/world folder paths reuse shared folders:
 *   <domain>/<level> with many cards inside each level folder.
 */

(function() {
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);
  const isStr = (v) => typeof v === "string" || v instanceof String;
  const isBool = (v) => typeof v === "boolean";

  function guessDocumentKind(doc) {
    if (!doc) return "Item";
    if (doc.documentType === "Actor") return "Actor";
    if (doc.documentType === "Item") return "Item";
    const t = String(doc.type ?? "").toLowerCase();
    const actorTypes = new Set(["character", "pc", "npc", "adversary", "creature"]);
    if (actorTypes.has(t)) return "Actor";
    return "Item";
  }

  function normalizeDoc(doc) {
    const inv = doc?.system?.inVault;
    if (typeof inv === "string") {
      const v = inv.trim().toLowerCase();
      if (v === "true" || v === "false") doc.system.inVault = (v === "true");
    }
    return doc;
  }

  function basicItemChecks(doc) {
    const errors = [];
    if (!isStr(doc?.name) || !doc.name.trim()) errors.push(`item: "name" (string) is required.`);
    if (!isStr(doc?.type)) errors.push(`item: "type" (string) is required.`);
    if (!isObj(doc?.system)) errors.push(`item: "system" (object) is required.`);
    return errors;
  }

  function basicActorChecks(doc) {
    const errors = [];
    if (!isStr(doc?.name) || !doc.name.trim()) errors.push(`actor: "name" (string) is required.`);
    if (!isStr(doc?.type)) errors.push(`actor: "type" (string) is required.`);
    if (!isObj(doc?.system)) errors.push(`actor: "system" (object) is required.`);
    return errors;
  }

  function validateActionList(actions, ctx = "feature") {
    const errors = [];
    const warnings = [];

    if (!Array.isArray(actions)) {
      warnings.push(`${ctx}: "system.actions" is not an array; skipping detailed action validation.`);
      return { errors, warnings };
    }

    if (!actions.length) warnings.push(`${ctx}: "system.actions" is empty.`);
    for (let i = 0; i < actions.length; i++) {
      const a = actions[i];
      if (!isObj(a)) { errors.push(`${ctx}: action[${i}] is not an object.`); continue; }
      if (!isStr(a.name)) errors.push(`${ctx}: action[${i}] missing "name" (string).`);
      if (!isStr(a.type) || !["attack","effect"].includes(a.type))
        errors.push(`${ctx}: action[${i}] invalid "type" (attack|effect).`);
      if (!isStr(a.systemPath) || a.systemPath !== "actions")
        errors.push(`${ctx}: action[${i}] must have systemPath:"actions".`);
      if (!isStr(a.actionType) || !["action","reaction","passive"].includes(a.actionType))
        errors.push(`${ctx}: action[${i}] invalid "actionType" (action|reaction|passive).`);
      if (!("chatDisplay" in a)) warnings.push(`${ctx}: action[${i}] missing "chatDisplay" (bool).`);
      if (!isStr(a.img)) warnings.push(`${ctx}: action[${i}] missing/invalid "img" (string).`);
      if (!("target" in a)) warnings.push(`${ctx}: action[${i}] missing "target".`);
      if (a.type === "attack") {
        const dmg = a.damage;
        if (!isObj(dmg)) warnings.push(`${ctx}: action[${i}] attack missing "damage" object.`);
        else if (!Array.isArray(dmg.parts)) warnings.push(`${ctx}: action[${i}] attack "damage.parts" should be an array.`);
        const roll = a.roll;
        if (!isObj(roll)) warnings.push(`${ctx}: action[${i}] attack missing "roll" object.`);
      }
    }
    return { errors, warnings };
  }

  function validateByType(doc) {
    const errors = [];
    const warnings = [];

    const kind = guessDocumentKind(doc);

    if (kind === "Actor") {
      const baseErrs = basicActorChecks(doc);
      errors.push(...baseErrs);
      if (baseErrs.length) return { errors, warnings };

      const subtype = doc.type;
      // Light-touch validation: check actions if present
      if ("actions" in (doc.system || {})) {
        const { errors: e2, warnings: w2 } = validateActionList(doc.system.actions, `actor(${subtype})`);
        errors.push(...e2); warnings.push(...w2);
      }
      return { errors, warnings };
    }

    // Item path (existing behavior)
    const baseErrs = basicItemChecks(doc);
    errors.push(...baseErrs);
    if (baseErrs.length) return { errors, warnings };

    const subtype = doc.type;
    if (subtype === "feature") {
      if (!isStr(doc?.system?.description)) errors.push(`feature: "system.description" (string) is required.`);
      if ("actions" in (doc.system || {})) {
        const { errors: e2, warnings: w2 } = validateActionList(doc.system.actions, "feature");
        errors.push(...e2); warnings.push(...w2);
      } else {
        warnings.push(`feature: no "system.actions" found (feature will import without a button/action).`);
      }
    }
    if (subtype === "domainCard") {
      if ("inVault" in (doc.system || {})) {
        if (!isBool(doc.system.inVault)) errors.push(`domainCard: "system.inVault" must be boolean.`);
      }
    }
    return { errors, warnings };
  }

  async function fetchJsonFromDataPath(path) {
    const assets = foundry.utils?.getRoute?.("assets");
    if (assets) {
      const url = `${assets}?path=${encodeURIComponent(path)}`;
      const r = await fetch(url, { cache: "no-store" });
      if (r.ok) return await r.json();
    }
    const r2 = await fetch(path, { cache: "no-store" });
    if (!r2.ok) throw new Error(`HTTP ${r2.status} for ${path}`);
    return await r2.json();
  }

  async function* walkDataTree(dir) {
    const browse = await FilePicker.browse("data", dir);
    for (const d of browse.dirs) {
      yield* walkDataTree(d);
    }
    for (const f of browse.files) {
      if (f.toLowerCase().endsWith(".json")) yield f;
    }
  }

  // --- Folder helpers with caching ---
  const worldFolderCache = new Map();     // key: `${type}::${parentId||root}::${name}` => Folder
  const packFolderCache  = new Map();     // key: `${pack.collection}::${parentId||root}::${name}` => Folder

  async function ensureWorldFolderPath(names, type = "Item") {
    let parentId = null;
    let folderDoc = null;
    for (const name of names) {
      const key = `${type}::${parentId ?? "root"}::${name}`;
      folderDoc = worldFolderCache.get(key);
      if (!folderDoc) {
        folderDoc = game.folders.find(f => f.type === type && f.name === name && (f.parent?.id ?? null) === parentId) || null;
        if (!folderDoc) {
          folderDoc = await Folder.create({ name, type, parent: parentId });
        }
        worldFolderCache.set(key, folderDoc);
      }
      parentId = folderDoc.id;
    }
    return folderDoc;
  }

  async function refreshPackFolders(pack) {
    try {
      if (typeof pack.getIndex === "function") await pack.getIndex({ fields: ["folder"] });
      // No direct refresh API for folders; rely on pack.folders getter if present
    } catch (e) {
      // ignore
    }
  }

  async function ensureCompendiumFolderPath(pack, names) {
    let parentId = null;
    let folder = null;
    for (const name of names) {
      const key = `${pack.collection}::${parentId ?? "root"}::${name}`;
      folder = packFolderCache.get(key);
      if (!folder) {
        const existing = pack.folders ? Array.from(pack.folders) : [];
        folder = existing.find(f => f.name === name && (f.parent?.id ?? null) === parentId) || null;
        if (!folder) {
          if (typeof pack.createFolder === "function") {
            folder = await pack.createFolder({ name, parent: parentId });
          } else if (typeof Folder.create === "function") {
            folder = await Folder.create({ name, type: "Compendium", parent: parentId, pack: pack.collection });
          } else {
            console.warn(`Compendium folder API not available for ${pack.collection}. Skipping folder organization.`);
            return null;
          }
          await refreshPackFolders(pack);
        }
        packFolderCache.set(key, folder);
      }
      parentId = folder.id;
    }
    return folder;
  }

  async function loadIntoCompendium(packName, docData) {
    const pack = game.packs.get(packName);
    if (!pack) throw new Error(`Compendium not found: ${packName}`);

    const kind = guessDocumentKind(docData);
    const DocCls = pack.documentClass
      ?? (kind === "Actor" ? game.actors.documentClass : game.items.documentClass);

    // Reuse shared <domain>/<level> path for domainCard items
    const isDomainCard = (kind === "Item" && docData?.type === "domainCard");
    if (isDomainCard) {
      const domainName = String(docData?.system?.domain ?? "Unknown").trim() || "Unknown";
      const levelName = String(docData?.system?.level ?? "0");
      const compFolder = await ensureCompendiumFolderPath(pack, [domainName, levelName]);
      if (compFolder?.id) docData.folder = compFolder.id;
    }

    const doc = new DocCls(docData);
    const created = await pack.importDocument(doc);

    // If folder assignment failed pre-import, try after
    if (created && isDomainCard && !created.folder && docData.folder) {
      try { await created.update({ folder: docData.folder }); } catch (e) { console.warn(`Assign compendium folder failed: ${created.name}`, e); }
    }
    return created;
  }

  async function createInWorld(docData) {
    const kind = guessDocumentKind(docData);

    if (kind === "Actor") {
      // No special foldering rules yet; drop in root or user-managed folders.
      return await Actor.create(docData, { renderSheet: false });
    }

    // Item path
    if (docData?.type === "domainCard") {
      const domainName = String(docData?.system?.domain ?? "Unknown").trim() || "Unknown";
      const levelName = String(docData?.system?.level ?? "0");
      const folder = await ensureWorldFolderPath([domainName, levelName], "Item");
      docData.folder = folder?.id ?? null;
    }
    return await Item.create(docData, { renderSheet: false });
  }

  async function run({ folder, pack, dryRun = true, toWorld = false } = {}) {
    if (!isStr(folder) || !folder) throw new Error(`Provide a 'folder' (data path).`);

    const results = [];
    for await (const file of walkDataTree(folder)) {
      try {
        const json = await fetchJsonFromDataPath(file);
        const doc = normalizeDoc(json);

        const { errors, warnings } = validateByType(doc);
        results.push({ file, errors, warnings });

        if (errors.length) {
          console.warn(`[Validate] ${file}`, { errors, warnings });
          continue;
        }

        if (!dryRun) {
          if (toWorld || !pack) {
            const created = await createInWorld(foundry.utils.duplicate(doc));
            console.log(`[World Imported] ${created?.uuid ?? created?.id} <= ${file}`);
          } else {
            const created = await loadIntoCompendium(pack, foundry.utils.duplicate(doc));
            console.log(`[Pack Imported] ${created?.uuid ?? created?.id} <= ${file}`);
          }
        } else {
          console.log(`[Validated] ${file}`, { warnings });
        }
      } catch (err) {
        console.error(`[Error] ${file}`, err);
        results.push({ file, errors: [String(err)], warnings: [] });
      }
    }

    const summary = {
      total: results.length,
      ok: results.filter(r => r.errors.length === 0).length,
      withWarnings: results.filter(r => r.errors.length === 0 && r.warnings.length > 0).length,
      withErrors: results.filter(r => r.errors.length > 0).length
    };
    console.table(summary);
    ui.notifications?.info(`ValidateAndLoad: total ${summary.total}, ok ${summary.ok}, errors ${summary.withErrors}`);
    return { summary, results };
  }

  async function openDialogAndRun() {
    const packs = Array.from(game.packs).filter(p => ["Item", "Actor"].includes(p.documentName));
    const packOptions = ['<option value="">(Validate Only)</option>']
      .concat(packs.map(p => `<option value="${p.collection}">${p.title} — ${p.collection} [${p.documentName}]</option>`))
      .join("");

    const content = `
      <form>
        <div class="form-group">
          <label>Start Folder (data path)</label>
          <div class="flexrow">
            <input type="text" name="folder" placeholder="worlds/YourWorld/data/..." />
            <button type="button" class="filepicker"><i class="fas fa-folder-open"></i></button>
          </div>
        </div>
        <div class="form-group">
          <label>Target Compendium (optional)</label>
          <select name="pack">${packOptions}</select>
        </div>
        <div class="form-group">
          <label class="checkbox"><input type="checkbox" name="toWorld" /> Import to World (ignores pack)</label>
        </div>
        <div class="form-group">
          <label class="checkbox"><input type="checkbox" name="dryRun" checked /> Dry Run (validation only)</label>
        </div>
      </form>
    `;

    return await new Promise((resolve) => {
      const dlg = new Dialog({
        title: "Validate & Load JSON Folder",
        content,
        buttons: {
          run: {
            label: "Run",
            callback: async html => {
              const folder = html.find('input[name="folder"]').val()?.trim();
              const pack = html.find('select[name="pack"]').val()?.trim();
              const toWorld = html.find('input[name="toWorld"]')[0].checked;
              const dryRun = html.find('input[name="dryRun"]')[0].checked;
              if (!folder) return ui.notifications?.error("Select a folder.");
              resolve({ folder, pack, dryRun, toWorld });
            }
          },
          cancel: { label: "Cancel", callback: () => resolve(null) }
        },
        default: "run",
        render: html => {
          html.find("button.filepicker").on("click", async ev => {
            const fp = new FilePicker({
              type: "folder",
              current: "data",
              callback: (path) => {
                html.find('input[name="folder"]').val(path);
              }
            });
            fp.browse("data");
          });
        }
      });
      dlg.render(true);
    });
  }

  const API = { run };
  window.ValidateAndLoad = API;

  (async () => {
    try {
      const opts = await openDialogAndRun();
      if (!opts) return;
      await API.run(opts);
    } catch (e) {
      console.error("ValidateAndLoad macro error:", e);
      ui.notifications?.error(`ValidateAndLoad failed: ${e.message ?? e}`);
    }
  })();
})();