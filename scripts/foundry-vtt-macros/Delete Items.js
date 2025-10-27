// Delete selected world Items with a checkbox picker (GM only).
// Shows all Items in the world (not compendia). Uncheck any to keep.

(async () => {
  if (!game.user.isGM) return ui.notifications.warn("GM only.");

  const items = game.items.contents.sort((a,b)=> a.name.localeCompare(b.name));
  if (!items.length) return ui.notifications.info("No world Items found.");

  const list = items.map(i => `
    <label style="display:flex;gap:.5rem;align-items:center;padding:.15rem 0;">
      <input type="checkbox" name="del" value="${i.id}" checked>
      <span style="flex:1">${foundry.utils.escapeHTML(i.name)}</span>
      <small style="opacity:.7">(${i.type})</small>
    </label>
  `).join("");

  const content = `
    <form>
      <p><strong>${items.length}</strong> Items in world. Uncheck any to keep.</p>
      <div style="display:flex;gap:1rem;align-items:center;margin:.25rem 0 .5rem;">
        <label><input type="checkbox" id="chkAll" checked> Select all</label>
        <input type="text" id="search" placeholder="Filter by name…" style="flex:1">
      </div>
      <div id="list" style="max-height:420px;overflow:auto;border:1px solid var(--color-border-light-1);padding:.5rem;">
        ${list}
      </div>
    </form>
  `;

  const dlg = new Dialog({
    title: "Delete World Items",
    content,
    buttons: {
      delete: {
        icon: '<i class="fas fa-trash"></i>',
        label: "Delete selected",
        callback: async (html) => {
          const ids = Array.from(html[0].querySelectorAll('input[name="del"]:checked')).map(el => el.value);
          if (!ids.length) return ui.notifications.info("Nothing selected.");
          const confirmed = await Dialog.confirm({
            title: "Confirm Deletion",
            content: `<p>Delete <strong>${ids.length}</strong> selected Item(s)? This cannot be undone.</p>`
          });
          if (!confirmed) return;
          // Bulk delete
          await Item.deleteDocuments(ids);
          ui.notifications.info(`Deleted ${ids.length} Item(s).`);
        }
      },
      cancel: { label: "Cancel" }
    },
    render: (html) => {
      const root = html[0];
      const chkAll = root.querySelector("#chkAll");
      const listEl = root.querySelector("#list");
      const search = root.querySelector("#search");

      chkAll?.addEventListener("change", () => {
        const boxes = listEl.querySelectorAll('input[name="del"]');
        boxes.forEach(cb => { cb.checked = chkAll.checked; });
      });

      search?.addEventListener("input", () => {
        const q = search.value.trim().toLowerCase();
        for (const row of listEl.querySelectorAll("label")) {
          const name = row.querySelector("span")?.textContent?.toLowerCase() ?? "";
          row.style.display = name.includes(q) ? "" : "none";
        }
      });
    },
    default: "delete"
  }, { width: 520 });

  dlg.render(true);
})();