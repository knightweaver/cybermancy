// Link armorFeatures[].effectIds to embedded effect IDs by name
for (const item of game.items.filter(i => i.type === "armor")) {
  const features = item.system?.armorFeatures ?? [];
  const effects = item.effects?.contents ?? [];

  let changed = false;
  for (const feat of features) {
    if (!Array.isArray(feat.effectIds)) feat.effectIds = [];
    // Example: link "Heavy" feature to effect named "Heavy"
    const eff = effects.find(e => e.name === "Heavy");
    if (eff && !feat.effectIds.includes(eff.id)) {
      feat.effectIds.push(eff.id);
      changed = true;
    }
  }

  if (changed) {
    await item.update({ "system.armorFeatures": features });
    console.log(`Linked effects for: ${item.name}`);
  }
}
