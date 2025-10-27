/**
 * Delete Items (and Folders) Macro for Foundry VTT (v10+)
 * - Now supports selecting the Items ROOT to delete all items (and folders) in one run.
 * - Choose root (Items root or a specific Item Folder), recurse, and optionally delete folders.
 * - Dry run option reports counts only.
 */

(async () => {
  const isItemFolder = f => f.type === "Item";
  const allFolders = game.folders.filter(isItemFolder);
  const ROOT = "__ROOT__";

  if (!allFolders.length && game.items.size === 0) {
    ui.notifications?.warn("No Items or Item folders found.");
    return;
  }

  // Build <select> including ROOT
  const folderOptions = [`<option value="${ROOT}">— Items (root) —</option>`]
    .concat(
      allFolders
        .slice()
        .sort((a,b)=>a.name.localeCompare(b.name))
        .map(f => `<option value="${f.id}">${f.name}</option>`)
    ).join("");

  const html = await new Promise(resolve => {
    new Dialog({
      title: "Delete Items (and Folders)",
      content: `
        <form>
          <div class="form-group">
            <label>Root</label>
            <select name="root">${folderOptions}</select>
          </div>
          <div class="form-group">
            <label class="checkbox"><input type="checkbox" name="recurse" checked>
              Include subfolders (if ROOT, this means *all* Item folders)
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox"><input type="checkbox" name="deleteFolders">
              Also delete folder(s) after items are removed
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

  const rootId = html.find('select[name="root"]').val();
  const recurse = html.find('input[name="recurse"]')[0].checked;
  const deleteFolders = html.find('input[name="deleteFolders"]')[0].checked;
  const dryRun = html.find('input[name="dryRun"]')[0].checked;

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
      // All folders in post-order starting from all top-level roots
      const roots = byParent.get(null) ?? [];
      const out = [];
      for (const top of roots) out.push(...postOrderFrom(top));
      foldersOrdered = out;
    } else {
      // No folders if not recursing from ROOT
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
    if (recurse) {
      // All items (in any folder + root)
      itemsToDelete = Array.from(game.items);
    } else {
      // Only items directly in root (no folder)
      itemsToDelete = game.items.filter(it => !it.folder);
    }
  } else {
    // Items under selected folder(s)
    itemsToDelete = game.items.filter(it => {
      const fid = it.folder?.id ?? null;
      return fid && (fid === rootId || folderIdSet.has(fid));
    });
  }

  const itemIds = itemsToDelete.map(i => i.id);
  const summary = {
    root: (rootId === ROOT ? "Items (root)" : (game.folders.get(rootId)?.name ?? "(missing)")),
    recurse,
    items: itemIds.length,
    foldersSelected: folderIdsOrdered.length,
    willDeleteFolders: deleteFolders
  };

  console.log("[Delete Items & Folders] Summary", summary);

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