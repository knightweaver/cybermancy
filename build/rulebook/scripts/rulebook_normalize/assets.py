from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib
import shutil
from urllib.parse import quote, unquote, urlsplit


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def strip_query_fragment(target: str) -> str:
    """Return the path portion of a Markdown image target."""
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return target
    return parts.path


def is_remote_asset_reference(target: str) -> bool:
    target = (target or '').strip()
    return target.startswith(('http://', 'https://', 'data:', '//'))


def map_asset_reference(target: str, mappings: list[dict]) -> str | None:
    """Map a reader-visible asset target to a repository-relative logical path.

    Runtime-only image wiring is filtered before this function is called. Any
    non-remote image that remains reader-visible is treated as a publication
    dependency and must resolve inside the normalized Step 4 corpus.
    """
    target = unquote(strip_query_fragment(target))
    if is_remote_asset_reference(target):
        return None
    for m in mappings:
        prefix = m.get('prefix', '')
        if prefix and target.startswith(prefix):
            return (m.get('repoPrefix', '') + target[len(prefix):]).lstrip('/')
    return target.lstrip('/')


def _audience_asset_roots(audience: str | None) -> tuple[str, ...]:
    value = (audience or '').strip().lower()
    if value in {'player', 'players', 'player-facing'}:
        return ('docs/player-facing', 'docs/_shared')
    if value in {'gm', 'game-master', 'gm-facing'}:
        return ('docs/gm-facing', 'docs/_shared')
    if value in {'shared', 'common', 'all'}:
        return ('docs/_shared', 'docs/player-facing', 'docs/gm-facing')
    return ('docs/_shared',)


def _resolution_groups(logical: str, audience: str | None) -> list[list[str]]:
    """Return ordered source-authority groups for one logical asset path.

    Audience-specific documentation assets are the canonical publication
    sources. ``docs/_shared`` is the next fallback, and a legacy repository-root
    copy is consulted only when no authoritative docs copy exists. Shared
    publication content may fall back to player/GM copies as one equal-priority
    group; conflicting files within that group remain ambiguous.
    """
    if not logical:
        return []
    if logical.startswith('docs/'):
        return [[logical]]

    value = (audience or '').strip().lower()
    if value in {'player', 'players', 'player-facing'}:
        return [
            [PurePosixPath('docs/player-facing', logical).as_posix()],
            [PurePosixPath('docs/_shared', logical).as_posix()],
            [logical],
        ]
    if value in {'gm', 'game-master', 'gm-facing'}:
        return [
            [PurePosixPath('docs/gm-facing', logical).as_posix()],
            [PurePosixPath('docs/_shared', logical).as_posix()],
            [logical],
        ]
    if value in {'shared', 'common', 'all'}:
        return [
            [PurePosixPath('docs/_shared', logical).as_posix()],
            [
                PurePosixPath('docs/player-facing', logical).as_posix(),
                PurePosixPath('docs/gm-facing', logical).as_posix(),
            ],
            [logical],
        ]
    return [
        [PurePosixPath('docs/_shared', logical).as_posix()],
        [logical],
    ]


def resolve_publication_source_asset(
    repo_root: Path,
    logical_repo_rel: str,
    audience: str | None = None,
) -> dict:
    """Resolve one logical publication asset to its checked-in repository file.

    Canonical Foundry records can keep runtime references such as
    ``modules/cybermancy/assets/...``. After runtime mapping reduces those to a
    logical path such as ``assets/...``, the publication source is resolved by
    explicit authority: audience-specific ``docs`` assets first, shared docs
    second, and legacy repository-root copies only as a fallback.

    This lets the repository keep large artwork once in the publication source
    tree while allowing older root-level asset copies to coexist temporarily.
    Conflicts only fail closed when multiple files exist at the *same authority
    level* and differ in content; a lower-authority legacy copy never overrides
    or makes an authoritative docs asset ambiguous.
    """
    logical = unquote(logical_repo_rel or '').replace('\\', '/').lstrip('/')
    groups = _resolution_groups(logical, audience)
    candidates = [candidate for group in groups for candidate in group]

    for priority, group in enumerate(groups):
        existing = [candidate for candidate in group if (repo_root / candidate).is_file()]
        if not existing:
            continue

        hashes = {candidate: sha256_file(repo_root / candidate) for candidate in existing}
        unique_hashes = set(hashes.values())
        if len(unique_hashes) > 1:
            return {
                'status': 'ambiguous',
                'logicalPath': logical,
                'audience': audience,
                'candidates': candidates,
                'existing': existing,
                'hashes': hashes,
                'authorityPriority': priority,
            }

        return {
            'status': 'resolved',
            'logicalPath': logical,
            'audience': audience,
            'sourceRepoPath': existing[0],
            'candidates': candidates,
            'equivalentSources': existing,
            'sha256': hashes[existing[0]],
            'authorityPriority': priority,
        }

    return {
        'status': 'missing',
        'logicalPath': logical,
        'audience': audience,
        'candidates': candidates,
    }


def publication_asset_path(repo_rel: str) -> str:
    """Return the deterministic path under build/rulebook/source/ for an asset.

    Repository assets already living below an ``assets`` directory keep the
    useful tail of that hierarchy. Other publication-visible files are placed
    below ``assets/repository`` so that every local image can still be staged
    without guessing or basename substitution.
    """
    repo_rel = unquote(repo_rel).replace('\\', '/').lstrip('/')
    parts = list(PurePosixPath(repo_rel).parts)
    if 'assets' in parts:
        idx = parts.index('assets')
        tail = parts[idx + 1:]
        if tail:
            return PurePosixPath('assets', *tail).as_posix()
    return PurePosixPath('assets', 'repository', *parts).as_posix()


def publication_markdown_reference(publication_rel: str) -> str:
    """Return the reference emitted from source/assembled/*.md."""
    encoded = quote(PurePosixPath(publication_rel).as_posix(), safe='/@:+-._~')
    return '../' + encoded


def stage_publication_asset(
    repo_root: Path,
    repo_rel: str,
    source_root: Path,
    publication_rel: str,
) -> dict:
    """Copy one source asset into the self-contained Step 4 source corpus."""
    source = (repo_root / unquote(repo_rel)).resolve()
    expected_repo_root = repo_root.resolve()
    if expected_repo_root not in source.parents and source != expected_repo_root:
        raise ValueError(f'Asset escapes repository root: {repo_rel}')

    dest = (source_root / PurePosixPath(publication_rel)).resolve()
    expected_source_root = source_root.resolve()
    if expected_source_root not in dest.parents and dest != expected_source_root:
        raise ValueError(f'Publication asset escapes Step 4 source root: {publication_rel}')

    if not source.exists() or not source.is_file():
        return {
            'source': repo_rel,
            'publicationPath': PurePosixPath(publication_rel).as_posix(),
            'status': 'missing',
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return {
        'source': repo_rel,
        'publicationPath': dest.relative_to(source_root).as_posix(),
        'status': 'staged',
        'sha256': sha256_file(dest),
    }


def stage_repo_asset(repo_root: Path, repo_rel: str, staging_root: Path) -> dict:
    """Legacy staging helper retained for backwards-compatible callers."""
    source = (repo_root / repo_rel).resolve()
    expected_root = repo_root.resolve()
    if expected_root not in source.parents and source != expected_root:
        raise ValueError(f'Asset escapes repository root: {repo_rel}')
    if not source.exists() or not source.is_file():
        return {'source': repo_rel, 'status': 'missing'}
    dest = staging_root / repo_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return {
        'source': repo_rel,
        'status': 'staged',
        'output': dest.relative_to(staging_root.parent.parent).as_posix(),
        'sha256': sha256_file(dest),
    }
