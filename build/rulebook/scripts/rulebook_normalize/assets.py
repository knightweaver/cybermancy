from __future__ import annotations
from pathlib import Path
import hashlib, shutil
from urllib.parse import unquote


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def map_asset_reference(target: str, mappings: list[dict]) -> str | None:
    target=unquote(target)
    if target.startswith(('http://','https://')): return None
    # Core/system icons are external Daggerheart assets; they are not Cybermancy repo assets.
    if target.startswith('icons/'): return None
    for m in mappings:
        prefix=m.get('prefix','')
        if prefix and target.startswith(prefix):
            return (m.get('repoPrefix','') + target[len(prefix):]).lstrip('/')
    return target.lstrip('/')


def stage_repo_asset(repo_root: Path, repo_rel: str, staging_root: Path) -> dict:
    source=(repo_root/repo_rel).resolve(); expected_root=repo_root.resolve()
    if expected_root not in source.parents and source!=expected_root:
        raise ValueError(f'Asset escapes repository root: {repo_rel}')
    if not source.exists() or not source.is_file():
        return {'source':repo_rel,'status':'missing'}
    dest=staging_root/repo_rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
    return {'source':repo_rel,'status':'staged','output':dest.relative_to(staging_root.parent.parent).as_posix(),'sha256':sha256_file(dest)}
