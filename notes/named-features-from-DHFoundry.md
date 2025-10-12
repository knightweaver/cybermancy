Here’s the plain-English, system-text version of the common weapon Features as they’re written in the  lists (which Foundryborne uses for its compendium entries and automations). I’ve grouped the most frequently seen ones first. I’ll note any automation hints we can infer from Foundryborne’s repo/issues where relevant.

![Foundryborne Action and Features page](https://github.com/Foundryborne/daggerheart/wiki/Actions-%26-Features_)

# Core combat modifiers

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

Foundryborne’s Wiki → Actions & Features explains that items carry Features and that Features can include Actions (attack, damage, healing, generic, macro) and Effects that apply passively—this is the layer where these SRD features are enacted in-system. 
GitHub

The Massive behavior shows up in bug reports about the “Massive weapon keyword” interacting with custom damage formulas—evidence it’s implemented as a keyword that alters damage rolling (extra die, drop lowest). 
GitHub

The Spear “Cumbersome” correction appears in both community discussions and a Foundryborne issue adjusting compendium data, confirming the expected SRD semantics (Spear should not be Cumbersome). 
GitHub
+1