from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class ManifestError(RuntimeError):
    pass

def load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)

def resolve_pointer(doc: Any, pointer: str | None) -> Any:
    if pointer in (None, ''):
        return None
    if pointer == '/':
        return doc
    if not pointer.startswith('/'):
        raise ManifestError(f"JSON pointer must begin with '/': {pointer}")
    cur = doc
    for raw in pointer.lstrip('/').split('/'):
        token = raw.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(cur, list):
                cur = cur[int(token)]
            else:
                cur = cur[token]
        except (KeyError, IndexError, ValueError, TypeError) as e:
            raise ManifestError(f'Pointer not found: {pointer}') from e
    return cur

def iter_pointers(doc: Any, base: str = ''):
    yield base or '/', doc
    if isinstance(doc, dict):
        for k, v in doc.items():
            token = str(k).replace('~', '~0').replace('/', '~1')
            yield from iter_pointers(v, f'{base}/{token}')
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from iter_pointers(v, f'{base}/{i}')

def candidate_collections(doc: Any):
    out = []
    for ptr, value in iter_pointers(doc):
        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            keys = sorted({k for row in value for k in row.keys()})
            out.append({'pointer': ptr, 'length': len(value), 'keys': keys})
    return out

def require_bound_collection(doc: Any, pointer: str | None, label: str) -> list[dict]:
    value = resolve_pointer(doc, pointer)
    if value is None:
        raise ManifestError(f'{label} binding is not configured.')
    if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
        raise ManifestError(f'{label} must resolve to a list of objects.')
    return value

def publication_views(pub: dict, config: dict) -> tuple[str, list[dict], list[dict]]:
    adapter = config['manifestAdapter']['publication']
    commit = resolve_pointer(pub, adapter['baselineCommitPointer'])
    authored = require_bound_collection(pub, adapter['authoredIncludeRecordsPointer'], 'publication authored inputs')
    families = require_bound_collection(pub, adapter['structuredFamilyRecordsPointer'], 'publication structured families')
    if not isinstance(commit, str) or not commit:
        raise ManifestError('Publication baseline commit binding did not resolve to a string.')
    return commit, authored, families

def assembly_views(asm: dict, config: dict) -> tuple[list[dict], list[dict]]:
    adapter = config['manifestAdapter']['assembly']
    sections = require_bound_collection(asm, adapter['sectionsPointer'], 'assembly sections')
    profiles = require_bound_collection(asm, adapter['profilesPointer'], 'assembly profiles')
    return sections, profiles

def included(record: dict) -> bool:
    disposition = str(record.get('disposition', 'INCLUDE')).upper()
    status = str(record.get('decisionStatus', record.get('status', 'DECIDED'))).upper()
    return disposition == 'INCLUDE' and status in {'DECIDED', 'NORMATIVE', 'FROZEN'}

def pub_authored_by_path(records: list[dict]) -> dict[str, dict]:
    return {r['path']: r for r in records if included(r) and isinstance(r.get('path'), str)}

def pub_families_by_id(records: list[dict]) -> dict[str, dict]:
    out = {}
    for r in records:
        if not included(r):
            continue
        fid = r.get('generatorFamily') or r.get('familyId')
        if isinstance(fid, str):
            out[fid] = r
    return out

def asm_authored_by_path(asm: dict) -> dict[str, dict]:
    return {r['path']: r for r in asm.get('authoredInputs', []) if isinstance(r.get('path'), str)}

def asm_families_by_id(asm: dict) -> dict[str, dict]:
    return {r['familyId']: r for r in asm.get('structuredFamilies', []) if isinstance(r.get('familyId'), str)}

def flatten_chapters(book_structure: list[dict]) -> list[dict]:
    rows = []
    for part in sorted(book_structure, key=lambda p: (p.get('order', 0), p.get('id', ''))):
        for chapter in sorted(part.get('chapters', []), key=lambda c: (c.get('number', 0), c.get('id', ''))):
            rows.append({'part': part, 'chapter': chapter})
    return rows
