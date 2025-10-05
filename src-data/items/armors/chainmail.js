{
  "name": "Chainmail Armor",
  "type": "armor",
  "img": "icons/equipment/chest/breastplate-scale-grey.webp",
  "system": {
    "description": "",
    "actions": {},
    "attached": [],
    "tier": 1,
    "equipped": false,
    "baseScore": 4,
    "armorFeatures": [
      { "value": "heavy", "effectIds": [], "actionIds": [] }
    ],
    "marks": { "value": 0 },
    "baseThresholds": { "major": 7, "severe": 15 }
  },
  "effects": [
    {
      "name": "Heavy",
      "description": "-1 to Evasion",
      "img": "icons/commodities/metal/ingot-worn-iron.webp",
      "type": "base",
      "system": {},
      "disabled": false,
      "duration": { "startTime": null, "combat": null },
      "origin": null,
      "tint": "#ffffff",
      "transfer": true,
      "statuses": [],
      "changes": [
        { "key": "system.evasion", "mode": 2, "value": "-1" }
      ],
      "sort": 0,
      "flags": {}
    }
  ]
}
