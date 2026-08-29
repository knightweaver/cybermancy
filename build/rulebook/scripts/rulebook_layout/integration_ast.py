from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from typing import Any


def iter_ast_nodes(value: Any) -> Iterator[dict[str, Any]]:
    """Yield Pandoc nodes in document order."""
    if isinstance(value, dict):
        if isinstance(value.get("t"), str):
            yield value
        for child in value.values():
            yield from iter_ast_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_ast_nodes(child)


def normalize_identifier(value: str) -> str:
    """Normalize Pandoc identifiers without changing their semantic namespace."""
    return str(value or "").replace(r"\:", ":").strip()


def canonical_chapter_id(value: str) -> str:
    ident = normalize_identifier(value)
    if ident.startswith("section:"):
        ident = ident[len("section:") :]
    return ident


def node_attr(node: dict[str, Any]) -> list[Any] | None:
    """Return Pandoc Attr [identifier, classes, keyvals] for common block nodes."""
    kind = node.get("t")
    content = node.get("c")
    if not isinstance(content, list):
        return None

    if kind == "Header" and len(content) >= 2:
        attr = content[1]
    elif kind in {"Div", "Span"} and len(content) >= 1:
        attr = content[0]
    else:
        return None

    if isinstance(attr, list) and len(attr) == 3:
        return attr
    return None


def node_identifier(node: dict[str, Any]) -> str:
    attr = node_attr(node)
    if attr is None:
        return ""
    return normalize_identifier(str(attr[0] or ""))


def node_classes(node: dict[str, Any]) -> list[str]:
    attr = node_attr(node)
    if attr is None or not isinstance(attr[1], list):
        return []
    return [str(item) for item in attr[1]]


def node_attributes(node: dict[str, Any]) -> dict[str, str]:
    attr = node_attr(node)
    if attr is None or not isinstance(attr[2], list):
        return {}
    result: dict[str, str] = {}
    for pair in attr[2]:
        if isinstance(pair, list) and len(pair) == 2:
            result[str(pair[0])] = str(pair[1])
    return result


def inline_text(value: Any) -> str:
    """Render enough Pandoc inline structure for structural validation."""
    if isinstance(value, list):
        return "".join(inline_text(item) for item in value)
    if not isinstance(value, dict):
        return ""

    kind = value.get("t")
    content = value.get("c")
    if kind == "Str":
        return str(content or "")
    if kind in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if kind == "Code" and isinstance(content, list) and len(content) == 2:
        return str(content[1] or "")
    if kind in {"Emph", "Strong", "Strikeout", "SmallCaps", "Underline", "Superscript", "Subscript"}:
        return inline_text(content)
    if kind == "Quoted" and isinstance(content, list) and len(content) == 2:
        return inline_text(content[1])
    if kind in {"Link", "Image"} and isinstance(content, list) and len(content) >= 2:
        return inline_text(content[1])
    if kind == "Span" and isinstance(content, list) and len(content) == 2:
        return inline_text(content[1])
    return ""


def block_text(node: dict[str, Any]) -> str:
    content = node.get("c")
    kind = node.get("t")
    if kind == "Header" and isinstance(content, list) and len(content) >= 3:
        return " ".join(inline_text(content[2]).split())
    if kind in {"Para", "Plain"}:
        return " ".join(inline_text(content).split())
    return ""


def chapter_headers(ast: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in iter_ast_nodes(ast):
        if node.get("t") != "Header":
            continue
        ident = node_identifier(node)
        canonical = canonical_chapter_id(ident)
        if not canonical.startswith("ch"):
            continue
        result.append(
            {
                "identifier": ident,
                "chapterId": canonical,
                "text": block_text(node),
                "audience": node_attributes(node).get("data-audience"),
                "level": node.get("c", [None])[0] if isinstance(node.get("c"), list) else None,
            }
        )
    return result


def family_divs(ast: dict[str, Any]) -> list[str]:
    return [
        node_identifier(node)
        for node in iter_ast_nodes(ast)
        if node.get("t") == "Div" and node_identifier(node).startswith("family:")
    ]


def count_identifier(ast: dict[str, Any], *, kind: str, identifier: str) -> int:
    normalized = normalize_identifier(identifier)
    count = 0
    for node in iter_ast_nodes(ast):
        if node.get("t") != kind:
            continue
        if node_identifier(node) == normalized:
            count += 1
    return count


def count_chapter_header(ast: dict[str, Any], chapter_id: str) -> int:
    wanted = canonical_chapter_id(chapter_id)
    return sum(
        1
        for node in iter_ast_nodes(ast)
        if node.get("t") == "Header" and canonical_chapter_id(node_identifier(node)) == wanted
    )


def find_family_divs(ast: dict[str, Any], family: str) -> list[dict[str, Any]]:
    identifier = family if family.startswith("family:") else f"family:{family}"
    return [
        node
        for node in iter_ast_nodes(ast)
        if node.get("t") == "Div" and node_identifier(node) == identifier
    ]


def count_raw_latex(ast: dict[str, Any], latex: str) -> int:
    count = 0
    for node in iter_ast_nodes(ast):
        if node.get("t") != "RawBlock":
            continue
        content = node.get("c")
        if isinstance(content, list) and len(content) == 2:
            if content[0] == "latex" and content[1] == latex:
                count += 1
    return count


def family_body_is_exact_raw_latex(ast: dict[str, Any], family: str, latex: str) -> bool:
    divs = find_family_divs(ast, family)
    if len(divs) != 1:
        return False
    content = divs[0].get("c")
    if not (isinstance(content, list) and len(content) == 2 and isinstance(content[1], list)):
        return False
    return content[1] == [{"t": "RawBlock", "c": ["latex", latex]}]


def document_text(ast: dict[str, Any]) -> str:
    chunks = [block_text(node) for node in iter_ast_nodes(ast)]
    return "\n".join(chunk for chunk in chunks if chunk)


def canonical_ast_bytes(ast: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            ast,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def canonical_ast_sha256(ast: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_ast_bytes(ast)).hexdigest()
