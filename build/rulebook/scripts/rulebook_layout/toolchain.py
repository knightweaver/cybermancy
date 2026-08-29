from __future__ import annotations

import os
import shutil
from pathlib import Path


_TOOL_CACHE: dict[str, str | None] = {}


def _is_windows() -> bool:
    return os.name == "nt"


def clear_tool_cache() -> None:
    """Clear cached executable resolutions; primarily useful to isolated tests."""
    _TOOL_CACHE.clear()


def _windows_app_path(name: str) -> str | None:
    """Resolve an executable through Windows App Paths when available."""
    if not _is_windows():
        return None
    try:
        import winreg
    except ImportError:
        return None

    exe_name = name if name.lower().endswith(".exe") else f"{name}.exe"
    subkey = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access in (
            getattr(winreg, "KEY_WOW64_64KEY", 0),
            getattr(winreg, "KEY_WOW64_32KEY", 0),
            0,
        ):
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | access) as key:
                    value, _ = winreg.QueryValueEx(key, None)
            except OSError:
                continue
            candidate = Path(str(value).strip('"')).expanduser()
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def _windows_tool_candidates(name: str) -> list[Path]:
    """Return common per-user/system install locations for Windows CLI tools."""
    if not _is_windows():
        return []

    exe = name if name.lower().endswith(".exe") else f"{name}.exe"
    env = os.environ
    roots: list[Path] = []
    for key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        value = env.get(key)
        if value:
            roots.append(Path(value))

    candidates: list[Path] = []
    local = env.get("LOCALAPPDATA")
    if local:
        local_root = Path(local)
        candidates.extend(
            [
                local_root / "Pandoc" / exe,
                local_root / "Programs" / "Pandoc" / exe,
                local_root / "Microsoft" / "WinGet" / "Links" / exe,
            ]
        )
    for root in roots:
        candidates.extend(
            [
                root / "Pandoc" / exe,
                root / "MiKTeX" / "miktex" / "bin" / "x64" / exe,
                root / "MiKTeX" / "miktex" / "bin" / exe,
            ]
        )
    return candidates


def resolve_tool(name: str) -> str | None:
    """Resolve a production tool without requiring a freshly updated Windows PATH.

    Resolution order is explicit Cybermancy environment override, current PATH,
    Windows App Paths, then common Pandoc/MiKTeX/WinGet install locations.
    """
    key = name.lower()
    if key in _TOOL_CACHE:
        return _TOOL_CACHE[key]

    env_override = os.environ.get(f"CYBERMANCY_{key.upper()}_PATH")
    if env_override:
        candidate = Path(env_override).expanduser()
        if candidate.is_file():
            _TOOL_CACHE[key] = str(candidate.resolve())
            return _TOOL_CACHE[key]

    found = shutil.which(name)
    if found:
        _TOOL_CACHE[key] = found
        return found

    app_path = _windows_app_path(name)
    if app_path:
        _TOOL_CACHE[key] = app_path
        return app_path

    for candidate in _windows_tool_candidates(name):
        if candidate.is_file():
            _TOOL_CACHE[key] = str(candidate.resolve())
            return _TOOL_CACHE[key]

    _TOOL_CACHE[key] = None
    return None
