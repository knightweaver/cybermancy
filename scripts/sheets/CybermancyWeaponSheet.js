export class CybermancyWeaponSheet extends ItemSheet {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      classes: ["cybermancy", "sheet", "item", "weapon"],
      template: "modules/cybermancy/templates/item-weapon-sheet.hbs",
      width: 560,
      height: 520,
      tabs: [{ navSelector: ".tabs", contentSelector: ".sheet-body", initial: "details" }]
    });
  }

  getData(options) {
    const data = super.getData(options);
    const f = this.item.getFlag("cybermancy", "weapon") || {};
    data.flagsCyber = {
      smartlink: !!f.smartlink,
      burst: !!f.burst,
      cybergrade: f.cybergrade ?? "none"
    };
    return data;
  }

  activateListeners(html) {
    super.activateListeners(html);
    if (!this.isEditable) return;

    html.find("[data-action='toggle-smartlink']").on("change", ev => {
      const smartlink = ev.currentTarget.checked;
      this.item.setFlag("cybermancy", "weapon.smartlink", smartlink);
    });

    html.find("[data-action='toggle-burst']").on("change", ev => {
      const burst = ev.currentTarget.checked;
      this.item.setFlag("cybermancy", "weapon.burst", burst);
    });

    html.find("[name='flags.cybermancy.weapon.cybergrade']").on("change", ev => {
      const val = ev.currentTarget.value;
      this.item.setFlag("cybermancy", "weapon.cybergrade", val);
    });

    html.find("[data-action='roll-attack']").on("click", _ => this._rollAttack());
  }

  async _rollAttack() {
    const actor = this.item.parent;
    if (!actor) return ui.notifications.warn("No owning actor for this item.");

    const flags = this.item.getFlag("cybermancy", "weapon") || {};
    const smartlink = !!flags.smartlink && game.settings.get("cybermancy", "enableSmartlink");

    const agi = foundry.utils.getProperty(actor, "system.abilities.agi.mod") ?? 0;
    const prof = foundry.utils.getProperty(actor, "system.proficiency.attack") ?? 0;

    const formula = `1d20 + ${agi} + ${prof}`;
    const roll = await new Roll(formula).roll({async: true});
    roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor }),
      flavor: `Attack with ${this.item.name}${smartlink ? " (Smartlink +1 Edge)" : ""}`
    });

    if (smartlink) {
      const current = actor.getFlag("cybermancy", "edge") ?? 0;
      await actor.setFlag("cybermancy", "edge", current + 1);
    }
  }
}
