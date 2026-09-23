#!/usr/bin/env python3
"""Build the source-backed Seattle lore-art manifest from atlas GeoJSON."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs" / "gm-facing" / "assets" / "atlas"
PLAYER_ATLAS = ROOT / "docs" / "player-facing" / "assets" / "atlas"
OUTPUT = ROOT / "art-production" / "seattle-lore"
VERSION = "0.1"
MODEL = "gpt-image-2.5-flare"


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()


def text_value(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value if item)
    return str(value or "").strip()


VISUAL_SPECS: dict[str, tuple[str, str]] = {
    "Seattle": ("civic", "A high panoramic view from Puget Sound toward the surviving city: dark water and working ferries in the foreground, a brilliant guarded downtown core, dimmer inhabited districts spreading outward, industrial southern approaches, and Lake Washington visible beyond. Make the contrast between curated corporate prosperity and stubborn neighborhood survival legible without turning the image into a map."),
    "Everett Bastion": ("industrial", "A broad view across a guarded northern port and aerospace manufacturing city: cranes, dry docks, immense weathered assembly halls, fortified logistics yards, and a few maintained aircraft silhouettes beneath cold Sound weather. Convey independent industrial capacity and disciplined defense rather than corporate luxury."),
    "Tacoma": ("civic", "A commanding view over Tacoma's deepwater port and steep urban slopes: container cranes, military logistics, working neighborhoods, harbor patrol craft, and restrained defensive works integrated into civic life. Show a metahuman-led republic sustained by service and trade, not a besieged military camp."),
    "Silicon Wilds": ("frontier", "An Eastside frontier panorama strictly east of Lake Washington: abandoned glass towers overtaken by vegetation, repaired settlements among earthquake ruins, salvage teams, patched utility lines, and half-functioning campus infrastructure. Lake Washington should form the western edge; Mercer Island must not be presented as part of the land territory."),
    "Cascade Approaches": ("uncanny", "A long view eastward where broken metropolitan roads dissolve into forested foothills, defended settlements, collapsed interchanges, and distant Cascade mountains. Add one restrained Resonance anomaly at the edge of perception while keeping the road, weather, ecology, and human defenses physically believable."),
    "Corporate Core": ("corporate", "A precise street-level canyon of maintained towers and luxury arcologies, immaculate public space, discreet security drones, credentialed transit, and small human figures moving under quiet surveillance. Power should read through cleanliness, scale, and restraint rather than excessive signage or ornament."),
    "Queen Anne": ("corporate", "An elevated residential street on a defensible hill, where restored historic houses stand beside boutique arcologies and landscaped executive compounds. Include controlled approaches and a distant view toward the Space Needle, with premium materials and discreet security embedded into an older neighborhood fabric."),
    "Helios Corridor": ("corporate", "A dense biomedical district organized around five research towers and an elevated central platform, with enclosed walkways, restricted laboratory entrances, clinical transit, and quiet corporate security. The campus should feel advanced, functional, and faintly unsettling without revealing hidden campaign truths."),
    "Meridian": ("street", "A busy Lake Washington-facing trade district between I-5 infrastructure and the water: salvage stalls, expedition outfitters, brokers, ferry crews, repaired cargo vehicles, and mixed old-new buildings. Frame the lake and an active terminal in the distance so Meridian reads as Seattle's staging interface with the Eastside frontier."),
    "Old City": ("street", "A layered pre-Razz streetscape at dusk: old masonry buildings, narrow alleys, active legitimate storefronts, stairways descending toward surviving underground markets, and a mixed crowd of workers, traders, and runners. Suggest selective lawlessness through watchful behavior and improvised access control, not universal squalor."),
    "Ballard Reach": ("maritime", "A working maritime district of fisheries, boat repair yards, compact shipyards, moored utility craft, and Currentborn-adapted waterside spaces. Use wet timber, painted industrial steel, nets, cranes, and guarded road access to communicate practical semi-autonomy."),
    "Gasworks": ("industrial", "A lived-in maker district north of the canal: dense small workshops, exterior worktables, repaired machines, public art, apprentices, riggers, and inventors sharing tools. Show productive disorder held together by custom and competence, with the preserved Gas Works structures in the wider skyline."),
    "University Enclave": ("academic", "A recognizable university campus where public student life overlaps with secured research architecture: older brick and concrete halls, modern laboratories, corporate-controlled access points, crowded walkways, and visibly underfunded humanities spaces. Keep the tension institutional and everyday rather than overtly militarized."),
    "The South End": ("civic", "An ordinary working neighborhood sustained by families and local institutions: aging apartments, small businesses, a school, a church, repair crews, buses, and residents using unreliable but functioning infrastructure. Show dignity, cultural variety, and community maintenance without poverty caricature."),
    "Bombshell": ("industrial", "A broad inhabited war-ruin streetscape spanning warehouses, rail infrastructure, homes, churches, mutual-aid repair activity, and shattered exclusion blocks. Functional industry and neighborhood life should exist directly beside unrepaired destruction, with the distant Boeing Field defenses as background context."),
    "West Seattle": ("maritime", "A resilient peninsula neighborhood seen from a guarded approach: civic checkpoints, local markets, modest homes, food gardens, fishing activity, ferry infrastructure, and residents maintaining their own public systems. Emphasize civic autonomy and preparedness rather than isolation or militarism."),
    "Guarded I-5 Corridor": ("industrial", "A convoy moving along a partially repaired interstate through the Puget Sound corridor, passing modular checkpoints, concrete barriers, watch posts, and alternating municipal control zones. The road must remain an active commercial artery rather than a deserted post-apocalyptic highway."),
    "West Seattle Ferry Route": ("maritime", "A practical passenger and light-cargo ferry crossing Elliott Bay in rain, with commuters, crates, bicycles, and a maintained but weathered vessel. Show the central waterfront behind it and West Seattle ahead, emphasizing routine local connection."),
    "Space Needle": ("civic", "A ground-up view of the carefully maintained Space Needle rising above a protected public plaza, with residents, visitors, discreet security, and weathered surrounding city fabric. Preserve its recognizable silhouette while making the scene clearly part of Cybermancy's lived-in future."),
    "Helios Campus": ("corporate", "A closer exterior view of the five-building biomedical campus and its elevated central platform, with enclosed bridges, controlled laboratory doors, staff transit, and restrained perimeter security. Use clinical materials softened by Seattle rain and atmospheric depth."),
    "Boeing Field Fortress": ("industrial", "A hardened aerospace-industrial complex behind layered barriers, repurposed hangars, radar and communications equipment, guarded runways, service aircraft, and heavy maintenance vehicles. Place the fortress within Bombshell's damaged southern infrastructure rather than in an empty battlefield."),
    "The Names We Carry": ("memorial", "A respectful public memorial built around a destroyed armored carrier, stabilized and incorporated into a civic plaza. Show flowers, handmade offerings, metahuman families, veterans, and quiet civil-rights remembrance; avoid depicting the original violence or turning the memorial into military spectacle."),
    "Meridian–Silicon Wilds Ferry Route": ("maritime", "A guarded vehicle ferry crossing Lake Washington between Seattle and the Eastside, carrying expedition teams east and secured salvage cargo west. Seattle's shoreline should be behind the vessel and ruined, overgrown Eastside towers ahead, making the lake boundary unmistakable."),
    "The Seam": ("street", "A twenty-four-hour gray-market bazaar beneath and alongside I-5: layered stalls, salvage parts, expedition gear, food counters, repair benches, fixers, ferry crews, and cautious negotiations under concrete spans. Make it busy and organized by local custom, not a chaotic junk heap."),
    "Madison Ferry Terminal": ("maritime", "An active passenger and light-cargo terminal on Lake Washington, with a Soundline-style commuter ferry, ticket and identity checks, expedition travelers, compact cargo, and views toward the Eastside. The facility should be functional, repaired, and crowded rather than sleek."),
    "Leschi Freight Terminal": ("industrial", "A controlled Lake Washington freight yard handling vehicle ferries, rugged cargo carriers, cranes, pallets of recovered technology, inspection crews, and salvage convoys arriving from the Eastside. Emphasize heavy logistics and security without corporate polish."),
    "Afterimage": ("street", "A sophisticated but dangerous Meridian nightclub where music, brokers, runners, and private deals overlap. Use a credible repurposed urban interior, selective teal and amber light, guarded private balconies, and a crowd whose body language makes clear that the venue is influential but not neutral."),
    "The Third Door": ("street", "An exclusive neutral negotiation venue for experienced runners and fixers: an understated entrance, controlled reception, sound-dampened private booths, observant staff, and tense professionals meeting without visible weapons drawn. Convey enforced neutrality without depicting or naming its hidden overseers."),
    "The Foundry": ("industrial", "A vast converted industrial makerspace near Gas Works Park, filled with fabrication bays, machine tools, cranes, shared worktables, half-finished prototypes, safety markings, and many generations of ongoing projects. Show skilled members collaborating and sponsoring visitors in a functional, crowded space."),
    "Gas Works Park": ("industrial", "The preserved towers, pipes, and painted machinery of Gas Works Park used as an open public gathering place, with district residents, makers, and families overlooking the canal. Keep all activity above ground and do not imply secret tunnels, creatures, or confirmed subsurface structures."),
    "Fremont Lenin Statue": ("civic", "The familiar Lenin statue as a public meeting point amid Gasworks' eccentric street life, surrounded by repaired storefronts, public art, bicycles, makers, and neighborhood foot traffic. Preserve the landmark's recognizable physical presence without adding readable slogans or political text."),
    "Physics-Astronomy Prometheus Shard": ("academic", "A dark, expended technological artifact displayed securely in a university physics-astronomy lobby, surrounded by restrained cases, scientific instruments, students, and visible security observation. It should look inert but historically consequential, with no active magical discharge."),
    "Allen Center Prometheus Shard": ("academic", "An expended Prometheus Shard inside a modern computing-center lobby under both university and corporate observation, with glass, concrete, access controls, researchers, and subtle surveillance. Distinguish the setting from the physics display while keeping the artifact inert and unexplained."),
    "Bombshell Mutual Works": ("civic", "A busy mutual-aid and reconstruction hub in a repaired warehouse: supply shelves, tool lending, neighborhood maps without readable text, repair teams, food distribution, and residents coordinating practical relief. The atmosphere should be competent, welcoming, and under-resourced rather than sentimental."),
    "Church of the Shattered Glass": ("uncanny", "An active Bombshell congregation inside a repaired church whose damaged stained glass has been deliberately preserved and reassembled, with worshippers, mutual-aid supplies, candlelight, and uncompromising ritual geometry. Keep the supernatural implication restrained and do not explicitly reveal the true object of worship."),
    "West Seattle High Bridge": ("industrial", "A surviving high bridge operating as critical infrastructure, with repaired spans, Civic Guard checkpoints, inspection lanes, freight traffic, and the peninsula visible beyond. Show controlled everyday passage rather than an active combat scene."),
    "1st Avenue South Bridge": ("industrial", "A rugged southern vehicle and freight crossing with movable bridge machinery, repaired steelwork, inspection booths, cargo trucks, and guarded access toward West Seattle. Emphasize industrial function and layered maintenance."),
    "Washington Park Arboretum Wild": ("uncanny", "A recognizable urban arboretum transformed by dense altered vegetation, partially swallowed paths, subtle impossible growth patterns, guide markers without readable text, and a small equipped expedition moving cautiously. Do not depict any specific rumored creature or settled explanation."),
    "Madrona Decay Wild": ("uncanny", "A lakefront residential area collapsing into an urban decay Wild: buckled streets, unstable houses, altered roots and vines, marked perimeter routes, and distant recovery crews. Keep the hazard ecological and structural; do not invent a named monster or definitive supernatural cause."),
    "AQRE / The Works": ("industrial", "Gasworks' annual exposition and induction festival staged like a compact nineteenth-century world's fair rebuilt by cyberpunk makers: temporary halls, working prototypes, demonstrations, art-machines, food, crowds, and prospective members. Make it celebratory, inventive, and slightly hazardous, with no readable banners or labels."),
    "Eriador, Inc.": ("industrial", "A small active technology firm embedded within the larger Gasworks workshop ecosystem: compact offices opening directly into a practical fabrication floor, a small skilled team, repaired instruments, prototypes, and appointment-controlled entry. It should feel independent and technically serious, not like a corporate tower."),
    "Kirkland Downs": ("frontier", "A Lake Washington fishing, agricultural, and salvage enclave built among earthquake-damaged lakefront structures: docks, small boats, gardens, repaired homes, salvage sheds, and a modest civic center. Show local self-government and working trade links."),
    "Badvue": ("frontier", "Former downtown Bellevue transformed into a casino boomtown and expedition hub: occupied glass towers, improvised casino entrances, outfitters, guarded salvage money, crowded streets, and competing house compounds. Keep the frontier energy fast and opportunistic without a cartoon neon-strip aesthetic."),
    "Mercer Island Outpost": ("frontier", "An agrarian lake outpost on Mercer Island with terraced food plots, repaired waterfront homes, small cargo docks, fishing craft, and locally maintained roads. Frame Eastside ruins across the water to show operational ties while keeping the island geographically separate from the Silicon Wilds."),
    "Forgetown": ("industrial", "A walled manufacturing settlement built around former Factoria, with controlled gates, rugged production halls, loading yards, entrepreneurs, and workers scaling rough Gasworks prototypes into practical goods. The place should feel competitive, noisy, and economically vital."),
    "Fool's End": ("frontier", "A fortified settlement occupying Redmond's surviving approach, with hardened walls, toll inspection lanes, repurposed office structures, patrols, traders, and the SR-520 route continuing east. Convey a durable military fief without depicting an active siege."),
    "I-405 Wilds Corridor": ("frontier", "A trade convoy on surviving I-405 segments linking Eastside settlements, moving through patched pavement, vegetation, collapsed interchanges, negotiated toll posts, and settlement patrols. Show a usable but discontinuous commercial spine."),
    "SR-520 Wilds Corridor": ("frontier", "A convoy moving east from Lake Washington toward Redmond along partially secured SR-520, crossing repaired gaps between overgrown technology campuses, toll positions, and hazardous abandoned segments. The direction from lake frontier to fortified interior should be visually clear."),
    "Port of Tacoma": ("industrial", "A vast working deepwater port with container cranes, ocean-going cargo ships, rail transfer, military logistics, harbor patrols, and credentialed freight zones. Show the port as the material foundation of Tacoma's independence and regional trade."),
    "Porter Way Memorial": ("memorial", "A restrained roadside memorial near Milton honoring school-bus bombing victims: a protected shelter, weathered personal offerings, flowers, small lights, families and travelers pausing beside the route. Do not reenact the attack, show bodies, or introduce current extremist activity."),
    "Tacoma Defensive Zone": ("industrial", "A porous fortified approach near Fife and Milton where through traffic continues along I-5 while side routes into Tacoma pass inspection. Include layered checkpoints, earthworks, watch positions, commercial vehicles, and visible restraint rather than a sealed border or firefight."),
}


PARENT_BY_NAME = {
    "Space Needle": "district-2-queen-anne",
    "Helios Campus": "district-3-helios-corridor",
    "Boeing Field Fortress": "district-10-bombshell",
    "The Names We Carry": "district-10-bombshell",
    "The Seam": "district-4-meridian",
    "Madison Ferry Terminal": "district-4-meridian",
    "Leschi Freight Terminal": "district-4-meridian",
    "Afterimage": "district-4-meridian",
    "The Third Door": "district-4-meridian",
    "The Foundry": "district-7-gasworks",
    "Gas Works Park": "district-7-gasworks",
    "Fremont Lenin Statue": "district-7-gasworks",
    "Physics-Astronomy Prometheus Shard": "district-8-university-enclave",
    "Allen Center Prometheus Shard": "district-8-university-enclave",
    "Bombshell Mutual Works": "district-10-bombshell",
    "Church of the Shattered Glass": "district-10-bombshell",
    "West Seattle High Bridge": "district-11-west-seattle",
    "1st Avenue South Bridge": "district-11-west-seattle",
    "Washington Park Arboretum Wild": "district-4-meridian",
    "Madrona Decay Wild": "district-4-meridian",
    "AQRE / The Works": "district-7-gasworks",
    "Eriador, Inc.": "district-7-gasworks",
    "Kirkland Downs": "region-104-silicon-wilds",
    "Badvue": "region-104-silicon-wilds",
    "Forgetown": "region-104-silicon-wilds",
    "Fool's End": "region-104-silicon-wilds",
    "I-405 Wilds Corridor": "region-104-silicon-wilds",
    "SR-520 Wilds Corridor": "region-104-silicon-wilds",
    "Port of Tacoma": "region-103-tacoma",
    "Porter Way Memorial": "region-103-tacoma",
    "Tacoma Defensive Zone": "region-103-tacoma",
}


def load_features(filename: str) -> list[dict[str, Any]]:
    return json.loads((ATLAS / filename).read_text(encoding="utf-8"))["features"]


def record_id(layer: str, feature: dict[str, Any]) -> str:
    return f"{layer}-{feature['id']}-{slugify(feature['properties']['name'])}"


def source_summary(properties: dict[str, Any]) -> str:
    parts = [text_value(properties.get("description"))]
    labels = (
        ("Status", properties.get("status")),
        ("Known for", properties.get("known_for")),
        ("Access", properties.get("access")),
        ("Governance", properties.get("governance")),
        ("Communities", properties.get("communities")),
        ("Organizations", properties.get("organizations")),
        ("Connections", properties.get("connections")),
    )
    for label, value in labels:
        rendered = text_value(value)
        if rendered:
            parts.append(f"{label}: {rendered}.")
    return " ".join(part for part in parts if part).strip()


def preset_for(layer: str, category: str) -> str:
    if layer == "region":
        return "regionEnvironment"
    if layer == "district":
        return "districtEnvironment"
    if category == "route":
        return "routeEnvironment"
    if category == "event":
        return "eventEnvironment"
    return "locationEnvironment"


def family_for(layer: str, category: str) -> str:
    return layer if layer in {"region", "district"} else category


def frozen_prompt(name: str, preset: str, summary: str, direction: str, negative: str) -> str:
    scale = {
        "regionEnvironment": "a cinematic regional establishing image",
        "districtEnvironment": "a cinematic district establishing image",
        "locationEnvironment": "a focused cinematic location establishing image",
        "routeEnvironment": "a cinematic travel-corridor establishing image",
        "eventEnvironment": "a cinematic public-event establishing image",
    }[preset]
    return (
        f"Create original Cybermancy lore artwork for {name}, {scale}. "
        f"Canonical context: {summary} "
        f"Visual direction: {direction} "
        "Use a grounded semi-photorealistic Cybermancy aesthetic: believable near-future cyberpunk, lived-in human activity, functional technology, physically plausible architecture and materials, visible maintenance and repair, muted charcoal and steel colors, cool teal-blue ambient light, restrained amber-orange practical light, Seattle atmospheric depth, readable shadows, and selective technological or Resonance glow only where motivated. "
        "Compose as a 3:2 landscape environment suitable for an atlas lore panel, with a clear focal structure, foreground human scale, midground activity, and geographic context in the background. "
        f"Avoid: {negative}; text, captions, logos, readable signage, labels, maps, diagrams, borders, stat blocks, UI or HUD overlays, pseudo-writing, copyrighted character likenesses, cartoon or anime treatment, superhero styling, generic space-marine imagery, glossy plastic, excessive chrome, rainbow neon, unexplained glowing clutter, sterile utopian futurism, muddy darkness, or an uninhabited generic cyberpunk city."
    )


def build_rows() -> list[dict[str, str]]:
    layer_files = (("region", "regions.geojson"), ("district", "districts.geojson"), ("context", "context.geojson"))
    features_by_id: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, str]] = []

    for layer, filename in layer_files:
        for feature in load_features(filename):
            props = feature["properties"]
            name = props["name"]
            if name not in VISUAL_SPECS:
                raise ValueError(f"Missing visual specification for {name}")
            substyle, direction = VISUAL_SPECS[name]
            category = text_value(props.get("category")) or layer
            rid = record_id(layer, feature)
            features_by_id[rid] = feature
            parent_id = "region-101-seattle" if layer == "district" else PARENT_BY_NAME.get(name, "")
            summary = source_summary(props)
            preset = preset_for(layer, category)
            negative = "do not reveal or invent GM-only actors, conspiracies, hidden facilities, secret inhabitants, unresolved rumors, or definitive explanations for ambiguous phenomena"
            if name in {"Silicon Wilds", "Meridian–Silicon Wilds Ferry Route", "Mercer Island Outpost"}:
                negative += "; do not place Silicon Wilds territory west of Lake Washington or merge Mercer Island into its geographic boundary"
            if name in {"The Names We Carry", "Porter Way Memorial"}:
                negative += "; no graphic violence, bodies, active attack, or triumphant military framing"
            if "Wild" in name or name == "Cascade Approaches":
                negative += "; do not invent a featured monster, named entity, or settled cause"

            rows.append({
                "enabled": "true",
                "record_id": rid,
                "family": family_for(layer, category),
                "asset_kind": "primary",
                "preset_family": preset,
                "parent_id": parent_id,
                "parent_name": "",
                "name": name,
                "slug": slugify(name),
                "source_dataset": filename,
                "source_feature_id": str(feature["id"]),
                "source_section": "Seattle Atlas",
                "source_extraction_status": "canonical-geojson",
                "source_confidence": "high",
                "geometry_type": feature["geometry"]["type"],
                "atlas_category": category,
                "substyle": substyle,
                "aspect_ratio": "3:2",
                "size": "1536x1024",
                "quality": "medium",
                "transparent_background": "false",
                "source_summary": summary,
                "subject_brief": direction,
                "prompt_notes": "Use public atlas canon only. Preserve recognizable Puget Sound geography and the subject's relationship to adjacent districts or routes.",
                "negative_notes": negative,
                "prompt": frozen_prompt(name, preset, summary, direction, negative),
                "output_filename": f"{layer if layer != 'context' else ('route' if category == 'route' else 'poi')}-{slugify(name)}.webp",
                "selection_notes": f"Generated from {filename} feature {feature['id']}; GM notes intentionally excluded from image prompt.",
            })

    name_by_id = {row["record_id"]: row["name"] for row in rows}
    for row in rows:
        if row["parent_id"]:
            row["parent_name"] = name_by_id[row["parent_id"]]
    return rows


PRESETS = {
    "presetVersion": VERSION,
    "name": "Cybermancy Seattle Lore Art",
    "visualCanon": "docs/gm-facing/meta/visual-canon.md",
    "defaults": {
        "model": MODEL,
        "quality": "medium",
        "background": "opaque",
        "outputFormat": "webp",
        "outputCompression": 92,
    },
    "basePrompt": "Grounded semi-photorealistic Cybermancy environment art with believable near-future infrastructure, lived-in human activity, restrained cyberpunk lighting, and clear geographic identity.",
    "globalNegative": [
        "no text, captions, labels, logos, readable signage, maps, diagrams, borders, stat blocks, UI, HUD overlays, or pseudo-writing",
        "no GM-only secrets, hidden campaign actors, unresolved rumors presented as fact, or invented named characters",
        "no cartoon, anime, superhero, generic space-marine, glossy-plastic, excessive-chrome, rainbow-neon, or sterile-utopian styling",
        "no unmotivated glow, muddy darkness, empty generic cyberpunk streets, or geography that contradicts the atlas",
    ],
    "substyles": {
        "academic": {"description": "Public education and research under uneven corporate influence.", "palette": "weathered brick, concrete, steel blue, institutional white, restrained corporate accents", "materials": "brick, concrete, glass, laboratory composites, old wood, technical fabric"},
        "civic": {"description": "Human-scale public life, municipal continuity, and neighborhood institutions.", "palette": "charcoal, rain blue, muted civic colors, warm practical light", "materials": "weathered concrete, painted steel, brick, repaired glass, public furnishings"},
        "corporate": {"description": "Controlled, premium, precise, and quietly surveilled.", "palette": "black, white, steel blue, restrained gold and amber", "materials": "architectural glass, ceramic composite, precision metal, premium textile"},
        "frontier": {"description": "Independent settlements, salvage economies, repaired infrastructure, and ecological reclamation.", "palette": "forest green, wet concrete, rust, steel blue, amber work light", "materials": "salvaged steel, timber, concrete, patched polymer, vegetation"},
        "industrial": {"description": "Working fabrication, logistics, repair, and heavy infrastructure.", "palette": "blackened steel, rust, safety amber, teal work light, weathered paint", "materials": "painted steel, concrete, heavy machinery, carbon composites, worn tools"},
        "maritime": {"description": "Puget Sound trade, ferries, fisheries, docks, and wet-weather infrastructure.", "palette": "deep water blue, fog grey, oxidized metal, faded paint, warm cabin light", "materials": "marine steel, wet timber, rope, composite hulls, concrete docks"},
        "memorial": {"description": "Respectful public remembrance centered on survivors and civic continuity.", "palette": "weathered steel, stone grey, subdued flowers, warm candle or vigil light", "materials": "stabilized wreckage, stone, glass, paper offerings, fabric"},
        "street": {"description": "Dense mixed economies, local custom, practical improvisation, and watchful social life.", "palette": "charcoal, wet asphalt, faded paint, selective teal and amber", "materials": "old masonry, repaired polymer, concrete, worn leather, mixed-generation hardware"},
        "uncanny": {"description": "Ninety percent believable environment with one selective Resonance or ecological impossibility.", "palette": "muted natural tones, steel blue, subtle cyan-violet anomaly, warm human light", "materials": "real vegetation, damaged concrete, glass, electronics, restrained luminous geometry"},
    },
    "assetFamilies": {
        "regionEnvironment": {"composition": "3:2 panoramic regional establishing scene with layered geography and representative human activity", "promptNotes": ["show political and material identity through visible infrastructure", "avoid attempting a literal overhead map"], "size": "1536x1024", "quality": "medium", "background": "opaque", "outputFormat": "webp"},
        "districtEnvironment": {"composition": "3:2 district establishing scene with foreground human scale, characteristic streets or workplaces, and a readable skyline", "promptNotes": ["show ordinary life as well as district-defining infrastructure", "distinguish the district from generic Seattle cyberpunk"], "size": "1536x1024", "quality": "medium", "background": "opaque", "outputFormat": "webp"},
        "locationEnvironment": {"composition": "3:2 focused establishing view of a specific landmark, institution, settlement, transit facility, or hazard", "promptNotes": ["make the named subject visually dominant", "include enough surroundings to establish geographic context"], "size": "1536x1024", "quality": "medium", "background": "opaque", "outputFormat": "webp"},
        "routeEnvironment": {"composition": "3:2 cinematic travel scene along or across the route, emphasizing movement, infrastructure, control, and destination", "promptNotes": ["do not depict an overhead map", "make the route's practical function immediately legible"], "size": "1536x1024", "quality": "medium", "background": "opaque", "outputFormat": "webp"},
        "eventEnvironment": {"composition": "3:2 public event scene with a clear central activity, characteristic venue, and readable crowd behavior", "promptNotes": ["show the event in progress", "avoid readable banners or signage"], "size": "1536x1024", "quality": "medium", "background": "opaque", "outputFormat": "webp"},
    },
}


FIELDS = [
    "enabled", "record_id", "family", "asset_kind", "preset_family", "parent_id", "parent_name", "name", "slug",
    "source_dataset", "source_feature_id", "source_section", "source_extraction_status", "source_confidence",
    "geometry_type", "atlas_category", "substyle", "aspect_ratio", "size", "quality", "transparent_background",
    "source_summary", "subject_brief", "prompt_notes", "negative_notes", "prompt", "output_filename", "selection_notes",
]


SCHEMA = """# Cybermancy Seattle Lore Art Manifest Schema v0.1

**Status:** Working production schema

**Source:** Canonical GM Seattle Atlas GeoJSON, with GM-only notes excluded from prompts

**Expected enabled rows:** 51

## Purpose

This manifest is the deterministic production boundary between the Seattle Atlas canon and generated lore artwork. It records stable source linkage, prompt text, request parameters, output filenames, and parent geography. Image generation itself remains nondeterministic.

## Coverage

| Source layer | Required rows | Preset family |
|---|---:|---|
| Regions | 5 | `regionEnvironment` |
| Districts | 11 | `districtEnvironment` |
| Point and event POIs | 29 | `locationEnvironment` or `eventEnvironment` |
| Routes and corridors | 6 | `routeEnvironment` |

## Core fields

- `record_id`: stable `{layer}-{feature_id}-{slug}` identifier.
- `family`: atlas layer or context category.
- `preset_family`: request and composition preset resolved by the batch generator.
- `parent_id` / `parent_name`: containing district or region where one authoritative parent exists.
- `source_dataset` / `source_feature_id`: exact GeoJSON provenance.
- `source_summary`: player-visible canonical atlas properties only.
- `subject_brief`: feature-specific visual composition.
- `prompt`: frozen full prompt used exactly by the generator.
- `negative_notes`: feature-specific canon and spoiler exclusions.
- `output_filename`: namespaced stable WebP filename.

Additional columns follow the Edgeheart manifest conventions and are ignored safely by the generator where not required.

## Validation rules

1. Exactly 51 enabled rows: 5 regions, 11 districts, 29 point/event POIs, and 6 routes.
2. Each GM atlas feature appears exactly once and matches the player atlas by ID and name.
3. `record_id` and `output_filename` values are unique.
4. Every row resolves to a declared preset family and approved substyle.
5. Every row uses `3:2`, `1536x1024`, opaque WebP output.
6. Prompts use player-visible properties and never include `gm_notes`.
7. Silicon Wilds geography remains strictly east of Lake Washington; Mercer Island remains separate.
8. Memorial prompts remain non-graphic and do not reenact the violence.
9. Wild and Resonance prompts do not establish rumored entities or explanations as fact.

## Generator command

```powershell
python batch-image-generation-on-OpenAI-v2.py `
  --input art-production/seattle-lore/cybermancy-seattle-lore-art-manifest-v0.1.csv `
  --presets art-production/seattle-lore/cybermancy-seattle-lore-art-presets-v0.1.json `
  --outdir generated-art/seattle-lore `
  --dry-run
```

Remove `--dry-run` only after reviewing the generation ledger and approving a representative pilot.
"""


README = """# Seattle Lore Art Production

This directory contains the source-backed image-generation manifest for every named feature currently displayed by the Seattle Atlas.

## Files

- `cybermancy-seattle-lore-art-manifest-v0.1.csv`: primary input for the batch generator.
- `cybermancy-seattle-lore-art-manifest-v0.1.json`: equivalent machine-readable manifest using the generator-compatible `items` key.
- `cybermancy-seattle-lore-art-presets-v0.1.json`: Cybermancy environment-art presets required by manifest mode.
- `cybermancy-seattle-lore-art-manifest-schema-v0.1.md`: field definitions, coverage, validation rules, and dry-run command.

The prompts are frozen in each row. Preset metadata still controls request defaults and remains mandatory because the batch generator validates every `preset_family`.

## Rebuild

```powershell
python tools/build-seattle-lore-art-manifest.py
```

The builder fails if atlas coverage, player/GM feature identity, parent links, preset keys, substyles, or stable filenames drift.
"""


def validate(rows: list[dict[str, str]]) -> None:
    counts = {
        "region": sum(row["record_id"].startswith("region-") for row in rows),
        "district": sum(row["record_id"].startswith("district-") for row in rows),
        "route": sum(row["atlas_category"] == "route" for row in rows),
    }
    counts["poi"] = len(rows) - counts["region"] - counts["district"] - counts["route"]
    if len(rows) != 51 or counts != {"region": 5, "district": 11, "route": 6, "poi": 29}:
        raise ValueError(f"Unexpected coverage: rows={len(rows)} counts={counts}")
    for key in ("record_id", "output_filename"):
        values = [row[key] for row in rows]
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {key}")
    for row in rows:
        if row["preset_family"] not in PRESETS["assetFamilies"]:
            raise ValueError(f"Unknown preset in {row['record_id']}")
        if row["substyle"] not in PRESETS["substyles"]:
            raise ValueError(f"Unknown substyle in {row['record_id']}")
        if row["parent_id"] and not any(candidate["record_id"] == row["parent_id"] for candidate in rows):
            raise ValueError(f"Unknown parent in {row['record_id']}")
        if row["aspect_ratio"] != "3:2" or row["size"] != "1536x1024" or row["transparent_background"] != "false":
            raise ValueError(f"Invalid request geometry in {row['record_id']}")
        prompt_lower = row["prompt"].lower()
        for forbidden in ("wessie", "etta 'switch'", "garran 'rampart'", "ilyra 'copper'", "first ephor sabine"):
            if forbidden in prompt_lower:
                raise ValueError(f"GM-only term in {row['record_id']}: {forbidden}")

    for filename in ("regions.geojson", "districts.geojson", "context.geojson"):
        gm = json.loads((ATLAS / filename).read_text(encoding="utf-8"))["features"]
        player = json.loads((PLAYER_ATLAS / filename).read_text(encoding="utf-8"))["features"]
        gm_keys = [(item["id"], item["properties"]["name"]) for item in gm]
        player_keys = [(item["id"], item["properties"]["name"]) for item in player]
        if gm_keys != player_keys:
            raise ValueError(f"GM/player feature identity mismatch: {filename}")
        public_fields = {
            "name", "category", "status", "description", "known_for", "access",
            "governance", "communities", "organizations", "connections",
        }
        for gm_feature, player_feature in zip(gm, player):
            for field in public_fields:
                if gm_feature["properties"].get(field) != player_feature["properties"].get(field):
                    raise ValueError(
                        f"GM/player public-field mismatch: {filename} feature {gm_feature['id']} field {field}"
                    )


def main() -> None:
    rows = build_rows()
    validate(rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUT / f"cybermancy-seattle-lore-art-manifest-v{VERSION}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    json_path = OUTPUT / f"cybermancy-seattle-lore-art-manifest-v{VERSION}.json"
    json_path.write_text(json.dumps({
        "manifestVersion": VERSION,
        "visualCanon": "docs/gm-facing/meta/visual-canon.md",
        "presetFile": f"cybermancy-seattle-lore-art-presets-v{VERSION}.json",
        "defaultModel": MODEL,
        "sourceDatasets": ["regions.geojson", "districts.geojson", "context.geojson"],
        "itemCount": len(rows),
        "items": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (OUTPUT / f"cybermancy-seattle-lore-art-presets-v{VERSION}.json").write_text(
        json.dumps(PRESETS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT / f"cybermancy-seattle-lore-art-manifest-schema-v{VERSION}.md").write_text(SCHEMA, encoding="utf-8")
    (OUTPUT / "README.md").write_text(README, encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
