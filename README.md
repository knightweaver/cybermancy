

# Cybermancy: A Daggerheart Conversion for a Shadowrun / Cyberpunk World

This repository presents a homebrew adaptation of the Daggerheart role-playing system for Cyberpunk 2020 and Shadowrun-inspired storytelling. I started working on this project because I had some ideas for role gamng design I wanted to try, but then Daggerheart was released and was quite close to many of the ideas I was ruminating on. Rather than building a full system from scratch, I pivoted to extending Daggerheart’s core principles—duality dice, narrative-driven resolution, and lightweight mechanics—into a high-tech, high-tension setting shaped by magic, netrunning, high-tech, chrome, and corporate intrigue.

## Project Structure

This project (and the resulting Github repo) was built from 4 key inputs: 

**Daggerheart** — the underlying rules engine and narrative framework (which is AMAZING and WONDERFUL!).

**Foundry VTT** — the digital platform used to organize, package, and run the system (which is also AMAZING and WONDERFUL!)

**Python tooling** — a set of scripts for transforming source data (CSV/JSON) into Foundry-ready content.

**GitHub** — for version control, documentation delivery to my group, and project organization.

The Python scripts were built to allow me to ideate for new items, domain, and classes in and Excel file, then convert the rows into minimal JSON files that Foundry can load without additional hand-editing (mostly). The python script also includes utilities for batch image generation through the OpenAI API, enabling consistent art production for the system’s components.

Player-facing and GM-facing pages are here: 

[Player-facing docs](https://knightweaver.github.io/cybermancy/player)

[GM-facing docs](https://knightweaver.github.io/cybermancy/gm)

## Cybermancy Foundry Compendium

A draft Cybermancy compendium for Foundry VTT is available at this module URL:

`https://github.com/knightweaver/cybermancy/releases/latest/download/module.json`

Just drop that into the "Add Modules" and the current draft of Cybermancy should load for you.

## Manual changes necessary in Foundry VTT's Daggerheart system from founderyborne

Because Cybermancy include 3 new Domains (and because I don't know a better way yet to do this), for the Cybermancy module to work in Foundry VTT requires 2 manual changes to the Daggerheart system files.  They are both very minor changes and the instructions are here: [Daggerheart Module edits](./daggerheart-mods/daggerheart-mods.md)

***If a foundryborne developer reads this or any developer that can guide me on a better / more correct way to do this, I'd love to hear from you.  There are other tweaks to the Daggerheart system as implemented in Foundry VTT that I'd love to make, but I am more of a hacker than an actual developer!***

## Rule Additions and System Expansions

Cybermancy preserves the narrative emphasis and duality dice mechanics of Daggerheart, while introducing some new rules tailored to cyberpunk storytelling.

### [Item Loadouts](https://knightweaver.github.io/cybermancy/player/rules/item-loadout/)

Inspired by *Blades in the Dark*, the Item Loadout rule allows players to begin a session without specifying their full inventory in advance. Instead, characters reveal equipment during play, constrained by their chosen loadout. This maintains narrative plausibility ("no, the rocket launcher cannot be hidden in your tuxedo jacket pocket") while making it faster for players to jump into the story.

### [Bennies](https://knightweaver.github.io/cybermancy/player/rules/bennies/)

Drawing from *Savage Worlds*, Cybermancy adopts a lightweight version of "Bennies": a player who deliver's an memorable moment of roleplaying, humor, or creativity is rewarded with a "Bennie" (we use poker chips). Bennies work a bit like inspiration in D&D 5e, but are handed out more frequently and give small bonuses.  

### [Flashbacks](https://knightweaver.github.io/cybermancy/player/rules/flashbacks/)

Flashbacks enable retroactive preparation, again inspired by *Blades in the Dark*. Characters may reveal prior planning — bribing a guard, obtaining the plans to a building, forging credentials — without halting the current scene. This keeps the group focused on the story while preserving the importance of non-combat expertise and events.

### [Driving and Chase Clocks](https://knightweaver.github.io/cybermancy/player/rules/driving-and-chases/)

Cybermancy expands the concept of a Chase Countdown in Daggerheart (pg. 163) a bit to handle the concept of driving, passengers, and chase Environments. By combining clocks with environmental effects, chases become dynamic sequences shaped by hazards, shifting terrain, and tactical decision-making, without bogging the chase down with a bunch of bookkeeping.

### Critical Fumbles

Daggerheart does not include critical failures, but Cybermancy introduces an optional rule: matching duality dice with a total result below 10 count as a critical fumble. While failure is not inherently enjoyable, the consequences of a dramatic misstep often create memorable and improvisational storytelling opportunities.  My observation from years of GMing, is that the group vividly remembers the scene where something went badly wrong and how they recovered more than they remember when everything went smoothly.

### Added effect of Marking an Armor Slot

I really like the concept of damage thresholds and Armor slots in Daggerheart, gut one aspect of that design that I dislike is how an Armor Slot is almost functionally equivalent to a hit point.  Cybermancy tweaks the rules such that when you mark an Armor Slot to prevent hit point damage, it has the additional effect of applying a -1/-1 to the Major and Severe damage thresholds.  The concept is that the armor has been slightly damaged by the hit it absorbed and thus provides a bit less protection until repaired.  I like this because it adds additional meaning to the decision about whether to mark an Armor Slot or a hit point, without leading to a "death spiral".

### [Netrunning](https://knightweaver.github.io/cybermancy/player/rules/netrunner-hacking/)

Cybermancy includes a custom netrunning subsystem designed to stay consistent with Daggerheart’s narrative philosophy. Netrunning is fast, descriptive, and directly connected to the physical scene. Actions in the digital layer influence the meat-space environment, and vice versa. These rules are still in active playtesting, and I'd love feedback from outside our gaming group.

## Contributing

Feedback, contributions, and playtest reports are encouraged. If you are interested in participating, please reach out to weaver.knight@gmail.com or submit an issue or pull request. Upcoming work will focus on expanding environments, refining netrunning interactions, and completing additional Foundry automation.

---

## Thanks!

I want to extend a thank you to all the authors of all the gaming systems that inspired Cybermancy.

 - *Savage Worlds*
 - *Blades in the Dark*
 - *D&D*

And most importantly **Daggerheart**!

We truly live in the golden age of gaming.