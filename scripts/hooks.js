const EDGE_FLAG_SCOPE = "cybermancy";
const EDGE_FLAG_KEY = "edge";

export function getCybermancyEdge(actor) {
  return actor?.getFlag?.(EDGE_FLAG_SCOPE, EDGE_FLAG_KEY) ?? 0;
}

export async function spendCybermancyEdge(actor) {
  const current = getCybermancyEdge(actor);
  if (current <= 0) return false;

  await actor.setFlag(EDGE_FLAG_SCOPE, EDGE_FLAG_KEY, current - 1);
  await ChatMessage.create({ content: `<b>${actor.name}</b> spends 1 Edge.` });
  return true;
}

export function registerCybermancyHooks() {
  // Foundry 13+ ApplicationV2 document context menus use the
  // get{DocumentName}ContextOptions hook family. Chat-message callbacks receive
  // HTMLElement entries rather than the legacy jQuery wrapper.
  Hooks.on("getChatMessageContextOptions", (_application, options) => {
    options.push({
      name: "Spend 1 Edge",
      icon: '<i class="fas fa-bolt"></i>',
      condition: () => !!game.user.character,
      callback: async _element => {
        const actor = game.user.character;
        const spent = await spendCybermancyEdge(actor);
        if (!spent) ui.notifications.warn("No Edge to spend.");
      }
    });
  });
}
