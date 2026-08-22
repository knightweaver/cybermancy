#!/usr/bin/env python3
"""Cybermancy Rulebook Step 5 content-only PDF builder.

Render compatibility patch r1: deterministic WebP/raster conversion for LuaLaTeX,
stale-output protection, UTF-8 subprocess handling, and clearer diagnostics.

Consumes Step 4 outputs from build/rulebook/source/assembled and metadata. It does
not select canonical sources or regenerate normalization.

Typical usage from repository root:
    python build/rulebook/scripts/build-rulebook-pdf.py build --profile all
    python build/rulebook/scripts/build-rulebook-pdf.py validate --profile complete-rulebook
    python build/rulebook/scripts/build-rulebook-pdf.py repro-check --profile all

For convenience, omitting the subcommand defaults to build:
    python build/rulebook/scripts/build-rulebook-pdf.py --profile player-guide
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
RULEBOOK_DIR = SCRIPT_DIR.parent
DEFAULT_REPO_ROOT = RULEBOOK_DIR.parent.parent
SOURCE_DIR = RULEBOOK_DIR / "source"
ASSEMBLED_DIR = SOURCE_DIR / "assembled"
METADATA_DIR = SOURCE_DIR / "metadata"
PANDOC_DIR = RULEBOOK_DIR / "pandoc"
FILTER_PATH = PANDOC_DIR / "filters" / "prototype.lua"
HEADER_PATH = PANDOC_DIR / "templates" / "prototype-header.tex"
MANIFEST_DIR = RULEBOOK_DIR / "manifests"
PROTOTYPE_DIR = RULEBOOK_DIR / "prototype"
REPORT_DIR = RULEBOOK_DIR / "reports"

GM_DIVIDER = "GM MATERIAL — SPOILERS BEYOND THIS POINT"
MARKDOWN_FROM = "markdown+fenced_divs+bracketed_spans+pipe_tables+grid_tables+definition_lists+raw_attribute"
PROFILE_CONFIG = {
    "complete-rulebook": {
        "title": "Cybermancy Complete Rulebook",
        "input": "complete-rulebook.md",
        "output": "Cybermancy_Core_Rulebook_Content_Prototype.pdf",
        "audiences": {"shared", "player", "gm"},
        "parts": [
            "The World of Cybermancy", "Cybermancy Rules",
            "Characters and Character Options", "Equipment and Technology",
            "GM World Guide", "GM Encounter Toolkit",
        ],
    },
    "player-guide": {
        "title": "Cybermancy Player Guide",
        "input": "player-guide.md",
        "output": "Cybermancy_Player_Guide_Content_Prototype.pdf",
        "audiences": {"shared", "player"},
        "parts": [
            "The World of Cybermancy", "Cybermancy Rules",
            "Characters and Character Options", "Equipment and Technology",
        ],
    },
}
APPENDIX_TITLES = [
    "Appendix A — Cybermancy Rules Quick Reference",
    "Appendix B — Entity Index",
    "Appendix C — Attribution and Publication Notice",
]
VERSION_RE = re.compile(r"-v(?P<v>\d+(?:\.\d+)*)(?:-r(?P<r>\d+))?", re.I)
SEMANTIC_PREFIXES = ("section:", "family:", "entity:")
WARNING_PATTERNS = (
    re.compile(r"Overfull \\hbox.*"), re.compile(r"Underfull \\hbox.*"),
    re.compile(r"Missing character:.*"), re.compile(r"LaTeX Warning:.*"),
    re.compile(r"Package .* Warning:.*"),
)

DIRECT_GRAPHICS_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
PILLOW_CONVERT_EXTENSIONS = {".webp", ".gif", ".bmp", ".tif", ".tiff"}

@dataclass
class Paths:
    repo_root: Path
    rulebook_dir: Path
    source_dir: Path
    assembled_dir: Path
    metadata_dir: Path
    manifest_dir: Path
    prototype_dir: Path
    report_dir: Path
    filter_path: Path
    header_path: Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    # Pandoc/LuaLaTeX emit UTF-8. Explicit decoding avoids Windows cp1252
    # reader-thread failures on Unicode output.
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def executable_version(name: str) -> str | None:
    exe = shutil.which(name)
    if not exe:
        return None
    version_args = {"pdfinfo": ["-v"], "pdftotext": ["-v"]}.get(name, ["--version"])
    p = run([exe, *version_args])
    lines = ((p.stdout or "") + "\n" + (p.stderr or "")).splitlines()
    return lines[0] if lines else exe


def version_key(path: Path) -> tuple[tuple[int, ...], int]:
    m = VERSION_RE.search(path.name)
    if not m:
        return ((-1,), -1)
    return (tuple(int(x) for x in m.group("v").split(".")), int(m.group("r") or 0))


def latest_manifest(pattern: str, directory: Path) -> Path | None:
    items = [p for p in directory.glob(pattern) if p.is_file()]
    return max(items, key=version_key) if items else None


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def report_shell(profile: str, paths: Paths) -> dict[str, Any]:
    return {
        "schema": "cybermancy-rulebook-step5-validation-v1.0",
        "profile": profile,
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "errors": [],
        "toolchain": {
            "pandoc": executable_version("pandoc"),
            "lualatex": executable_version("lualatex"),
            "pdfinfo": executable_version("pdfinfo"),
            "pdftotext": executable_version("pdftotext"),
        },
        "paths": {"rulebook": str(paths.rulebook_dir), "repoRoot": str(paths.repo_root)},
    }


def add_check(report: dict[str, Any], code: str, status: str, message: str, details: Any = None) -> None:
    item = {"code": code, "status": status, "message": message}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if status in {"ERROR", "BLOCKED"}:
        report["errors"].append(item)
        report["status"] = "FAIL"
    elif status in {"WARNING", "INFO"}:
        report["warnings"].append(item)


def walk_ast(obj: Any) -> Iterable[dict[str, Any]]:
    if isinstance(obj, dict):
        if "t" in obj:
            yield obj
        for v in obj.values():
            yield from walk_ast(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_ast(v)


def attr_from_node(node: dict[str, Any]) -> tuple[str, list[str], dict[str, str]]:
    c = node.get("c")
    attr = None
    if node.get("t") == "Header" and isinstance(c, list) and len(c) >= 2:
        attr = c[1]
    elif node.get("t") in {"Div", "Span", "CodeBlock"} and isinstance(c, list) and c:
        attr = c[0]
    if not (isinstance(attr, list) and len(attr) == 3):
        return "", [], {}
    identifier = attr[0] or ""
    classes = list(attr[1] or [])
    kv = {str(k): str(v) for k, v in (attr[2] or [])}
    return identifier, classes, kv


def stringify_inlines(inlines: Any) -> str:
    out: list[str] = []
    if isinstance(inlines, list):
        for x in inlines:
            if not isinstance(x, dict):
                continue
            t, c = x.get("t"), x.get("c")
            if t in {"Str", "Code"}:
                if t == "Code" and isinstance(c, list): out.append(str(c[-1]))
                else: out.append(str(c))
            elif t in {"Space", "SoftBreak", "LineBreak"}: out.append(" ")
            elif isinstance(c, (list, dict)): out.append(stringify_inlines(c))
    elif isinstance(inlines, dict):
        out.append(stringify_inlines(inlines.get("c")))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def profile_expected_targets(metadata: list[dict[str, Any]], profile: str) -> tuple[set[str], set[str]]:
    allowed = PROFILE_CONFIG[profile]["audiences"]
    families, entities = set(), set()
    for item in metadata or []:
        if item.get("audience") not in allowed:
            continue
        sid = item.get("semanticId", "")
        if item.get("kind") == "family" or sid.startswith("family:"):
            families.add(sid)
        elif item.get("kind") == "entity" or sid.startswith("entity:"):
            entities.add(sid)
    return families, entities


def resolve_image(source: str, paths: Paths, input_path: Path) -> Path | None:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", source):
        return Path("/__external__")
    candidates = [
        (input_path.parent / source), (paths.source_dir / source),
        (paths.source_dir / "assets" / source), (paths.repo_root / source),
        (paths.rulebook_dir / source),
    ]
    for c in candidates:
        try:
            if c.resolve().exists(): return c.resolve()
        except OSError:
            continue
    return None


def is_external_image(source: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", source))


def render_asset_relative_path(resolved: Path, paths: Paths) -> Path:
    """Return a stable publication-relative path for a resolved local asset."""
    roots = [paths.source_dir / "assets", paths.source_dir]
    for root in roots:
        try:
            return resolved.relative_to(root.resolve())
        except ValueError:
            pass
    # Step 4 should normally stage publication assets under source/assets. If a
    # local asset resolves elsewhere, isolate it deterministically by source hash
    # rather than leaking host-specific absolute paths into the render tree.
    return Path("_external-local") / f"{sha256_file(resolved)[:16]}-{resolved.name}"


def convert_raster_to_png(source: Path, destination: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required to convert WebP/GIF/BMP/TIFF assets for LuaLaTeX. "
            "Install it with: python -m pip install Pillow"
        ) from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im)
        has_alpha = "A" in im.getbands() or (im.mode == "P" and "transparency" in im.info)
        prepared = im.convert("RGBA" if has_alpha else "RGB")
        # Fixed options and no copied metadata keep render assets deterministic.
        prepared.save(destination, format="PNG", compress_level=9, optimize=False)
        width, height = prepared.size
    return {
        "source": str(source),
        "sourceSha256": sha256_file(source),
        "render": str(destination),
        "renderSha256": sha256_file(destination),
        "width": width,
        "height": height,
    }


def prepare_render_ast(ast: dict[str, Any], ast_images: list[str], profile: str,
                       paths: Paths, input_path: Path, report: dict[str, Any]) -> tuple[dict[str, Any] | None, Path | None]:
    """Prepare a LuaLaTeX-safe AST and deterministic render asset tree.

    Step 4 remains untouched. Local WebP/GIF/BMP/TIFF images are converted to
    PNG under build/rulebook/prototype/_render-assets/<profile>/ and only the
    Step 5 render AST is rewritten to point at those derived assets.
    """
    render_root = paths.prototype_dir / "_render-assets" / profile
    if render_root.exists():
        shutil.rmtree(render_root)
    render_root.mkdir(parents=True, exist_ok=True)

    mapping: dict[str, str] = {}
    converted: list[dict[str, Any]] = []
    direct: list[dict[str, Any]] = []
    external: list[str] = []
    unsupported: list[dict[str, str]] = []
    missing: list[str] = []

    for source in ast_images:
        if source in mapping:
            continue
        if is_external_image(source):
            external.append(source)
            mapping[source] = source
            continue
        resolved = resolve_image(source, paths, input_path)
        if resolved is None or str(resolved) == "/__external__":
            missing.append(source)
            continue
        ext = resolved.suffix.lower()
        if ext in DIRECT_GRAPHICS_EXTENSIONS:
            mapping[source] = resolved.as_posix()
            direct.append({
                "source": source,
                "resolved": str(resolved),
                "sha256": sha256_file(resolved),
                "extension": ext,
            })
            continue
        if ext in PILLOW_CONVERT_EXTENSIONS:
            rel = render_asset_relative_path(resolved, paths).with_suffix(".png")
            destination = render_root / rel
            try:
                record = convert_raster_to_png(resolved, destination)
            except Exception as exc:
                unsupported.append({"source": source, "resolved": str(resolved), "error": str(exc)})
                continue
            record["reference"] = source
            record["sourceExtension"] = ext
            converted.append(record)
            mapping[source] = destination.as_posix()
            continue
        unsupported.append({
            "source": source,
            "resolved": str(resolved),
            "error": f"Unsupported LuaLaTeX graphics extension: {ext or '<none>'}",
        })

    failures = missing or unsupported
    details = {
        "imageReferences": len(ast_images),
        "uniqueImageReferences": len(set(ast_images)),
        "direct": len(direct),
        "converted": len(converted),
        "external": len(external),
        "missing": missing,
        "unsupported": unsupported,
        "renderRoot": str(render_root),
        "convertedAssets": converted,
    }
    add_check(
        report,
        "RENDER_ASSET_PREPARATION",
        "ERROR" if failures else "PASS",
        (f"Render asset preparation failed: {len(missing)} missing, {len(unsupported)} unsupported/conversion failures."
         if failures else f"Prepared {len(converted)} converted render assets; {len(direct)} local assets are directly LuaLaTeX-compatible."),
        details,
    )
    expected = len(set(ast_images))
    reconciled = len(mapping) == expected and not failures
    add_check(
        report,
        "RENDER_ASSET_RECONCILIATION",
        "ERROR" if not reconciled else "PASS",
        f"{len(mapping)} of {expected} unique AST image references have render targets.",
    )
    if not reconciled:
        return None, render_root

    render_ast = copy.deepcopy(ast)
    rewritten = 0
    for node in walk_ast(render_ast):
        if node.get("t") != "Image":
            continue
        c = node.get("c", [])
        if not (isinstance(c, list) and len(c) >= 3 and isinstance(c[2], list) and c[2]):
            continue
        source = c[2][0]
        if source in mapping:
            target = mapping[source]
            if target != source:
                rewritten += 1
            c[2][0] = target
    report["renderAssets"] = {
        "root": str(render_root),
        "rewrittenImageNodes": rewritten,
        "convertedCount": len(converted),
        "directCount": len(direct),
        "externalCount": len(external),
    }
    return render_ast, render_root


def ast_validate(ast: dict[str, Any], source_text: str, profile: str, paths: Paths,
                 input_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    ids: list[str] = []
    headings: list[tuple[int, str, str, list[str], dict[str, str]]] = []
    internal_links: list[str] = []
    images: list[str] = []
    raw_html = 0
    gm_nodes = 0
    fast_play = 0
    for node in walk_ast(ast):
        t = node.get("t")
        identifier, classes, kv = attr_from_node(node)
        if identifier:
            ids.append(identifier)
        if kv.get("data-audience") == "gm": gm_nodes += 1
        if any("fast-play" in c.lower() for c in classes): fast_play += 1
        if t == "Header":
            c = node.get("c", [])
            headings.append((int(c[0]), stringify_inlines(c[2]), identifier, classes, kv))
        elif t == "Link":
            c = node.get("c", [])
            if isinstance(c, list) and len(c) >= 3 and isinstance(c[2], list):
                target = c[2][0]
                if isinstance(target, str) and target.startswith("#"):
                    internal_links.append(target[1:])
        elif t == "Image":
            c = node.get("c", [])
            if isinstance(c, list) and len(c) >= 3 and isinstance(c[2], list): images.append(c[2][0])
        elif t in {"RawBlock", "RawInline"}:
            c = node.get("c", [])
            if isinstance(c, list) and c and str(c[0]).lower() in {"html", "html5"}: raw_html += 1

    dupes = sorted({x for x in ids if ids.count(x) > 1})
    add_check(report, "AST_SEMANTIC_ID_UNIQUENESS", "ERROR" if dupes else "PASS",
              f"{len(dupes)} duplicate AST IDs." if dupes else f"{len(ids)} AST identifiers are unique.", dupes[:100] if dupes else None)
    bad_sem = sorted({x for x in ids if ":" in x and not x.startswith(SEMANTIC_PREFIXES)})
    if bad_sem:
        add_check(report, "AST_SEMANTIC_ID_FORMS", "WARNING", "Colon-bearing IDs outside canonical semantic forms detected.", bad_sem[:100])
    else:
        add_check(report, "AST_SEMANTIC_ID_FORMS", "PASS", "Semantic IDs use accepted prefixes.")

    broken = sorted(set(internal_links) - set(ids))
    add_check(report, "INTERNAL_REFERENCES", "ERROR" if broken else "PASS",
              f"{len(broken)} internal targets are unresolved." if broken else f"{len(internal_links)} internal PDF-link candidates resolve in the AST.", broken[:100] if broken else None)

    add_check(report, "RAW_HTML_AST", "ERROR" if raw_html else "PASS",
              f"{raw_html} raw HTML AST nodes remain; classify as Step 4 normalization defects." if raw_html else "No raw HTML remains in the Pandoc AST.")

    # Architecture order.
    heading_texts = [h[1] for h in headings]
    positions = []
    missing_parts = []
    for part in PROFILE_CONFIG[profile]["parts"]:
        try: positions.append(heading_texts.index(part))
        except ValueError: missing_parts.append(part)
    ordered = not missing_parts and positions == sorted(positions)
    add_check(report, "PART_ARCHITECTURE", "PASS" if ordered else "ERROR",
              "Required parts occur in approved order." if ordered else "Required part hierarchy is missing or out of order.", {"missing": missing_parts, "positions": positions})

    divider_count = source_text.count(GM_DIVIDER)
    if profile == "complete-rulebook":
        add_check(report, "GM_DIVIDER", "PASS" if divider_count == 1 else "ERROR", f"Complete Rulebook contains GM divider {divider_count} time(s).")
    else:
        leaked = divider_count > 0 or gm_nodes > 0 or 'data-audience="gm"' in source_text
        add_check(report, "PLAYER_AUDIENCE_ISOLATION", "ERROR" if leaked else "PASS",
                  "Player Guide contains GM material." if leaked else "Player Guide contains no GM divider or GM-audience nodes.")

    # Fast Play must remain a distinct GM-only structure. Accommodate exact class differences by text fallback.
    fast_text = len(re.findall(r"fast[ -]?play", source_text, flags=re.I))
    if profile == "complete-rulebook":
        status = "PASS" if (fast_play or fast_text) else "WARNING"
        add_check(report, "FAST_PLAY", status, f"Fast Play markers: AST divs={fast_play}, textual markers={fast_text}.")
    else:
        leaked_fp = bool(fast_play or fast_text)
        add_check(report, "FAST_PLAY_PLAYER_EXCLUSION", "ERROR" if leaked_fp else "PASS",
                  "Fast Play appears in Player Guide." if leaked_fp else "No Fast Play markers in Player Guide.")

    # Family/entity reconciliation against Step 4 metadata when available.
    targets = load_json(paths.metadata_dir / "semantic-targets.json", [])
    expected_families, expected_entities = profile_expected_targets(targets, profile)
    found_families = {x for x in ids if x.startswith("family:")}
    found_entities = {x for x in ids if x.startswith("entity:")}
    if targets:
        fam_missing = sorted(expected_families - found_families)
        ent_missing = sorted(expected_entities - found_entities)
        add_check(report, "STRUCTURED_FAMILY_RECONCILIATION", "ERROR" if fam_missing else "PASS",
                  f"{len(found_families)} families present; {len(expected_families)} expected for profile.", fam_missing[:100] if fam_missing else None)
        add_check(report, "STRUCTURED_ENTITY_RECONCILIATION", "ERROR" if ent_missing or len(found_entities) != len(expected_entities) else "PASS",
                  f"{len(found_entities)} entities present; {len(expected_entities)} expected for profile.", ent_missing[:100] if ent_missing else None)
    else:
        add_check(report, "STRUCTURED_RECONCILIATION_BASELINE", "WARNING", "Step 4 semantic-targets.json unavailable; family/entity totals cannot be authoritatively reconciled.")

    # Appendices are reserved; absence is diagnostic, not fabrication.
    present_appendices = [t for t in APPENDIX_TITLES if any(t in h for h in heading_texts)]
    if len(present_appendices) == len(APPENDIX_TITLES):
        add_check(report, "APPENDICES", "PASS", "All three approved appendices are materialized.")
    else:
        add_check(report, "APPENDICES", "INFO", "Reserved appendices not all materialized; no missing content was invented.", {"present": present_appendices, "reserved": APPENDIX_TITLES})

    # Asset existence.
    missing_images = []
    for src in images:
        resolved = resolve_image(src, paths, input_path)
        if resolved is None: missing_images.append(src)
    add_check(report, "AST_ASSETS", "ERROR" if missing_images else "PASS",
              f"{len(missing_images)} image references could not be resolved." if missing_images else f"{len(images)} AST image references resolve or are external.", missing_images[:100] if missing_images else None)

    return {"ids": ids, "headings": headings, "images": images, "fastPlayDivs": fast_play}


def parse_pdfinfo(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1); out[k.strip()] = v.strip()
    return out


def pdf_validate(pdf_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        add_check(report, "PDF_EXISTS", "ERROR", f"PDF missing or empty: {pdf_path}")
        return {}
    add_check(report, "PDF_EXISTS", "PASS", f"PDF exists ({pdf_path.stat().st_size} bytes).")
    pdfinfo = shutil.which("pdfinfo")
    pdftotext = shutil.which("pdftotext")
    info: dict[str, str] = {}
    if pdfinfo:
        p = run([pdfinfo, str(pdf_path)])
        if p.returncode != 0:
            add_check(report, "PDF_OPEN", "ERROR", p.stderr.strip())
        else:
            info = parse_pdfinfo(p.stdout)
            add_check(report, "PDF_OPEN", "PASS", "pdfinfo opens the rendered PDF.")
            pages = int(info.get("Pages", "0") or 0)
            add_check(report, "PDF_PAGE_COUNT", "PASS" if pages > 0 else "ERROR", f"Rendered PDF has {pages} pages.")
            size = info.get("Page size", "")
            is_letter = "612 x 792" in size or "letter" in size.lower()
            add_check(report, "PDF_PAGE_SIZE", "PASS" if is_letter else "ERROR", f"Page size: {size or 'unknown'}")
    if pdftotext:
        with tempfile.TemporaryDirectory(prefix="rb-step5-text-") as td:
            txt = Path(td) / "out.txt"
            p = run([pdftotext, "-layout", str(pdf_path), str(txt)])
            if p.returncode == 0 and txt.exists():
                text = txt.read_text(encoding="utf-8", errors="replace")
                pages = text.split("\f")
                page_list = pages[:-1] if pages and pages[-1] == "" else pages
                near_empty = [
                    i + 1 for i, pg in enumerate(page_list)
                    if len(re.sub(r"\s+", "", pg)) < 40 and GM_DIVIDER not in pg
                ]
                intentional_divider_pages = [i + 1 for i, pg in enumerate(page_list) if GM_DIVIDER in pg]
                malformed = text.count("�")
                add_check(report, "PDF_TEXT_EXTRACTION", "PASS", f"Extracted {len(text)} characters from PDF.")
                add_check(report, "PDF_NEAR_EMPTY_PAGES", "WARNING" if near_empty else "PASS", f"{len(near_empty)} unexpected near-empty pages detected.", near_empty[:100] if near_empty else None)
                if intentional_divider_pages:
                    add_check(report, "PDF_GM_DIVIDER_PAGE", "PASS", f"GM divider rendered on dedicated page(s): {intentional_divider_pages}.")
                add_check(report, "PDF_MALFORMED_GLYPHS", "WARNING" if malformed else "PASS", f"Replacement glyph count: {malformed}.")
                return {"pdfInfo": info, "textSha256": sha256_bytes(text.encode("utf-8")), "nearEmptyPages": near_empty, "malformedGlyphs": malformed}
            add_check(report, "PDF_TEXT_EXTRACTION", "WARNING", "pdftotext could not extract rendered text.")
    return {"pdfInfo": info}


def warning_lines(stderr: str) -> list[str]:
    out: list[str] = []
    for line in stderr.splitlines():
        if any(p.search(line) for p in WARNING_PATTERNS):
            out.append(line.strip())
    return out


def make_paths(args: argparse.Namespace) -> Paths:
    rulebook = Path(args.rulebook_dir).resolve() if args.rulebook_dir else RULEBOOK_DIR
    repo_root = Path(args.repo_root).resolve() if args.repo_root else rulebook.parent.parent
    return Paths(repo_root, rulebook, rulebook / "source", rulebook / "source" / "assembled",
                 rulebook / "source" / "metadata", rulebook / "manifests", rulebook / "prototype",
                 rulebook / "reports", rulebook / "pandoc" / "filters" / "prototype.lua",
                 rulebook / "pandoc" / "templates" / "prototype-header.tex")


def validate_step4_input(profile: str, paths: Paths, report: dict[str, Any], allow_unvalidated: bool) -> Path | None:
    input_path = paths.assembled_dir / PROFILE_CONFIG[profile]["input"]
    add_check(report, "STEP4_PROFILE_SOURCE", "PASS" if input_path.exists() else "BLOCKED", str(input_path))
    val_path = paths.metadata_dir / "validation.json"
    validation = load_json(val_path, None)
    if validation is None:
        add_check(report, "STEP4_VALIDATION", "WARNING" if allow_unvalidated else "BLOCKED", "Step 4 validation.json is unavailable.")
    else:
        status = validation.get("status")
        ok = status == "PASS"
        add_check(report, "STEP4_VALIDATION", "PASS" if ok else ("WARNING" if allow_unvalidated else "BLOCKED"), f"Step 4 validation status: {status}.")
    for tool in ("pandoc", "lualatex"):
        add_check(report, f"TOOL_{tool.upper()}", "PASS" if shutil.which(tool) else "BLOCKED", executable_version(tool) or f"{tool} not found")
    for p, code in ((paths.filter_path, "PANDOC_FILTER"), (paths.header_path, "LATEX_HEADER")):
        add_check(report, code, "PASS" if p.exists() else "BLOCKED", str(p))
    if report["status"] != "PASS" and not allow_unvalidated:
        return None
    return input_path if input_path.exists() else None


def build_one(profile: str, paths: Paths, allow_unvalidated: bool = False,
              output_override: Path | None = None, write_report: bool = True) -> tuple[dict[str, Any], Path | None]:
    report = report_shell(profile, paths)
    input_path = validate_step4_input(profile, paths, report, allow_unvalidated)
    if not input_path:
        if write_report:
            write_reports(report, paths, profile)
        return report, None
    source_text = input_path.read_text(encoding="utf-8")

    # AST compatibility pass is intentionally independent of LaTeX transformations.
    ast_cmd = ["pandoc", str(input_path), "--from", MARKDOWN_FROM, "--to", "json"]
    ast_run = run(ast_cmd, cwd=paths.repo_root)
    if ast_run.returncode != 0:
        add_check(report, "PANDOC_AST", "ERROR", "Pandoc failed to parse Step 4 Markdown.", (ast_run.stderr or "")[-8000:])
        if write_report:
            write_reports(report, paths, profile)
        return report, None
    add_check(report, "PANDOC_AST", "PASS", "Normalized manuscript parses into a Pandoc AST.")
    if not ast_run.stdout:
        add_check(report, "PANDOC_AST_JSON", "ERROR", "Pandoc returned no AST output despite completing the command.", (ast_run.stderr or "")[-8000:])
        if write_report:
            write_reports(report, paths, profile)
        return report, None
    try:
        ast = json.loads(ast_run.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        add_check(report, "PANDOC_AST_JSON", "ERROR", f"Pandoc AST JSON is invalid: {exc}")
        if write_report:
            write_reports(report, paths, profile)
        return report, None

    ast_summary = ast_validate(ast, source_text, profile, paths, input_path, report)
    report["ast"] = {
        "sha256": sha256_bytes(ast_run.stdout.encode("utf-8")),
        "summary": {
            "identifierCount": len(ast_summary["ids"]),
            "imageCount": len(ast_summary["images"]),
            "fastPlayDivCount": ast_summary["fastPlayDivs"],
        },
    }

    # Build a Step 5-only render AST. This is where unsupported source image
    # formats (notably WebP) are deterministically converted for LuaLaTeX.
    render_ast, render_root = prepare_render_ast(
        ast, ast_summary["images"], profile, paths, input_path, report
    )
    if render_ast is None:
        if write_report:
            write_reports(report, paths, profile)
        return report, None

    outdir = output_override.parent if output_override else paths.prototype_dir / profile
    outdir.mkdir(parents=True, exist_ok=True)
    pdf = output_override or (outdir / PROFILE_CONFIG[profile]["output"])
    log_path = outdir / "pandoc-lualatex.log"
    render_dir = outdir / "_render"
    render_dir.mkdir(parents=True, exist_ok=True)
    render_ast_path = render_dir / "render-input.ast.json"
    render_ast_text = json.dumps(render_ast, ensure_ascii=False, separators=(",", ":")) + "\n"
    render_ast_path.write_text(render_ast_text, encoding="utf-8")
    report["renderAst"] = {
        "path": str(render_ast_path),
        "sha256": sha256_bytes(render_ast_text.encode("utf-8")),
    }

    # A failed current render must never leave an old PDF to be mistaken for the
    # result of this run.
    if pdf.exists():
        pdf.unlink()
    if log_path.exists():
        log_path.unlink()

    resource_candidates = [input_path.parent, paths.source_dir, paths.source_dir / "assets", paths.repo_root]
    if render_root is not None:
        resource_candidates.insert(0, render_root)
    resource_path = os.pathsep.join(str(x) for x in resource_candidates)
    cmd = [
        "pandoc", str(render_ast_path), "--from", "json", "--standalone", "--toc", "--toc-depth=2",
        "--pdf-engine=lualatex", f"--lua-filter={paths.filter_path}", f"--include-in-header={paths.header_path}",
        "-V", "papersize=letter", "-V", "geometry:margin=0.75in", "-V", "fontsize=10pt", "-V", "colorlinks=true",
        f"--resource-path={resource_path}", "--output", str(pdf),
    ]
    rendered = run(cmd, cwd=paths.repo_root)
    log_path.write_text(
        (rendered.stdout or "") + "\n--- STDERR ---\n" + (rendered.stderr or ""),
        encoding="utf-8",
    )
    report["pandocCommand"] = cmd
    if rendered.returncode != 0:
        add_check(
            report,
            "PANDOC_LUALATEX",
            "ERROR",
            f"Pandoc/LuaLaTeX exited {rendered.returncode}.",
            (rendered.stderr or "")[-12000:],
        )
    else:
        add_check(report, "PANDOC_LUALATEX", "PASS", "Pandoc/LuaLaTeX completed successfully.")

    warns = warning_lines(rendered.stderr or "")
    add_check(
        report,
        "LATEX_WARNINGS",
        "WARNING" if warns else "PASS",
        f"{len(warns)} diagnostic LaTeX warning lines captured.",
        warns[:200] if warns else None,
    )

    if rendered.returncode != 0:
        # No PDF checks after a failed current render; any prior PDF was removed.
        report["pdf"] = {}
        add_check(report, "PDF_VALIDATION_SKIPPED", "INFO", "PDF validation skipped because the current Pandoc/LuaLaTeX render failed.")
        if write_report:
            write_reports(report, paths, profile)
        return report, None

    report["pdf"] = pdf_validate(pdf, report)
    if pdf.exists():
        report["pdf"]["sha256"] = sha256_file(pdf)
    if write_report:
        write_reports(report, paths, profile)
    return report, pdf if pdf.exists() else None


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Step 5 Validation - {report['profile']}", "", f"**Status:** {report['status']}", "",
        "## Checks", "", "| Check | Status | Result |", "|---|---|---|",
    ]
    for c in report["checks"]:
        msg = str(c.get("message", "")).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{c['code']}` | **{c['status']}** | {msg} |")

    def append_items(title: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        lines.extend(["", title, ""])
        for item in items:
            lines.append(f"- `{item['code']}` - {item['message']}")
            details = item.get("details")
            if details is not None:
                rendered = details if isinstance(details, str) else json.dumps(details, indent=2, ensure_ascii=False)
                lines.extend(["", "```text", rendered.rstrip(), "```", ""])

    append_items("## Blocking defects", report.get("errors", []))
    append_items("## Diagnostics", report.get("warnings", []))
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], paths: Paths, profile: str) -> None:
    paths.report_dir.mkdir(parents=True, exist_ok=True)
    (paths.report_dir / f"step5-{profile}-validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (paths.report_dir / f"step5-{profile}-validation.md").write_text(markdown_report(report), encoding="utf-8")


def repro_one(profile: str, paths: Paths, allow_unvalidated: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="rb-step5-repro-") as td:
        base = Path(td)
        r1, p1 = build_one(profile, paths, allow_unvalidated, base / "a" / PROFILE_CONFIG[profile]["output"], write_report=False)
        r2, p2 = build_one(profile, paths, allow_unvalidated, base / "b" / PROFILE_CONFIG[profile]["output"], write_report=False)
        result = {"profile": profile, "status": "PASS", "astEquivalent": False, "textEquivalent": False, "pdfByteEquivalent": False}
        if r1["status"] != "PASS" or r2["status"] != "PASS" or not p1 or not p2:
            result["status"] = "FAIL"; result["reason"] = "One or both rebuilds failed validation."; return result
        result["astEquivalent"] = r1.get("ast", {}).get("sha256") == r2.get("ast", {}).get("sha256")
        result["textEquivalent"] = r1.get("pdf", {}).get("textSha256") == r2.get("pdf", {}).get("textSha256")
        result["pdfByteEquivalent"] = sha256_file(p1) == sha256_file(p2)
        if not (result["astEquivalent"] and result["textEquivalent"]): result["status"] = "FAIL"
        return result


def profile_list(value: str) -> list[str]:
    return list(PROFILE_CONFIG) if value == "all" else [value]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"build", "validate", "repro-check", "--help", "-h"}:
        argv.insert(0, "build")
    elif not argv:
        argv = ["build", "--profile", "all"]
    parser = argparse.ArgumentParser(description="Cybermancy Rulebook Step 5 content-only PDF builder")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "validate", "repro-check"):
        p = sub.add_parser(name)
        p.add_argument("--profile", choices=[*PROFILE_CONFIG, "all"], default="all")
        p.add_argument("--rulebook-dir", help="Override build/rulebook directory (used by smoke/regression fixtures).")
        p.add_argument("--repo-root", help="Override repository root.")
        p.add_argument("--allow-unvalidated-source", action="store_true", help="Diagnostic only: permit missing/non-PASS Step 4 validation baseline.")
    args = parser.parse_args(argv)
    paths = make_paths(args)
    profiles = profile_list(args.profile)
    overall = 0
    if args.command in {"build", "validate"}:
        for profile in profiles:
            report, pdf = build_one(profile, paths, args.allow_unvalidated_source)
            if args.command == "validate" and pdf and report["status"] == "PASS":
                # validate intentionally re-renders: PDF is a pipeline product and must be inspected against current source.
                pass
            print(f"{profile}: {report['status']}" + (f" -> {pdf}" if pdf else ""))
            if report["status"] != "PASS": overall = 2
    else:
        paths.report_dir.mkdir(parents=True, exist_ok=True)
        results = [repro_one(p, paths, args.allow_unvalidated_source) for p in profiles]
        out = {"schema": "cybermancy-rulebook-step5-repro-v1.0", "status": "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL", "profiles": results,
               "interpretation": "AST and extracted PDF text must match. PDF byte equality is informational because metadata/timestamps may differ."}
        (paths.report_dir / "step5-reproducibility.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2))
        if out["status"] != "PASS": overall = 2
    return overall

if __name__ == "__main__":
    raise SystemExit(main())
