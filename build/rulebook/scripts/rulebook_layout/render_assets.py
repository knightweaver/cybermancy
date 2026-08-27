from __future__ import annotations

import hashlib
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


DIRECT_GRAPHICS_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
PILLOW_CONVERT_EXTENSIONS = {".webp", ".gif", ".bmp", ".tif", ".tiff"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_path(source_root: Path, publication_path: str) -> Path:
    pure = PurePosixPath(publication_path)
    return source_root / Path(*pure.parts)


def _convert_raster_to_png(source: Path, destination: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required to convert WebP/GIF/BMP/TIFF publication assets for LuaLaTeX. "
            "Install it with: python -m pip install Pillow"
        ) from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        has_alpha = "A" in image.getbands() or (
            image.mode == "P" and "transparency" in image.info
        )
        prepared = image.convert("RGBA" if has_alpha else "RGB")
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


def prepare_lualatex_render_assets(
    publication_paths: Iterable[str],
    source_root: Path,
    render_root: Path,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Prepare normalized Step 4 publication images for LuaLaTeX.

    Directly supported PNG/JPEG/PDF files remain in the Step 4 staged tree.
    WebP/GIF/BMP/TIFF files are deterministically converted to PNG under the
    caller-owned render root. The returned mapping never mutates Step 4 assets.
    """
    source_root = Path(source_root).resolve()
    render_root = Path(render_root).resolve()
    if render_root.exists():
        shutil.rmtree(render_root)
    render_root.mkdir(parents=True, exist_ok=True)

    references = sorted(
        {
            str(value or "").strip().replace("\\", "/")
            for value in publication_paths
            if str(value or "").strip()
        }
    )
    mapping: dict[str, str] = {}
    direct: list[dict[str, Any]] = []
    converted: list[dict[str, Any]] = []
    missing: list[str] = []
    unsupported: list[dict[str, str]] = []

    for reference in references:
        source = _source_path(source_root, reference)
        if not source.is_file():
            missing.append(reference)
            continue
        ext = source.suffix.casefold()
        if ext in DIRECT_GRAPHICS_EXTENSIONS:
            mapping[reference] = str(source)
            direct.append(
                {
                    "reference": reference,
                    "source": str(source),
                    "sha256": sha256_file(source),
                    "extension": ext,
                }
            )
            continue
        if ext in PILLOW_CONVERT_EXTENSIONS:
            destination = render_root / Path(
                *PurePosixPath(reference).with_suffix(".png").parts
            )
            try:
                record = _convert_raster_to_png(source, destination)
            except Exception as exc:
                unsupported.append(
                    {
                        "reference": reference,
                        "source": str(source),
                        "error": str(exc),
                    }
                )
                continue
            record["reference"] = reference
            record["sourceExtension"] = ext
            converted.append(record)
            mapping[reference] = str(destination)
            continue
        unsupported.append(
            {
                "reference": reference,
                "source": str(source),
                "error": f"Unsupported LuaLaTeX graphics extension: {ext or '<none>'}",
            }
        )

    failures = bool(missing or unsupported)
    details = {
        "status": "FAIL" if failures else "PASS",
        "references": len(references),
        "direct": len(direct),
        "converted": len(converted),
        "missing": missing,
        "unsupported": unsupported,
        "renderRoot": str(render_root),
        "convertedAssets": converted,
        "directAssets": direct,
    }
    return mapping, details
