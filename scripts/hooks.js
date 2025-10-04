export function registerCybermancyHooks() {
  Hooks.on("getChatLogEntryContext", (html, options) => {
    options.push({
      name: "Spend 1 Edge",
      icon: '<i class="fas fa-bolt"></i>',
      condition: li => !!game.user.character,
      callback: async li => {
        const actor = game.user.character;
        const curr = actor.getFlag("cybermancy", "edge") ?? 0;
        if (curr <= 0) return ui.notifications.warn("No Edge to spend.");
        await actor.setFlag("cybermancy", "edge", curr - 1);
        ChatMessage.create({ content: `<b>${actor.name}</b> spends 1 Edge.` });
      }
    });
  });
}
