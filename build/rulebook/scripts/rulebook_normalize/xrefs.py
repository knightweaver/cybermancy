from __future__ import annotations
import re
from pathlib import PurePosixPath

SEMANTIC_RE=re.compile(r'\b(?:section|family|entity):[A-Za-z0-9_.:-]+\b')
MD_LINK_RE=re.compile(r'(?<!!)\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)(?:\s+"[^"]*")?\)')


def collect_targets(markdown: str)->set[str]:
    return set(re.findall(r'\{#((?:section|family|entity):[^\s}]+)',markdown))

def collect_semantic_refs(markdown: str)->set[str]:
    return set(SEMANTIC_RE.findall(markdown))

def validate_unique_targets(targets_by_file: dict[str,set[str]]):
    seen={}; dupes=[]
    for path,targets in targets_by_file.items():
        for target in targets:
            if target in seen: dupes.append((target,seen[target],path))
            else: seen[target]=path
    return dupes

def audience_reference_allowed(source_audience: str,target_audience: str)->bool:
    return not (source_audience in {'shared','player'} and target_audience=='gm')

def resolve_relative_repo_path(source_repo_path: str,target: str)->str | None:
    if target.startswith(('#','http://','https://','mailto:')): return None
    base=PurePosixPath(source_repo_path).parent
    clean=target.split('#',1)[0].split('?',1)[0]
    if not clean: return None
    parts=[]
    for p in (base/PurePosixPath(clean)).parts:
        if p=='.': continue
        if p=='..':
            if parts: parts.pop()
        else: parts.append(p)
    return '/'.join(parts)

def rewrite_internal_links(markdown: str,source_repo_path: str,path_targets: dict[str,str],generated_targets: dict[str,str])->tuple[str,list[dict]]:
    refs=[]
    def repl(m):
        label=m.group('label'); target=m.group('target')
        repo_rel=resolve_relative_repo_path(source_repo_path,target)
        if repo_rel is None: return m.group(0)
        sem=path_targets.get(repo_rel) or generated_targets.get(repo_rel)
        if not sem:
            refs.append({'source':source_repo_path,'target':target,'resolved':False})
            return m.group(0)
        anchor=target.split('#',1)[1] if '#' in target else None
        # Source-level semantic target wins; legacy sub-anchors remain unresolved because they are not stable.
        refs.append({'source':source_repo_path,'target':target,'resolved':True,'semanticTarget':sem,'legacyAnchor':anchor})
        return f'[{label}](#{sem})'
    return MD_LINK_RE.sub(repl,markdown),refs
