from __future__ import annotations

import re

from .markdown import html_to_markdown


_DETACHED_LIST_MARKER_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)(?P<marker>(?:[-*+]|\d+\.))[ \t]*\n+(?P<body>[^\n])"
)
_LIST_ITEM_LINE_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+\S")


def repair_detached_list_markers(markdown: str) -> str:
    """Repair paragraph-wrapped HTML list items after generic HTML conversion.

    Foundry often serializes list entries as ``<li><p>...</p></li>``. The
    generic converter correctly emits the list marker for ``li`` and paragraph
    boundaries for ``p``, but that combination can leave publication Markdown
    as ``-\n\nItem``. This helper repairs only that deterministic structural
    artifact and then removes blank lines *between adjacent list-item lines* so
    nested list indentation remains explicit.

    It does not rewrite prose, labels, list ordering, or emphasis.
    """
    text = str(markdown or "").replace("\r\n", "\n").replace("\r", "\n")

    previous = None
    while previous != text:
        previous = text
        text = _DETACHED_LIST_MARKER_RE.sub(
            lambda match: (
                f"{match.group('indent')}{match.group('marker')} "
                f"{match.group('body')}"
            ),
            text,
        )

    lines = text.split("\n")
    out: list[str] = []
    for index, line in enumerate(lines):
        if line.strip():
            out.append(line.rstrip())
            continue

        previous_line = out[-1] if out else ""
        next_line = ""
        for candidate in lines[index + 1 :]:
            if candidate.strip():
                next_line = candidate
                break

        # Markdown permits blank lines inside lists, but the Step 6 ICE renderer
        # intentionally uses compact lists. Remove only the converter-generated
        # blank line separating consecutive list-item lines. Ordinary paragraph
        # boundaries remain untouched.
        if _LIST_ITEM_LINE_RE.match(previous_line) and _LIST_ITEM_LINE_RE.match(next_line):
            continue
        out.append("")

    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def html_to_publication_markdown(value: str) -> str:
    """Convert Foundry HTML to reader-facing Markdown with stable list structure."""
    return repair_detached_list_markers(html_to_markdown(str(value or "")))
