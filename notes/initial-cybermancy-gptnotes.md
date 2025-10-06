# 🧠 Cybermancy Project Index (GPT Notes)

*A Foundry VTT system and world-building project extending Daggerheart into a cyberpunk / Shadowrun-style RPG.*

---

## 🎯 Project Overview

**Goal:**  
Create a modular Foundry VTT extension for *Daggerheart*—the **Cybermancy** system—with features including:

- Custom sheets, item types, and rule extensions (Edge economy, cyberware, netrunning)  
- A comprehensive content compendium (weapons, armor, programs, NPCs)  
- Automated pipelines: JSON → Foundry compendia & JSON → player website  
- Continuous release and update capability via GitHub  

**Primary Repository:**  
[knightweaver/cybermancy](https://github.com/knightweaver/cybermancy)

**Current Version:** `v0.0.4`  
**Foundry Compatibility:** Core v11–13  
**Base System:** Daggerheart (by Foundryborne)

---

## 🗂 Active Workstreams

| Thread | Purpose | ChatGPT Link | Repo / Docs Path |
|---|---|---|---|
| **System Design** | Core mechanics, data models, rules schema | *[Chat link]* | `/system/` |
| **Foundry Code** | JS/TS implementation, custom sheets, roll logic | *[Chat link]* | `/scripts/`, `/templates/` |
| **Content Development** | Weapons, armor, cyberware, NPCs, lore | *[Chat link]* | `/src-data/`, `/packs/` |
| **ETL & Web Export** | JSON → compendia + website generation | *[Chat link]* | `/tools/etl/`, `/web/` |
| **Release Process** | Packaging, versioning, GitHub Actions, manifest updates | *[Chat link]* | `.github/workflows/` |
| **Worldbuilding / Lore** | Factions, setting, NPCs, story arcs | *[Chat link]* | `/docs/lore/` |

> Replace `*[Chat link]*` with the shareable URL of each ChatGPT thread.


---

## 🧮 Build & Packaging Commands

(*Use these in your `package.json` or local scripts for convenience*)

```bash
npm run pack:all      # Build all compendium packs
npm run unpack:all    # Unpack packs back into /src-data for editing
