

# Cybermancy: A Daggerheart Conversion for a Shadowrun / Cyberpunk World

This repository presents a homebrew adaptation of the Daggerheart role-playing system for Cyberpunk 2020 and Shadowrun-inspired storytelling. The project began as an experiment in system design, but Daggerheart’s release aligned with many of the mechanics under consideration. Rather than building a full system from scratch, the work here focuses on extending Daggerheart’s core principles—duality dice, narrative-driven resolution, and lightweight mechanics—into a high-tech, high-tension setting shaped by netrunning, biotech, chrome, and corporate intrigue.

## Project Structure

This repository was built around 4 key inputs: 

**Daggerheart** — the underlying rules engine and narrative framework (which is AMAZING and WONDERFUL!).

**Foundry VTT** — the digital platform used to organize, package, and run the system (which is also AMAZING and WONDERFUL!)

**Python toolchain** — a set of scripts for transforming source data (CSV/JSON) into Foundry-ready content.

**GitHub** — version control, documentation, and project organization.

The Python scripts support rapid iteration by allowing items, domains, equipment, cybernetics, and other game data to be captured in structured CSV files. Each file is compiled into minimal, schema-clean JSON objects that Foundry can load without additional hand-editing. The toolchain also includes utilities for batch image generation through the OpenAI API, enabling consistent art production for the system’s components.

Player-facing and GM-facing documentation is separated for ease of reference; both sections are linked throughout the repository.

[Player-facing docs](https://knightweaver.github.io/cybermancy/player)

[GM-facing docs](https://knightweaver.github.io/cybermancy/gm)

## Cybermancy Foundry Compendium

A draft Cybermancy compendium is available at this module URL:

Just drop that into the "Add Modules" and the current draft of Cybermancy should load for you

## Manual chances necessary in Foundry VTT's Daggerheart system from founderyborne

Because Cybermancy include 3 new Domains (and because I don't know a better way yet to do this), for the Cybermancy module to work in Daggerheart in Foundry VTT requires 2 manual changes to the Daggerheart system files.  They are both very minor changes and the instructions are here: [Daggerheart Module edits](./daggerheart-mods/daggerheart-mods.md)

*** If a foundryborne developer reads this or any developer that can guide me on a better / more correct way to do this, I'd love to hear from you.  There are other tweaks to the Daggerheart system as implemented in Foundry VTT that I'd love to make, but I am more of a hacker than an actual developer!  ***

## Rule Additions and System Expansions

Cybermancy preserves the narrative emphasis and duality dice mechanics of Daggerheart, while introducing several new subsystems tailored to cyberpunk storytelling.

### [Item Loadouts](https://knightweaver.github.io/cybermancy/player/rules/item-loadout/)

Inspired by *Blades in the Dark*, the loadout system allows players to begin a session without specifying their full inventory in advance. Instead, characters reveal equipment during play, constrained by their chosen loadout. This maintains narrative plausibility—certain gear simply cannot be concealed in a formal event—while accelerating the start of each session.

### [Bennies](https://knightweaver.github.io/cybermancy/player/rules/bennies/)

Drawing from *Savage Worlds*, Cybermancy adopts a lightweight version of Bennies: a table-driven resource awarded for roleplaying, humor, creativity, and memorable character moments. Bennies increase player agency, but the system assumes that narrative tension—not encounter balance—is the primary driver of difficulty. As always, the world provides larger threats when needed.

### [Flashbacks](https://knightweaver.github.io/cybermancy/player/rules/flashbacks/)

Flashbacks enable retroactive preparation, again inspired by *Blades in the Dark*. Characters may reveal prior planning—bribing a guard, hiding a weapon, forging credentials—without halting the current scene. This keeps the story focused on the action while preserving the importance of non-combat expertise.

### [Driving and Chase Clocks](https://knightweaver.github.io/cybermancy/player/rules/driving-and-chase/)

Cybermancy expands Daggerheart’s countdown clocks into a structured chase mechanic. By combining clocks with environmental effects, chases become dynamic sequences shaped by hazards, shifting terrain, and tactical decision-making.

### Critical Fumbles

Daggerheart does not include critical failures, but Cybermancy introduces an optional rule: matching duality dice with a total result below 10 count as a critical fumble. While failure is not inherently enjoyable, the consequences of a dramatic misstep often create memorable and improvisational storytelling opportunities.

### [Netrunning](https://knightweaver.github.io/cybermancy/player/rules/driving-and-chase/)

Cybermancy includes a custom netrunning subsystem designed to stay consistent with Daggerheart’s narrative philosophy. Netrunning is fast, descriptive, and directly connected to the physical scene. Actions in the digital layer influence the meat-space environment, and vice versa. These rules are still in active playtesting, and community experimentation is welcome.

## Contributing

Feedback, contributions, and playtest reports are encouraged. If you are interested in participating, please reach out to weaver.knight@gmail.com or submit an issue or pull request. Upcoming work will focus on expanding environments, refining netrunning interactions, and completing additional Foundry automation.

---
