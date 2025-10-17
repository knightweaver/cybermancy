Here’s the plain-English, system-text version of the common weapon Features as they’re written in the  lists (which Foundryborne uses for its compendium entries and automations). I’ve grouped the most frequently seen ones first. I’ll note any automation hints we can infer from Foundryborne’s repo/issues where relevant.

![Foundryborne Action and Features page](https://github.com/Foundryborne/daggerheart/wiki/Actions-%26-Features_)

# Core Weapon combat modifiers

**Reliable** — “+1 to attack rolls.” 

**Heavy** — “–1 to Evasion.” 

**Cumbersome** — “–1 to Finesse.” (Appears on halberd/longbow lines.) Note: Spear was corrected in the SRD to not have Cumbersome. 

**Massive** — “–1 to Evasion; on a successful attack, roll an additional damage die and discard the lowest result.” (So, advantage-style extra die on damage only.) 

**Powerful** — “On a successful attack, roll an additional damage die and discard the lowest result.” (Like Massive’s damage rider, without the Evasion penalty.) 

**Brutal** — “When you roll the maximum value on a damage die, roll an additional damage die.” 

**Quick** — “When you make an attack, you can mark a Stress to target another creature within range.” (Adds a second target at a Stress cost.) 

# Action economy / battlefield control

**Reloading** — “After you make an attack, roll a d6. On a 1, you must mark a Stress to reload this weapon before you can fire it again.” 

**Protective** — Adds a flat bonus to Armor Score (e.g., +1, +2, +4 depending on item). 

**Barrier** — “+X to Armor Score; –1 to Evasion.” (Tower shields scale the bonus by tier.) 

**Paired** — On secondary blades: “+X to primary weapon damage to targets within Melee range” (scales by tier). 

**Returning** — Thrown within range, the weapon appears back in your hand after the attack. 

**Versatile** — Provides an alternate stat/range/damage line you may use instead (exact alt profile is printed per item). 

# Movement / range manipulation

**Hooked** — “On a successful attack, you can pull the target into Melee range.” 

**Startling** — “Mark a Stress to crack the whip and force all adversaries within Melee back to Close range.” 

**Concussive** — “On a successful attack, you can spend a Hope to knock the target back to Far range.” 

**Long** — “This weapon’s attack targets all adversaries in a line within range.” 

**Grappling** — “On a successful attack, you can spend a Hope to Restrain the target or pull them into Melee with you.” 

**Bouncing** — “Mark 1 or more Stress to hit that many targets in range of the attack.” 

# Other notable riders

**Scary** — “On a successful attack, the target must mark a Stress.” 

**Deadly** — “When you deal Severe damage, the target must mark an additional HP.” 

**Dueling** — “When there are no other creatures within Close of the target, gain advantage on your attack roll against them.” 

**Sharpening** — “Gain a bonus to your damage rolls equal to your Agility.” (Feature name varies by item; see Flickerfly Blade.) 

**Devastating** — “Before you make an attack roll, you can mark a Stress to use a d20 as your damage die.” 

**Brave** — “–1 to Evasion; +3 to Severe damage threshold.” 

**Serrated** — “When you roll a 1 on a damage die, it deals 8 damage instead.” 

Where this lives in Foundryborne (and evidence it’s implemented)


# Core Armor combat modifiers

**Flexible** — “+1 to Evasion.”
Foundryborne: passive +1 Evasion when the item is equipped. 


**Heavy** — “−1 to Evasion.”
Foundryborne: passive −1 Evasion on equip. 


**Very Heavy** — “−2 to Evasion; −1 to Agility.”
Foundryborne: passive penalties applied while equipped. 


**Resilient** — Before you’d mark your last Armor Slot, roll d6; on a 6, reduce the severity by one threshold without marking the slot.
Foundryborne: a triggered effect at the “last slot” moment; GMs/players click/roll to resolve. 


**Reinforced** — When you mark your last Armor Slot, increase your damage thresholds by +2 until you clear at least 1 slot.
Foundryborne: stateful buff after last-slot is marked; clear it when you free a slot. 


**Shifting** — When targeted for an attack, you may mark an Armor Slot to give the attack roll disadvantage.
Foundryborne: spend-to-toggle disadvantage on the incoming roll. 


**Quiet** — +2 to rolls to move silently.
Foundryborne: passive situational bonus (GM applies/sets advantage as needed). 


**Hopeful** — When you would spend a Hope, you can mark an Armor Slot instead.
Foundryborne: replacement cost; mark slot instead of spending Hope. 


**Warded** — You reduce incoming magic damage by your Armor Score before applying to thresholds.
Foundryborne: subtract Armor Score from magic damage first, then resolve thresholds. 


**Gilded** — +1 to Presence.
Foundryborne: passive +1 Presence while equipped. 


**Impenetrable** — Once per short rest, when you’d mark your last Hit Point, you can mark a Stress instead.
Foundryborne: 1/short-rest replacement trigger at “last HP” moment. 


**Sharp** — On a successful attack against a target in Melee, add a d4 to the damage roll.
Foundryborne: conditional damage rider (melee only). 


**Physical** — You can’t mark an Armor Slot to reduce magic damage.
Foundryborne: prohibits using slots vs. magic. 


**Magic** — You can’t mark an Armor Slot to reduce physical damage.
Foundryborne: prohibits using slots vs. physical. 


**Painful** — Each time you mark an Armor Slot, you must mark a Stress.
Foundryborne: adds a cost when spending slots. 


**Timeslowing** — Mark an Armor Slot to roll d4 and add to Evasion against an incoming attack.
Foundryborne: reaction: spend slot, roll d4, add to Evasion for that attack. 


**Channeling** — +1 to Spellcast Rolls.
Foundryborne: passive +1 on spellcast checks while equipped. 


**Burning** — When an adversary attacks you in Melee, they mark a Stress.
Foundryborne: reactive penalty to melee attackers. 


**Fortified** — When you mark an Armor Slot, you reduce severity by two thresholds instead of one.
Foundryborne: stronger slot-spend mitigation. 


**Truthseeking** — Armor glows when a creature within Close tells a lie.
Foundryborne: narrative/visual indicator; no roll math. 


**Difficult** — “−1 to all character traits and Evasion.”
Foundryborne: broad passive penalties while equipped.