from __future__ import annotations

GM_DIVIDER = "GM MATERIAL — SPOILERS BEYOND THIS POINT"

def assemble_profile(section_fragments: list[dict], profile: str) -> str:
    """
    Expects fragments already sorted by authoritative assembly-manifest order.
    This function never sorts them itself.
    Each item: {semanticId,title,audience,markdown}
    """
    if profile not in {"complete-rulebook", "player-guide"}:
        raise ValueError(f"Unknown profile: {profile}")
    chunks = []
    inserted_gm_divider = False
    for item in section_fragments:
        audience = item["audience"]
        if profile == "player-guide" and audience == "gm":
            continue
        if profile == "complete-rulebook" and audience == "gm" and not inserted_gm_divider:
            chunks += [f"# {GM_DIVIDER} {{#section:gm-material-divider .gm-divider data-audience=\"gm\"}}", ""]
            inserted_gm_divider = True
        chunks += [item["markdown"].rstrip(), ""]
    out = "\n".join(chunks).rstrip() + "\n"
    if profile == "player-guide" and GM_DIVIDER in out:
        raise AssertionError("Player guide contains GM divider")
    return out
