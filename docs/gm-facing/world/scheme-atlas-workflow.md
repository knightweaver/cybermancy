# Scheme Atlas Data Guide

The Scheme Atlas is a read-only GM view of `docs/gm-facing/assets/schemes/schemes.json`. Changes are requested through the campaign conversation, reviewed in GitHub, and published with the GM docs. The data is canonical; the browser does not save edits or change player awareness.

## Scheme records

Each scheme has a stable identifier, title, owning entity, corporate/strategic layer, scope, objective, plan, consequences, optional projects and canon notes, approval status, awareness, missions, and rumors. Preserve stable IDs when revising titles. Add schemes without changing existing IDs.

`approval` is `approved`, `proposed`, or `retired`. Initial schemes are approved following the October 5, 2026 conversation. No schemes are initially selected for introduction or revealed.

`awareness.selectedForIntroduction` queues a future introduction. `awareness.revealed` records actual PC exposure. `awareness.knowledge` explains exactly what the PCs know; partial exposure does not reveal objectives, sponsors, or hidden affiliations automatically.

Missions and rumors are independent arrays; both support multiple records. Each record has a stable `id`, `title`, `description`, `status`, `revealed` boolean, and optional document `url` (empty when absent). Mission statuses: `draft-hook`, `available`, `active`, `completed`, `failed`, `withdrawn`. Rumor statuses: `draft`, `available`, `retired`. Record truth, provenance, or misleading interpretations in the rumor description; do not silently present rumors as GM facts.

When PCs hear a rumor, mark that rumor revealed, mark the scheme revealed, and update the knowledge note to reflect only the information actually conveyed. A mission may still be unrevealed. Queuing an introduction does not itself reveal a scheme. Initial content includes the 33 drafted corporate mission-entry hooks, no full missions, and no invented rumors.

## Location tags and filtering

The Location selector groups canonical Districts and Regions. A district matches only schemes explicitly tagged to it; a region also includes schemes tagged to its districts. The filter combines with entity, awareness, approval, search, and relationship filters. **Show all related** can temporarily include neighbors outside the chosen location; the status line reports hidden selected relationships.

Each scheme's `locations` array contains IDs from the top-level `locations` registry. Registry records have `id`, `name`, and `type` (`district` or `region`); districts also have a `region` ID. The current catalog follows the Seattle Atlas district/region names, including **The South End** and **Everett Bastion**. Tags record explicit geographic ties in existing scopes, plans, and mission hooks. City-scoped schemes are tied to Seattle. Named places such as Forgetown are covered by their established region, Silicon Wilds, while their original scope remains visible. Tags do not automatically propagate through scheme relationships or imply that a regional scheme concerns every district.

Use **No specific location recorded** for schemes with broad regional scope but no named geographic tie. An empty array means no specific tie has been recorded, not that the scheme lacks geographic consequences. The Details panel displays recorded locations. Request tag revisions through the campaign conversation and include them in the normal data review.

## Relationship direction

| Type | Source → target means | Graph |
| --- | --- | --- |
| directs | Source orchestrates target | Arrow |
| supports | Source advances target | Arrow |
| exploits | Source takes advantage of target | Dashed arrow |
| opposes | Source obstructs target | Blocking bar at target |
| competes | Both contend for a resource or authority | Dashed line, bars at both ends |

Each link has an ID, source, target, type, explanatory note, and a `conditional` boolean. Conditional links describe sought cooperation or hypothetical developments, not established alliances; their titles and panel entries expose the qualification. Graph direction does not imply that one corporation belongs to another's hidden faction.

Distinct relations between the same pair may coexist. Competition is symmetric: store it once. Incoming and outgoing relations appear in the details panel. Filters may hide relations; the status line counts hidden selected relationships and **Show all related** temporarily overrides filters for that neighborhood.

## Entity colors and affiliations

The five Council seats and their corporations share cool entity colors. Aurum Rex and Helios Biotech share warm gold; VAI and Abraxas have distinct warm colors. Independent megacorps use separate neutral palettes. Helion and Helios remain distinct; Vesper's exploitation by Abraxas does not imply Cabal membership. Aurum Rex is Dr. Aurelia Vale, CEO of Helios Biotech.

## Publication and checks

Run `npm run schemes:check` after data edits. It checks identifiers, endpoint validity, duplicate relationships, record fields, exposure consistency, GM-only source paths, and navigation/assets. Run the normal docs staging and GM build before publication. The staged configuration inherits the GM configuration; no Player configuration changes are needed.

The atlas initializes on MkDocs Material instant navigation. Escape clears selection or exits full screen. Nodes and relationships are keyboard accessible; Enter/Space selects a node. Drag the divider beside Details to resize the panel. Focus the divider and use Left to widen or Right to narrow it; Shift changes the step from 10 to 50 pixels, and Home/End select the minimum/maximum width. The graph retains space and reframes the selected neighborhood as the panel changes. The width is retained while browsing the current atlas, including hiding details and entering full screen. On narrow screens the panel stacks below the graph. Full screen, panel width, and panel collapse are view controls only.

For browser regression checks, build both sites, install Playwright as an optional local test dependency (`npm install --no-save --package-lock=false playwright` and `npx playwright install chromium`), then run `npm run schemes:test-browser`. The test serves `_site` on an ephemeral loopback port and checks graph markers, expansion, collision-free neighborhoods, filters, keyboard use, zoom, details, instant navigation, responsive views, and multiple mission/rumor records. Fixture awareness changes are intercepted in memory and never written to canonical data. `SCHEME_ATLAS_PLAYWRIGHT` and `SCHEME_ATLAS_BROWSER` can select an existing Playwright module and Chromium executable.
