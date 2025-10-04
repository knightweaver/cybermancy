export class CybermancyRunnerSheet extends ActorSheet {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      classes: ["cybermancy", "sheet", "actor", "runner"],
      template: "modules/cybermancy/templates/actor-runner-sheet.hbs",
      width: 700,
      height: 620,
      tabs: [{ navSelector: ".tabs", contentSelector: ".sheet-body", initial: "stats" }]
    });
  }

  getData(options) {
    const ctx = super.getData(options);
    const baseEdge = foundry.utils.getProperty(this.actor, "system.resources.edge.value") ?? 0;
    const bonus = this._calcCyberwareEdgeBonus();
    ctx.cybermancy = { edgeTotal: baseEdge + bonus, bonus };
    return ctx;
  }

  _calcCyberwareEdgeBonus() {
    const items = this.actor.items.contents || [];
    return items.some(i => i.getFlag("cybermancy", "weapon.smartlink")) ? 1 : 0;
  }
}
