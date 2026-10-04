#!/usr/bin/env python3
"""
Batch image generator for Cybermancy / Edgeheart production.

New in v2 draft:
- External visual-canon/preset JSON via --presets.
- Manifest columns for family, substyle, size, quality, transparency,
  subject brief, parent linkage, and full prompt override.
- Deterministic prompt compilation and JSONL generation ledger.
- Per-row PNG / WEBP / JPEG output.
- Transparent token generation through Image API background="transparent".
- --dry-run compiles prompts and request parameters without API calls.
- Existing simple name/description/effect/style/organ CSVs can still run in legacy mode.

Dependencies:
    pip install -U openai python-slugify python-dotenv

Environment:
    OPENAI_API_KEY
    OPENAI_IMAGE_MODEL (optional; default gpt-image-2.5-flare)
"""

import argparse
import base64
import csv
import json
import logging
import os
import time
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

LEGACY_EFFECT_PALETTE: Dict[str, str] = {
    "healing": "warm red-orange to amber",
    "stress": "soft violet-blue to lavender",
    "physical": "cyan-teal to electric blue",
    "strength": "amber-gold to bronze",
    "cognitive": "neon green to lime-white",
    "charisma": "neon green to lime-white",
    "armor": "steel grey to leather brown, realistic textile/leather tones",
    "loot": "infer from description; metallic accents appropriate to the object",
    "circuit": "glowing circuitry motif, light grey background, neon blue and green accents",
    "weapons": "gunmetal grey with electric cyan and molten red-orange accents",
    "corporate": "gunmetal and chrome with cold blue-white highlights",
    "military": "matte steel with amber-orange tracer glows",
    "prototype": "graphite and silver with lime-green or violet plasma lines",
    "street": "scratched chrome with graffiti teal and orange",
    "antique": "aged bronze and iron with faint amber and smoke-blue glow",
    "stealth": "matte black and charcoal with subtle purple or cyan pulse lines",
    "cybernetic": "metallic organ implants integrated into skin; accent glow matches enhancement type",
    "programs": "graphite/black vector iconography with cyan circuit lines, glyph-like and minimal",
}

LEGACY_STYLE_PRESETS: Dict[str, str] = {
    "item": (
        "cyberpunk item icon, semi-realistic rendering, physically believable materials, "
        "clean silhouette, soft reflections, subtle vignette, no text or labels, "
        "light grey background, consistent luminance"
    ),
    "weapon": (
        "cyberpunk weapon icon, semi-realistic rendering, gunmetal/graphite materials, "
        "clean silhouette, subtle reflections, medium grey background, restrained glow"
    ),
    "program": (
        "minimalist glyph-like software icon, vector feel, crisp edges, graphite/black base "
        "with neon circuitry accents, light grey background, no text"
    ),
    "cybernetic": (
        "semi-abstract cybernetics study with realistic anatomical integration, "
        "clean composition, functional implant design, no text or busy HUD"
    ),
    "ice": (
        "semi-abstract cyberpunk ICE concept art, luminous circuit geometry, crystalline or "
        "tessellated data structures, controlled technological glow, no text or borders"
    ),
}

LEGACY_ORGAN_FOCUS = {
    "eye": "close-up portrait; one cybernetic eye prominently integrated",
    "arm": "upper torso with cybernetic arm clearly visible",
    "hand": "close-up of cybernetic hand with functional articulation",
    "legs": "mid or full-body with cybernetic legs visible",
    "spinal": "rear three-quarter angle showing spinal interface",
    "skin": "mid-torso showing technology beneath intact skin",
    "vocal chords": "neck/throat close-up with integrated vocal hardware",
    "bones": "anatomical study showing reinforced skeletal elements",
    "nervous system": "anatomical study with neural interface pathways",
    "brain": "skull/cranial study with implanted cortex hardware",
}


def truthy(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def slugify_safe(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "untitled"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_rows(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix == ".json":
        data = load_json(path)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            data = data["items"]
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list or an object containing an 'items' list.")
        return [dict(row) for row in data if isinstance(row, dict)]
    raise ValueError(f"Unsupported input format: {path.suffix}")


def load_presets(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Preset file must be a JSON object.")
    return data


def parse_listish(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [clean(x) for x in value if clean(x)]
    text = clean(value)
    if not text:
        return []
    return [part.strip() for part in text.split("|") if part.strip()]


def choose_output_format(filename: str, fallback: str = "webp") -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".png":
        return "png"
    if ext in {".jpg", ".jpeg"}:
        return "jpeg"
    if ext == ".webp":
        return "webp"
    return fallback


def ensure_extension(filename: str, output_format: str) -> str:
    if Path(filename).suffix:
        return filename
    ext = ".jpg" if output_format == "jpeg" else f".{output_format}"
    return filename + ext


def build_substyle_text(substyle: str, presets: Dict[str, Any]) -> str:
    block = (presets.get("substyles") or {}).get(substyle)
    if not block:
        valid = ", ".join(sorted((presets.get("substyles") or {}).keys()))
        raise ValueError(f"Unknown substyle '{substyle}'. Valid: {valid}")
    return (
        f"Socioeconomic substyle: {substyle}. "
        f"{clean(block.get('description'))} "
        f"Palette: {clean(block.get('palette'))}. "
        f"Materials: {clean(block.get('materials'))}."
    )


def build_family_text(preset_family: str, presets: Dict[str, Any]) -> str:
    block = (presets.get("assetFamilies") or {}).get(preset_family)
    if not block:
        valid = ", ".join(sorted((presets.get("assetFamilies") or {}).keys()))
        raise ValueError(f"Unknown preset_family '{preset_family}'. Valid: {valid}")
    notes = "; ".join(parse_listish(block.get("promptNotes")))
    text = f"Asset family: {preset_family}. Composition: {clean(block.get('composition'))}."
    if notes:
        text += f" Family guidance: {notes}."
    return text


def compile_manifest_prompt(row: Dict[str, Any], presets: Dict[str, Any]) -> str:
    frozen = clean(row.get("prompt"))
    if frozen:
        return frozen

    parts: List[str] = [clean(presets.get("basePrompt"))]
    parts.append(build_substyle_text(clean(row.get("substyle")), presets))
    preset_family = clean(row.get("preset_family"))
    parts.append(build_family_text(preset_family, presets))

    name = clean(row.get("name"))
    subject = clean(row.get("subject_brief"))
    if name:
        parts.append(f"Subject name: {name}.")
    if subject:
        parts.append(f"Subject brief: {subject}.")

    parent_name = clean(row.get("parent_name"))
    if preset_family == "competencyCard" and parent_name:
        parts.append(
            f"Parent Competency: {parent_name}. The image must visibly inherit the parent "
            "Competency's recurring visual motifs without becoming a duplicate."
        )
    elif preset_family == "adversaryToken" and parent_name:
        parts.append(
            f"Identity continuity: this token depicts the same adversary identity as the "
            f"accepted portrait for {parent_name}; do not redesign the character."
        )

    row_notes = clean(row.get("prompt_notes"))
    if row_notes:
        parts.append(f"Specific notes: {row_notes}.")

    negatives = parse_listish(presets.get("globalNegative"))
    row_negative = clean(row.get("negative_notes"))
    if row_negative:
        negatives.append(row_negative)
    if negatives:
        parts.append("Avoid: " + "; ".join(negatives) + ".")

    return " ".join(part for part in parts if part).strip()


def resolve_manifest_request(
    row: Dict[str, Any],
    presets: Dict[str, Any],
    cli_model: Optional[str],
    cli_quality: Optional[str],
) -> Dict[str, Any]:
    preset_family = clean(row.get("preset_family"))
    family = (presets.get("assetFamilies") or {}).get(preset_family)
    if not family:
        raise ValueError(f"Missing asset-family preset: {preset_family}")

    defaults = presets.get("defaults") or {}
    model = (
        cli_model
        or clean(row.get("model"))
        or clean(defaults.get("model"))
        or os.getenv("OPENAI_IMAGE_MODEL")
        or "gpt-image-2.5-flare"
    )
    quality = (
        clean(row.get("quality"))
        or cli_quality
        or clean(family.get("quality"))
        or clean(defaults.get("quality"))
        or "medium"
    )
    size = clean(row.get("size")) or clean(family.get("size")) or "1024x1024"

    if clean(row.get("transparent_background")):
        transparent = truthy(row.get("transparent_background"))
    else:
        transparent = clean(family.get("background")).lower() == "transparent"

    background = "transparent" if transparent else clean(
        family.get("background") or defaults.get("background") or "opaque"
    )

    default_format = clean(
        family.get("outputFormat") or defaults.get("outputFormat") or "webp"
    ).lower()
    filename = clean(row.get("output_filename")) or slugify_safe(
        clean(row.get("slug") or row.get("name"))
    )
    output_format = choose_output_format(filename, default_format)
    filename = ensure_extension(filename, output_format)

    if background == "transparent" and output_format not in {"png", "webp"}:
        raise ValueError("Transparent output requires PNG or WebP.")

    compression = family.get("outputCompression", defaults.get("outputCompression", 92))
    try:
        compression = int(compression)
    except Exception:
        compression = 92

    return {
        "model": model,
        "quality": quality,
        "size": size,
        "background": background,
        "output_format": output_format,
        "output_compression": compression,
        "filename": filename,
    }


def legacy_prompt(row: Dict[str, Any]) -> str:
    name = clean(row.get("name") or row.get("title"))
    desc = clean(row.get("description") or row.get("text") or row.get("blurb"))
    effect = clean(row.get("effect") or row.get("domain") or row.get("category")).lower()
    style = clean(row.get("style") or row.get("visual_style") or row.get("art_style")).lower()
    organ = clean(row.get("organ") or row.get("body_part") or row.get("cyber_organ")).lower()

    style_text = LEGACY_STYLE_PRESETS.get(style, LEGACY_STYLE_PRESETS["item"])
    palette = LEGACY_EFFECT_PALETTE.get(
        effect, "cyan-teal to electric-blue accents on a light grey background"
    )

    if style == "cybernetic" or effect == "cybernetic":
        focus = LEGACY_ORGAN_FOCUS.get(
            organ,
            "depict the augmentation integrated into a human body with realistic anatomical logic",
        )
    else:
        focus = "depict the subject in isolation with a clean readable silhouette"

    return (
        f"Generate an image for '{name}'. Description: {desc}. "
        f"Style: {style_text}. Palette guidance: {palette}. "
        f"Composition guidance: {focus}. No text or labels."
    )


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_base64_image(b64_data: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(b64_data))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-generate images from legacy Cybermancy rows or an externalized art manifest."
    )
    parser.add_argument("--input", "-i", required=True, type=Path)
    parser.add_argument("--outdir", "-o", required=True, type=Path)
    parser.add_argument("--presets", type=Path, help="External art-preset JSON. Enables manifest mode.")
    parser.add_argument("--model", default=None, help="Override image model for all rows.")
    parser.add_argument("--quality", default=None, help="Override image quality for all rows.")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Compile prompts without API calls.")
    parser.add_argument(
        "--ledger", type=Path, default=None,
        help="JSONL ledger path; defaults to <outdir>/generation-ledger.jsonl"
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s: %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    presets = load_presets(args.presets)
    rows = load_rows(args.input)
    if args.max_items and args.max_items > 0:
        rows = rows[: args.max_items]

    args.outdir.mkdir(parents=True, exist_ok=True)
    ledger = args.ledger or (args.outdir / "generation-ledger.jsonl")

    client: Optional[Any] = None
    if not args.dry_run:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("Missing OPENAI_API_KEY")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SystemExit("Missing dependency: pip install -U openai") from exc
        client = OpenAI(api_key=api_key)

    manifest_mode = presets is not None
    generated = skipped = failed = disabled = 0

    for index, row in enumerate(rows, start=1):
        if manifest_mode and not truthy(row.get("enabled"), default=True):
            disabled += 1
            continue

        try:
            if manifest_mode:
                record_id = clean(row.get("record_id"))
                name = clean(row.get("name"))
                if not record_id:
                    raise ValueError("Enabled manifest row missing record_id.")
                if not name:
                    raise ValueError(f"{record_id}: enabled manifest row missing name.")

                prompt = compile_manifest_prompt(row, presets)
                request = resolve_manifest_request(row, presets, args.model, args.quality)
                filename = request.pop("filename")
                out_path = args.outdir / filename
            else:
                record_id = clean(row.get("record_id")) or f"legacy-{index:04d}"
                name = clean(row.get("name") or row.get("title"))
                prompt = legacy_prompt(row)

                filename = clean(row.get("img") or row.get("image") or row.get("filename"))
                filename = filename or slugify_safe(name) + ".webp"
                if not Path(filename).suffix:
                    filename += ".webp"
                output_format = choose_output_format(filename, "webp")
                out_path = args.outdir / filename

                request = {
                    "model": args.model or os.getenv("OPENAI_IMAGE_MODEL") or "gpt-image-2.5-flare",
                    "quality": args.quality or "medium",
                    "size": "1024x1024",
                    "background": "opaque",
                    "output_format": output_format,
                    "output_compression": 92,
                }

            ledger_base = {
                "index": index,
                "record_id": record_id,
                "name": name,
                "prompt": prompt,
                "request": dict(request),
                "output": str(out_path),
            }

            if out_path.exists() and not args.overwrite and not args.dry_run:
                skipped += 1
                append_jsonl(ledger, {**ledger_base, "status": "skipped-existing"})
                logging.info("[%s/%s] SKIP %s", index, len(rows), out_path.name)
                continue

            if args.dry_run:
                append_jsonl(ledger, {**ledger_base, "status": "dry-run"})
                logging.info("[%s/%s] DRY %s", index, len(rows), out_path.name)
                continue

            assert client is not None
            api_request = {
                "model": request["model"],
                "prompt": prompt,
                "size": request["size"],
                "quality": request["quality"],
                "background": request["background"],
                "output_format": request["output_format"],
            }
            if request["output_format"] in {"webp", "jpeg"}:
                api_request["output_compression"] = request["output_compression"]

            response = client.images.generate(**api_request)
            if not response.data or not response.data[0].b64_json:
                raise RuntimeError("Image API returned no base64 image data.")

            write_base64_image(response.data[0].b64_json, out_path)
            generated += 1
            append_jsonl(
                ledger,
                {
                    **ledger_base,
                    "status": "generated",
                    "request_id": getattr(response, "_request_id", None),
                },
            )
            logging.info("[%s/%s] WROTE %s", index, len(rows), out_path.name)
            time.sleep(args.delay)

        except Exception as exc:
            failed += 1
            append_jsonl(
                ledger,
                {
                    "index": index,
                    "record_id": clean(row.get("record_id")) or f"legacy-{index:04d}",
                    "name": clean(row.get("name") or row.get("title")),
                    "status": "failed",
                    "error": repr(exc),
                },
            )
            logging.error("[%s/%s] FAILED %s: %s", index, len(rows), clean(row.get("name")), exc)

    logging.info(
        "Done. generated=%s skipped=%s failed=%s disabled=%s rows=%s ledger=%s",
        generated, skipped, failed, disabled, len(rows), ledger,
    )


if __name__ == "__main__":
    main()