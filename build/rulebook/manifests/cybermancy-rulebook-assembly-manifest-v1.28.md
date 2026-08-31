# Cybermancy Rulebook Assembly Manifest v1.28

**Status:** NORMATIVE  
**Step:** Rulebook Step 3 — Book Information Architecture  
**Parent authority:** `cybermancy-rulebook-publication-manifest-v1.28.json`  
**Frozen repository commit:** `db893e26bf3791ed5f716a19ab80aa420e179c03`  
**Supersedes:** `cybermancy-rulebook-assembly-manifest-v1.27.json`

## 1. Rebuild result

This manifest consumes the frozen Step 2 publication manifest and applies the
approved Step 3 information architecture.

Hard invariants:

- **33 INCLUDE rows**
- **18 authored publication inputs**
- **15 structured publication families**
- **1084 logical structured entities**
- generated MkDocs collection/detail output remains **DERIVATIVE / EXCLUDE**
- canonical structured publication content comes directly from `src/packs/...`
- full Markdown/HTML/Jinja normalization remains deferred to Step 4

The hand-authored player and GM landing pages are canonical publication inputs.
The player landing page supplies the Welcome material. The GM landing page is
placed as GM-only front matter after the spoiler divider and before Chapter 23.

`docs/gm-facing/world/the-alternate-chessboard.md` is explicitly excluded from
assembly. Campaign/adventure actor aggregation such as
`docs/gm-facing/adventures/npc-actors.md` remains outside reusable rulebook
authority.

## 2. Book architecture

### The World of Cybermancy
- **1. Welcome to Cybermancy** — `auth.welcome`
- **2. The Resonance Cascade** — `auth.resonance`
- **3. Megacorporations** — `auth.corps`

### Cybermancy Rules
- **4. Cybermancy Frame Rules** — `auth.frame-rules`
- **5. Item Loadouts** — `auth.loadouts`
- **6. Flashbacks** — `auth.flashbacks`
- **7. Bennies** — `auth.bennies`
- **8. Driving and Chases** — `auth.driving`
- **9. Netrunning and Device Intrusion** — `auth.netrunning`

### Characters and Character Options
- **10. Ancestories** — `auth.ancestories`
- **11. Communities** — `auth.communities`
- **12. Classes and Subclasses** — `family:classes`, `family:subclasses`
- **14. Domains and Domain Cards** — `family:domains`

### Equipment and Technology
- **15. Weapons** — `family:weapons`
- **16. Ammunition** — `family:ammo`
- **17. Armor** — `family:armors`
- **18. Cybernetics** — `family:cybernetics`
- **19. Drones and Devices** — `family:drones-devices`
- **20. Consumables** — `family:consumables`
- **21. Mods** — `family:mods`
- **22. Loot** — `family:loot`

### GM World Guide **[GM ONLY]**
- **Section opener:** `auth.gm-guide-index`
- **23. Project Helios and the Hidden History** — `auth.project-helios`
- **24. The Council** — `auth.council`
- **25. The Cabal** — `auth.cabal`
- **26. Cabal Projects** — `auth.cabal-projects`
- **27. The Chessboard** — `auth.chessboard`
- **28. The Resonance: GM Interpretation** — `auth.gm-resonance`

### GM Encounter Toolkit **[GM ONLY]**
- **29. ICE Reference** — `family:features`
- **30. Adversaries** — `family:adversaries`
- **31. Environments** — `family:environments`
- **32. Adversary Feature Reference** — `family:adversaries-features`


The complete book inserts **GM MATERIAL — SPOILERS BEYOND THIS POINT** before
Part V. A player-guide build omits the divider, GM opener, Parts V–VI, and all
GM-only structured collections.

## 3. Authored input mapping

| Step 2 ID | Source | Audience | Placement | Book role/title | Assembly mode |
|---|---|---|---|---|---|
| A032 | `docs/player-facing/index.md` | player | ch01-welcome | Cybermancy Player Introduction | segment |
| A004 | `docs/_shared/world/the-resonance.md` | shared | ch02-resonance | The Event: The Resonance Cascade | whole-document |
| A054 | `docs/player-facing/world/corps.md` | player | ch03-megacorporations | Megacorporations | whole-document |
| A045 | `docs/player-facing/rules/index.md` | player | ch04-frame-rules | Cybermancy Frame Rules | segment |
| A046 | `docs/player-facing/rules/item-loadout.md` | player | ch05-item-loadouts | Item Loadouts | whole-document |
| A044 | `docs/player-facing/rules/flashbacks.md` | player | ch06-flashbacks | Flashbacks | whole-document |
| A042 | `docs/player-facing/rules/bennies.md` | player | ch07-bennies | Bennies | whole-document |
| A043 | `docs/player-facing/rules/driving-and-chases.md` | player | ch08-driving-chases | Driving and Chases | whole-document |
| A047 | `docs/player-facing/rules/netrunner-hacking.md` | player | ch09-netrunning | Netrunning and Device Intrusion | whole-document |
| A052 | `docs/player-facing/world/ancestories.md` | player | ch10-ancestories | Ancestories | whole-document |
| A053 | `docs/player-facing/world/communities.md` | player | ch11-communities | Communities | whole-document |
| A015 | `docs/gm-facing/index.md` | gm | gm-front-matter | Cybermancy — GM Guide | whole-document |
| A019 | `docs/gm-facing/world/project-helios-remnants.md` | gm | ch23-project-helios | Project Helios and the Hidden History | whole-document |
| A025 | `docs/gm-facing/world/the-council.md` | gm | ch24-council | The Council | whole-document |
| A022 | `docs/gm-facing/world/the-cabal.md` | gm | ch25-cabal | The Cabal | whole-document |
| A021 | `docs/gm-facing/world/the-cabal-projects.md` | gm | ch26-cabal-projects | Cabal Projects | whole-document |
| A023 | `docs/gm-facing/world/the-chessboard.md` | gm | ch27-chessboard | The Chessboard | whole-document |
| A026 | `docs/gm-facing/world/timeline.md` | gm | ch28-gm-resonance | The Resonance: GM Interpretation | segment |

### Structural deduplication

Three sources use assembly-level segmentation without rewriting their source:

1. `docs/player-facing/index.md` supplies **Welcome to Cybermancy** but does not
   duplicate the Resonance section owned by `docs/_shared/world/the-resonance.md`.
2. `docs/player-facing/rules/index.md` supplies the Frame Rules lead plus unique
   Critical Fail / Armor Slot material, while dedicated rule files own their
   complete rule sections.
3. `docs/gm-facing/world/timeline.md` supplies its unique GM interpretation and
   tone sections but does not duplicate the shared Resonance text it transcludes.

The GM landing page is mapped whole as the GM section opener. Any editorial
cleanup of navigation/development phrasing is deferred to Step 4.

## 4. Structured-family mapping

| Step 2 ID | Family | Canonical source | Entities | Audience | Placement |
|---|---|---|---:|---|---|
| B001 | `adversaries` | `src/packs/adventures/adversaries` | 107 | gm | ch30-adversaries |
| B002 | `adversaries-features` | `src/packs/system/adversaries-features` | 419 | gm | ch32-adversary-features |
| B004 | `ammo` | `src/packs/items/ammo` | 13 | player | ch16-ammunition |
| B005 | `armors` | `src/packs/items/armors` | 36 | player | ch17-armor |
| B006 | `classes` | `src/packs/system/classes` | 5 | player | ch12-classes |
| B007 | `consumables` | `src/packs/items/consumables` | 59 | player | ch20-consumables |
| B008 | `cybernetics` | `src/packs/items/cybernetics` | 103 | player | ch18-cybernetics |
| B009 | `domains` | `src/packs/system/domains` | 73 | player | ch14-domains |
| B010 | `drones-devices` | `src/packs/items/drones-devices` | 19 | player | ch19-drones-devices |
| B003 | `environments` | `src/packs/adventures/environments` | 8 | gm | ch31-environments |
| B011 | `features` | `src/packs/system/features` | 105 | gm | ch29-ice-reference |
| B012 | `loot` | `src/packs/items/loot` | 60 | player | ch22-loot |
| B013 | `mods` | `src/packs/items/mods` | 20 | player | ch21-mods |
| B014 | `subclasses` | `src/packs/system/subclasses` | 10 | player | ch12-classes |
| B015 | `weapons` | `src/packs/items/weapons` | 47 | player | ch15-weapons |

**Total logical structured entities: 1084.**

Generated book collections consume canonical structured sources directly.
Existing generated MkDocs detail pages and aggregation pages remain excluded as
authority.

For **Adversaries** and **Environments**, `flags.cybermancy.fastPlay` is consumed
structurally and rendered as a dedicated **Fast Play** section rather than
flattened into Description.

## 5. Audience and front-matter routing

- `shared`: safe for all builds.
- `player`: player-safe; included in player and complete builds.
- `gm`: complete build only, after the spoiler divider.
- `developer`: never reader-facing.

Player/shared content must not target GM-only semantic references.

## 6. Cross-reference convention

Semantic targets are:

- `section:<chapter-or-section-id>`
- `family:<family-id>`
- `entity:<family-id>:<stable-source-id>`

Structured entities resolve by family plus stable source/Foundry ID where
available. Page numbers remain render-time products. Existing Markdown/MkDocs
links remain untouched until Step 4 normalization.

## 7. Appendices

- **Appendix A — Cybermancy Rules Quick Reference**
- **Appendix B — Entity Index**
- **Appendix C — Attribution and Publication Notice**

These remain generated/editorial-later and cannot introduce authority outside
the frozen publication inputs.

## 8. Validation

The generated manifest passes the Step 3 structural gate when:

- all 18 authored inputs have exactly one
  primary book/front-matter placement;
- all 15 structured families have
  exactly one primary placement;
- structured-family counts sum to 1084;
- all 33 Step 2 INCLUDE rows are represented;
- the GM boundary is preserved;
- generated MkDocs outputs remain derivative;
- Fast Play structured-source handling is preserved; and
- no full Markdown/HTML normalization is performed.

The JSON file is the normative machine-readable assembly manifest. This
Markdown file is its human-readable companion.
