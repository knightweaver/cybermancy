/**
 * Delete Items or Actors (and Folders) — Foundry VTT (v10+)
 * - Delete World Items, Item Folders
 * - Delete from Item Compendiums
 * - NEW: Delete World Actors, Actor Folders
 * - Dry run support
 */

(async () => {
  const ROOT = "__ROOT__";

  const isItemFolder = f => f.type === "Item";
  const isActorFolder = f => f.type === "Actor";

  const itemFolders = game.folders.filter(isItemFolder);
  const actorFolders = game.folders.filter(isActorFolder);

  // Gather Item compendium packs
  const itemPacks = Array.from(game.packs).filter(p =>
    (p.documentName ?? p?.metadata?.type) === "Item"
  );

  // UI early-exit check
  if (!itemFolders.length && !actorFolders.length &&
      game.items.size === 0 && game.actors.size === 0 &&
      itemPacks.length === 0) {
    ui.notifications?.warn("No world Items, world Actors, or Item packs found.");
    return;
  }

  // Build folder <select> helper
  const makeFolderSelect = (folders, label) => {
    const options = [`<option value="${ROOT}">— ${label} (root) —</option>`]
      .concat(
        folders
          .slice()
          .sort((a,b)=>a.name.localeCompare(b.name))
          .map(f => `<option value="${f.id}">${f.name}</option>`)
      ).join("");
    return options;
  };

  const itemFolderOptions = makeFolderSelect(itemFolders, "Items");
  const actorFolderOptions = makeFolderSelect(actorFolders, "Actors");

  const packOptions = itemPacks
    .slice()
    .sort((a,b)=>a.title.localeCompare(b.title))
    .map(p => `<option value="${p.collection}">${p.title} (${p.collection})</option>`)
    .join("");

  // --- Dialog ---
  const html = await new Promise(resolve => {
    new Dialog({
      title: "Delete Documents",
      content: `
        <form>
          <fieldset style="margin-bottom: 8px;">
            <legend>Delete From</legend>
            <label><input type="radio" name="scope" value="world-items" checked> World Items</label>
            <label style="margin-left: 1em;"><input type="radio" name="scope" value="pack" ${itemPacks.length ? "" : "disabled"}> Item Compendium</label>
            <label style="margin-left: 1em;"><input type="radio" name="scope" value="world-actors"> World Actors</label>
          </fieldset>

          <div class="form-group">
            <label>World Item Root</label>
            <select name="itemRoot">${itemFolderOptions}</select>
          </div>

          <div class="form-group">
            <label>World Actor Root</label>
            <select name="actorRoot">${actorFolderOptions}</select>
          </div>

          <div class="form-group">
            <label>Compendium Pack (Items)</label>
            <select name="pack" ${itemPacks.length ? "" : "disabled"}>${packOptions || "<option>(none)</option>"}</select>
          </div>

          <div class="form-group">
            <label><input type="checkbox" name="recurse" checked> Include subfolders</label>
          </div>

          <div class="form-group">
            <label><input type="checkbox" name="deleteFolders"> Also delete folders</label>
          </div>

          <hr>

          <div class="form-group">
            <label><input type="checkbox" name="dryRun" checked> Dry run (report only)</label>
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

  const scope = html.find('input[name="scope"]:checked').val();
  const recurse = html.find('input[name="recurse"]')[0].checked;
  const deleteFolders = html.find('input[name="deleteFolders"]')[0].checked;
  const dryRun = html.find('input[name="dryRun"]')[0].checked;

  // Utility: post-order traversal
  const buildByParent = (folders) => {
    const map = new Map();
    for (const f of folders) {
      const pid = f.parent?.id ?? null;
      if (!map.has(pid)) map.set(pid, []);
      map.get(pid).push(f);
    }
    return map;
  };

  const postOrder = (root, byParent) => {
    const out = [];
    (function dfs(f) {
      for (const c of (byParent.get(f.id) ?? [])) dfs(c);
      out.push(f);
    })(root);
    return out;
  };

  // ============================================================
  // === PACK DELETE (Items only)
  // ============================================================
  if (scope === "pack") {
    const packKey = html.find('select[name="pack"]').val();
    const pack = game.packs.get(packKey);
    if (!pack) return ui.notifications.error("Pack not found.");
    if (pack.locked) return ui.notifications.error(`Pack "${pack.title}" is locked.`);

    const docs = await pack.getDocuments();
    const ids = docs.map(d => d.id);
    const summary = `Pack "${pack.title}": ${ids.length} item(s)`;

    console.log(summary);

    if (dryRun) return ui.notifications.info(`Dry run: would delete ${ids.length} item(s).`);

    if (ids.length)
      await pack.documentClass.deleteDocuments(ids, { pack: pack.collection });

    return ui.notifications.info(`Deleted ${ids.length} item(s) from pack "${pack.title}".`);
  }

  // ============================================================
  // === WORLD ITEMS / WORLD ACTORS SHARED LOGIC
  // ============================================================

  async function runWorldDelete({ isActor }) {
    const rootSelect = isActor ? 'actorRoot' : 'itemRoot';
    const rootId = html.find(`select[name="${rootSelect}"]`).val();

    const docs = isActor ? game.actors : game.items;
    const folders = isActor ? actorFolders : itemFolders;

    const byParent = buildByParent(folders);

    let selectedFolders = [];

    if (rootId === ROOT) {
      if (recurse) {
        const roots = byParent.get(null) ?? [];
        for (const r of roots) selectedFolders.push(...postOrder(r, byParent));
      }
    } else {
      const root = game.folders.get(rootId);
      if (!root) return ui.notifications.error("Folder not found.");
      selectedFolders = recurse ? postOrder(root, byParent) : [root];
    }

    const folderIds = new Set(selectedFolders.map(f => f.id));

    // Collect documents
    let docsToDelete;
    if (rootId === ROOT) {
      docsToDelete = recurse ? Array.from(docs) : docs.filter(d => !d.folder);
    } else {
      docsToDelete = docs.filter(d =>
        d.folder && (d.folder.id === rootId || folderIds.has(d.folder.id))
      );
    }

    const ids = docsToDelete.map(d => d.id);
    const label = isActor ? "actor" : "item";

    console.log(`[Delete ${isActor ? "Actors" : "Items"}]`, {
      count: ids.length,
      folders: folderIds.size
    });

    if (dryRun) {
      ui.notifications.info(
        `Dry run: would delete ${ids.length} ${label}(s)` +
        (deleteFolders ? ` and ${folderIds.size} folder(s)` : "")
      );
      return;
    }

    // Delete docs
    if (ids.length) {
      const cls = isActor ? Actor : Item;
      await cls.deleteDocuments(ids);
    }

    if (deleteFolders && folderIds.size) {
      await Folder.deleteDocuments([...folderIds]);
    }

    ui.notifications.info(
      `Deleted ${ids.length} ${label}(s)` +
      (deleteFolders ? ` and ${folderIds.size} folder(s)` : "")
    );
  }

  // ============================================================
  // === BRANCH: WORLD ITEMS / WORLD ACTORS
  // ============================================================

  if (scope === "world-items") {
    return await runWorldDelete({ isActor: false });
  }

  if (scope === "world-actors") {
    return await runWorldDelete({ isActor: true });
  }

})();