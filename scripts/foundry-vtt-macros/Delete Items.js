/**
 * Delete Items (and Folders) Macro for Foundry VTT (v10+)
 * - World Items: choose Items ROOT or a specific Item Folder, recurse, optionally delete folders.
 * - Compendium: choose an Item pack; deletes all items in that pack.
 * - Dry run option reports counts only.
 */

(async () => {
  const isItemFolder = f => f.type === "Item";
  const allFolders = game.folders.filter(isItemFolder);
  const ROOT = "__ROOT__";

  // Gather Item compendium packs
  const itemPacks = Array.from(game.packs).filter(p => {
    // v10/11 compatibility: documentName is canonical; older used .metadata.type
    return (p.documentName ?? p?.metadata?.type) === "Item";
  });

  if (!allFolders.length && game.items.size === 0 && itemPacks.length === 0) {
    ui.notifications?.warn("No World Items/Item folders or Item compendium packs found.");
    return;
  }

  // Build World Items <select> including ROOT
  const folderOptions = [`<option value="${ROOT}">— Items (root) —</option>`]
    .concat(
      allFolders
        .slice()
        .sort((a,b)=>a.name.localeCompare(b.name))
        .map(f => `<option value="${f.id}">${f.name}</option>`)
    ).join("");

  // Build Compendium <select>
  const packOptions = itemPacks
    .sort((a,b)=>a.title.localeCompare(b.title))
    .map(p => `<option value="${p.collection}">${p.title} (${p.collection})</option>`)
    .join("");

  const html = await new Promise(resolve => {
    new Dialog({
      title: "Delete Items: World vs Compendium",
      content: `
        <form>
          <fieldset style="margin-bottom: 8px;">
            <legend>Delete From</legend>
            <label class="radio"><input type="radio" name="scope" value="world" checked> World Items</label>
            <label class="radio" style="margin-left: 1em;"><input type="radio" name="scope" value="pack" ${itemPacks.length ? "" : "disabled"}> Compendium (Item pack)</label>
          </fieldset>

          <div class="form-group">
            <label>World Root</label>
            <select name="root">${folderOptions}</select>
            <p class="notes">Used only when deleting from World Items.</p>
          </div>

          <div class="form-group">
            <label>Compendium Pack</label>
            <select name="pack" ${itemPacks.length ? "" : "disabled"}>${packOptions || "<option>(none)</option>"}</select>
            <p class="notes">Deletes <b>all</b> items in the selected pack. Pack must be unlocked.</p>
          </div>

          <div class="form-group">
            <label class="checkbox"><input type="checkbox" name="recurse" checked>
              Include subfolders (World only; if ROOT, this means *all* Item folders)
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox"><input type="checkbox" name="deleteFolders">
              Also delete folder(s) after items are removed (World only)
            </label>
          </div>
          <hr>
          <div class="form-group">
            <label class="checkbox"><input type="checkbox" name="dryRun" checked>
              Dry run (report only)
            </label>
          </div>
        </form>
      `,
      buttons: {
        run: { label: "Run", callback: html => resolve(html) },
        cancel: { label: "Cancel", callback: () => resolve(null) }
      },
      default: "run"
    }).render(true);
  });
  if (!html) return;

  const scope = html.find('input[name="scope"]:checked').val(); // "world" | "pack"
  const dryRun = html.find('input[name="dryRun"]')[0].checked;

  // --- Compendium branch ---
  if (scope === "pack") {
    const packKey = html.find('select[name="pack"]').val();
    const pack = game.packs.get(packKey);
    if (!pack) {
      ui.notifications?.error("Compendium pack not found.");
      return;
    }
    if (pack.locked) {
      ui.notifications?.error(`Pack "${pack.title}" is locked. Unlock it first.`);
      return;
    }

    const docs = await pack.getDocuments(); // all Item documents in pack
    const ids = docs.map(d => d.id);
    const summary = { scope: "Compendium", pack: pack.collection, title: pack.title, items: ids.length };

    console.log("[Delete Items] Compendium Summary", summary);

    if (dryRun) {
      ui.notifications?.info(`Dry run: ${summary.items} item(s) in pack "${summary.title}" would be deleted.`);
      return;
    }
    if (ids.length) {
      // Bulk delete via DocumentClass API, scoped to the pack
      await pack.documentClass.deleteDocuments(ids, { pack: pack.collection });
    }
    ui.notifications?.info(`Deleted ${ids.length} item(s) from compendium "${pack.title}".`);
    return;
  }

  // --- World Items branch (original behavior) ---
  const rootId = html.find('select[name="root"]').val();
  const recurse = html.find('input[name="recurse"]')[0].checked;
  const deleteFolders = html.find('input[name="deleteFolders"]')[0].checked;

  // Build parent->children map once
  const byParent = new Map();
  for (const f of allFolders) {
    const pid = f.parent?.id ?? null;
    if (!byParent.has(pid)) byParent.set(pid, []);
    byParent.get(pid).push(f);
  }

  // Post-order traversal (children before parent)
  function postOrderFrom(folder) {
    const out = [];
    (function dfs(f) {
      for (const child of (byParent.get(f.id) ?? [])) dfs(child);
      out.push(f);
    })(folder);
    return out;
  }

  // Collect folders based on selection
  let foldersOrdered = [];
  if (rootId === ROOT) {
    if (recurse) {
      const roots = byParent.get(null) ?? [];
      const out = [];
      for (const top of roots) out.push(...postOrderFrom(top));
      foldersOrdered = out;
    } else {
      foldersOrdered = [];
    }
  } else {
    const root = game.folders.get(rootId);
    if (!root) {
      ui.notifications?.error("Selected folder not found.");
      return;
    }
    foldersOrdered = recurse ? postOrderFrom(root) : [root];
  }

  const folderIdsOrdered = foldersOrdered.map(f => f.id);
  const folderIdSet = new Set(folderIdsOrdered);

  // Collect items to delete
  let itemsToDelete;
  if (rootId === ROOT) {
    itemsToDelete = recurse ? Array.from(game.items) : game.items.filter(it => !it.folder);
  } else {
    itemsToDelete = game.items.filter(it => {
      const fid = it.folder?.id ?? null;
      return fid && (fid === rootId || folderIdSet.has(fid));
    });
  }

  const itemIds = itemsToDelete.map(i => i.id);
  const summary = {
    scope: "World",
    root: (rootId === ROOT ? "Items (root)" : (game.folders.get(rootId)?.name ?? "(missing)")),
    recurse,
    items: itemIds.length,
    foldersSelected: folderIdsOrdered.length,
    willDeleteFolders: deleteFolders
  };

  console.log("[Delete Items & Folders] World Summary", summary);

  if (dryRun) {
    ui.notifications?.info(
      `Dry run: ${summary.items} item(s), ${deleteFolders ? summary.foldersSelected : 0} folder(s) would be deleted.`
    );
    return;
  }

  // 1) Delete items first
  if (itemIds.length) {
    await Item.deleteDocuments(itemIds);
  }

  // 2) Optionally delete folders (bottom-up)
  if (deleteFolders && folderIdsOrdered.length) {
    await Folder.deleteDocuments(folderIdsOrdered);
  }

  ui.notifications?.info(
    `Deleted ${itemIds.length} item(s)` +
    (deleteFolders ? ` and ${folderIdsOrdered.length} folder(s)` : "") +
    ` from ${summary.root}.`
  );
})();