from __future__ import annotations
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

from .assets import (
    is_remote_asset_reference, map_asset_reference, publication_asset_path,
    publication_markdown_reference, sha256_file, stage_publication_asset,
    strip_query_fragment,
)
from .manifest import (
    publication_views, assembly_views, pub_authored_by_path, pub_families_by_id,
    asm_authored_by_path, asm_families_by_id, flatten_chapters
)
from .markdown import (
    body_yaml_delimiter_ambiguities, extract_images, normalize_authored_markdown,
    pandoc_safe_assembled_markdown, rewrite_image_targets,
)
from .structured import render_entity, source_sort_value, stable_id
from .snapshot import (
    STRUCTURED_DIGEST_ALGORITHM, SnapshotError, structured_family_snapshot
)
from .validate import new_report, add_check, tree_hash_manifest
from .xrefs import rewrite_internal_links, collect_targets, validate_unique_targets, audience_reference_allowed


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _slug(s: str) -> str:
    s=(s or '').casefold().replace('_','-').replace(' ','-')
    s=re.sub(r'[^a-z0-9-]+','-',s); s=re.sub(r'-+','-',s).strip('-')
    return s or 'entry'


def _write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.rstrip()+'\n',encoding='utf-8')


def manifest_contract_report(pub: dict, asm: dict, config: dict) -> dict:
    report=new_report()
    try:
        pub_commit,pub_auth_records,pub_family_records=publication_views(pub,config)
        book_structure,profiles=assembly_views(asm,config)
    except Exception as e:
        add_check(report,'MANIFEST_BINDINGS','ERROR',str(e)); return report

    baseline=config['baseline']['commit']
    asm_commit=asm.get('authority',{}).get('sourceCommit')
    commits={'config':baseline,'publication':pub_commit,'assembly':asm_commit}
    if len(set(v for v in commits.values() if v))==1 and all(commits.values()):
        add_check(report,'BASELINE_COMMIT_ALIGNMENT','PASS',f'All authorities resolve to {baseline}.')
    else:
        add_check(report,'BASELINE_COMMIT_ALIGNMENT','ERROR','Baseline commits disagree.',commits)

    pub_auth=pub_authored_by_path(pub_auth_records); asm_auth=asm_authored_by_path(asm)
    only_pub=sorted(set(pub_auth)-set(asm_auth)); only_asm=sorted(set(asm_auth)-set(pub_auth))
    if not only_pub and not only_asm:
        add_check(report,'AUTHORED_MANIFEST_JOIN','PASS',f'{len(pub_auth)} authored inputs join exactly by path.')
    else:
        add_check(report,'AUTHORED_MANIFEST_JOIN','ERROR',
                  'Step 3 authored inputs do not exactly join to Step 2 INCLUDE authored inputs.',
                  {'publicationOnly':only_pub,'assemblyOnly':only_asm})

    pub_fam=pub_families_by_id(pub_family_records); asm_fam=asm_families_by_id(asm)
    if set(pub_fam)==set(asm_fam):
        add_check(report,'STRUCTURED_FAMILY_JOIN','PASS',f'{len(pub_fam)} structured families join exactly by family ID.')
    else:
        add_check(report,'STRUCTURED_FAMILY_JOIN','ERROR','Structured family IDs disagree.',
                  {'publicationOnly':sorted(set(pub_fam)-set(asm_fam)),'assemblyOnly':sorted(set(asm_fam)-set(pub_fam))})

    count_errors=[]
    for fid in sorted(set(pub_fam)&set(asm_fam)):
        p=int(pub_fam[fid].get('entityCount',-1)); a=int(asm_fam[fid].get('entityCount',-2)); c=config.get('families',{}).get(fid,{}).get('expected')
        if c is None or p!=a or p!=int(c): count_errors.append({'family':fid,'publication':p,'assembly':a,'config':c})
    if count_errors:
        add_check(report,'STRUCTURED_FAMILY_COUNTS','ERROR','Per-family counts disagree.',count_errors)
    else:
        total=sum(int(x.get('entityCount',0)) for x in asm_fam.values())
        status='PASS' if total==int(config['baseline']['expectedLogicalEntities']) else 'ERROR'
        add_check(report,'STRUCTURED_FAMILY_COUNTS',status,f'Per-family counts align; total {total}.')

    declared_algorithms={
        str(r.get('contentDigestAlgorithm') or '').strip()
        for r in pub_fam.values()
        if str(r.get('contentDigestAlgorithm') or '').strip()
    }
    configured_algorithm=str(config.get('structured',{}).get('familyDigestAlgorithm') or '').strip()
    if declared_algorithms=={STRUCTURED_DIGEST_ALGORITHM} and configured_algorithm==STRUCTURED_DIGEST_ALGORITHM:
        add_check(report,'STRUCTURED_DIGEST_CONTRACT','PASS','Publication manifest and normalization config use the shared structured-family digest v2 contract.')
    else:
        add_check(report,'STRUCTURED_DIGEST_CONTRACT','ERROR','Structured-family digest contract is not aligned.',{
            'publicationAlgorithms':sorted(declared_algorithms),
            'configAlgorithm':configured_algorithm,
            'requiredAlgorithm':STRUCTURED_DIGEST_ALGORITHM,
        })

    # Primary placement is expressed in two Step 3 locations:
    #   * part.openerRefs for front-matter/opening fragments, and
    #   * chapter.contentRefs for ordinary chapter content.
    # gmDivider.afterDividerFrontMatterRefs is an ordering/routing assertion for
    # the GM opener, not a second primary placement.
    authored_refs=[]; family_refs=[]; chapter_ids=[]
    for part in sorted(book_structure,key=lambda p:(p.get('order',0),p.get('id',''))):
        for ref in part.get('openerRefs',[]):
            if isinstance(ref,str) and ref.startswith('auth.'):
                authored_refs.append(ref)
            elif isinstance(ref,str) and ref.startswith('family:'):
                family_refs.append(ref.split(':',1)[1])
            else:
                add_check(report,'UNKNOWN_CONTENT_REF','ERROR',f"Unknown assembly openerRef {ref} in {part.get('id')}")
        for ch in sorted(part.get('chapters',[]),key=lambda c:(c.get('number',0),c.get('id',''))):
            chapter_ids.append(ch.get('id'))
            for ref in ch.get('contentRefs',[]):
                if isinstance(ref,str) and ref.startswith('auth.'): authored_refs.append(ref)
                elif isinstance(ref,str) and ref.startswith('family:'): family_refs.append(ref.split(':',1)[1])
                else: add_check(report,'UNKNOWN_CONTENT_REF','ERROR',f"Unknown assembly contentRef {ref} in {ch.get('id')}")
    asm_auth_ids=[r.get('assemblyInputId') for r in asm.get('authoredInputs',[])]
    dup_auth=sorted({x for x in authored_refs if authored_refs.count(x)>1}); missing_auth=sorted(set(asm_auth_ids)-set(authored_refs)); extra_auth=sorted(set(authored_refs)-set(asm_auth_ids))
    if not dup_auth and not missing_auth and not extra_auth:
        add_check(report,'AUTHORED_PRIMARY_PLACEMENT','PASS',f'{len(authored_refs)} authored refs placed exactly once.')
    else:
        add_check(report,'AUTHORED_PRIMARY_PLACEMENT','ERROR','Authored placement invariant violated.',{'duplicates':dup_auth,'missing':missing_auth,'unknown':extra_auth})
    dup_fam=sorted({x for x in family_refs if family_refs.count(x)>1}); missing_fam=sorted(set(asm_fam)-set(family_refs)); extra_fam=sorted(set(family_refs)-set(asm_fam))
    if not dup_fam and not missing_fam and not extra_fam:
        add_check(report,'STRUCTURED_PRIMARY_PLACEMENT','PASS',f'{len(family_refs)} family refs placed exactly once.')
    else:
        add_check(report,'STRUCTURED_PRIMARY_PLACEMENT','ERROR','Structured placement invariant violated.',{'duplicates':dup_fam,'missing':missing_fam,'unknown':extra_fam})

    profile_ids={p.get('id') for p in profiles}
    required={'complete-rulebook','player-guide'}
    if required.issubset(profile_ids): add_check(report,'BUILD_PROFILES','PASS','Required complete-rulebook and player-guide profiles are present.')
    else: add_check(report,'BUILD_PROFILES','ERROR','Required build profile missing.',{'found':sorted(profile_ids)})

    divider=asm.get('gmDivider',{})
    if divider.get('title')==config['semantics']['gmDivider'] and divider.get('requiredInCompleteBuild') and divider.get('omittedInPlayerBuild'):
        add_check(report,'GM_DIVIDER_CONTRACT','PASS',divider.get('title'))
    else: add_check(report,'GM_DIVIDER_CONTRACT','ERROR','GM divider contract does not match normalization config.',divider)

    # v1.1 makes the GM-section opener explicit in both the part and divider
    # metadata. Treat the divider list as a routing assertion and require it to
    # agree with the openerRefs of beforePart when either side is present.
    before_part=next((p for p in book_structure if p.get('id')==divider.get('beforePart')),None)
    divider_front=list(divider.get('afterDividerFrontMatterRefs',[]) or [])
    part_openers=list((before_part or {}).get('openerRefs',[]) or [])
    if divider_front or part_openers:
        if before_part is None:
            add_check(report,'GM_FRONT_MATTER_ROUTING','ERROR','gmDivider.beforePart does not resolve to a book part.',{'beforePart':divider.get('beforePart')})
        elif divider_front==part_openers:
            add_check(report,'GM_FRONT_MATTER_ROUTING','PASS',f'{len(part_openers)} GM front-matter opener ref(s) route immediately after the divider.')
        else:
            add_check(report,'GM_FRONT_MATTER_ROUTING','ERROR','GM divider front-matter refs disagree with the beforePart openerRefs.',{'afterDividerFrontMatterRefs':divider_front,'openerRefs':part_openers,'beforePart':divider.get('beforePart')})
    return report


def repository_preflight(repo_root: Path, pub: dict, asm: dict, config: dict, report: dict):
    """Validate the frozen canonical source corpus independently of repository HEAD.

    ``frozenSourceCommit`` is provenance, not the acceptance gate. Repository HEAD
    may advance for build/tooling commits. Canonical source integrity is enforced
    by authored source hashes plus structured-family digest/count reconciliation.
    """
    pub_commit,pub_auth_records,pub_family_records=publication_views(pub,config)
    pub_fam=pub_families_by_id(pub_family_records)
    asm_fam=asm_families_by_id(asm)

    # HEAD is implementation-state metadata only. A mismatch is informational;
    # source hashes/digests below decide whether the frozen corpus still matches.
    git_marker=repo_root/'.git'
    if git_marker.exists():
        try:
            head=subprocess.check_output(
                ['git','-C',str(repo_root),'rev-parse','HEAD'],
                text=True,stderr=subprocess.STDOUT
            ).strip()
            details={
                'currentHead':head,
                'frozenSourceCommit':pub_commit,
                'headMatchesFrozenSourceCommit':head==pub_commit,
            }
            if head==pub_commit:
                add_check(
                    report,'REPOSITORY_HEAD','PASS',
                    'Repository HEAD matches the frozen source commit.',details
                )
            else:
                add_check(
                    report,'REPOSITORY_HEAD','INFO',
                    'Repository HEAD has advanced beyond the frozen source commit; '
                    'canonical source integrity is enforced by hashes and structured-family digests.',
                    details
                )
        except Exception as e:
            add_check(
                report,'REPOSITORY_HEAD','WARNING',
                'Could not resolve repository HEAD; canonical source integrity will still be '
                f'enforced directly from the frozen corpus: {e}',
                {'frozenSourceCommit':pub_commit}
            )
    else:
        add_check(
            report,'REPOSITORY_HEAD','INFO',
            'No Git metadata found; canonical source integrity is enforced directly from '
            'authored hashes and structured-family digests.',
            {'frozenSourceCommit':pub_commit}
        )

    source_errors=[]

    # Authored canonical sources: existence + mandatory stored SHA-256.
    missing_auth=[]; missing_hash=[]; bad_hash=[]
    for r in pub_authored_by_path(pub_auth_records).values():
        path=r['path']; p=repo_root/path
        if not p.is_file():
            missing_auth.append(path)
            continue
        expected=r.get('sha256')
        if not isinstance(expected,str) or not expected:
            missing_hash.append(path)
            continue
        actual=sha256_file(p)
        if actual!=expected:
            bad_hash.append({'path':path,'expected':expected,'actual':actual})

    if missing_auth:
        item=add_check(
            report,'AUTHORED_SOURCE_FILES','ERROR',
            'Included authored canonical sources are missing.',missing_auth
        ); source_errors.append(item)
    if missing_hash:
        item=add_check(
            report,'AUTHORED_SOURCE_HASHES','ERROR',
            'Included authored canonical sources are missing frozen SHA-256 values.',
            missing_hash
        ); source_errors.append(item)
    if bad_hash:
        item=add_check(
            report,'AUTHORED_SOURCE_HASHES','ERROR',
            'Included authored source hashes do not match the frozen publication manifest.',
            bad_hash
        ); source_errors.append(item)
    if not missing_auth and not missing_hash and not bad_hash:
        add_check(
            report,'AUTHORED_SOURCE_FILES','PASS',
            'All frozen authored INCLUDE sources exist and match their SHA-256 values.'
        )

    # Structured canonical sources: existence + shared digest-v2 + entity counts.
    missing_fams=[]
    structured_errors=[]
    structured_entities=0
    for fid,r in pub_fam.items():
        source_path=r.get('sourcePath')
        p=repo_root/source_path if isinstance(source_path,str) else None
        if p is None or not p.is_dir():
            missing_fams.append({'family':fid,'path':source_path})
            continue

        declared_algorithm=r.get('contentDigestAlgorithm')
        if declared_algorithm!=STRUCTURED_DIGEST_ALGORITHM:
            structured_errors.append({
                'family':fid,
                'issue':'digest-algorithm',
                'declared':declared_algorithm,
                'required':STRUCTURED_DIGEST_ALGORITHM,
            })
            continue

        expected_digest=r.get('contentDigestSha256')
        if not isinstance(expected_digest,str) or not expected_digest:
            structured_errors.append({
                'family':fid,
                'issue':'missing-frozen-digest',
                'requiredAlgorithm':STRUCTURED_DIGEST_ALGORITHM,
            })
            continue

        arec=asm_fam.get(fid,{})
        actor_type=(r.get('actorType') or arec.get('actorType') or '')
        try:
            snap=structured_family_snapshot(repo_root,source_path,actor_type)
        except SnapshotError as e:
            structured_errors.append({'family':fid,'issue':'snapshot','error':str(e)})
            continue

        expected_count=int(r.get('entityCount',-1))
        structured_entities += snap.entity_count
        if snap.entity_count!=expected_count:
            structured_errors.append({
                'family':fid,
                'issue':'entity-count',
                'expected':expected_count,
                'actual':snap.entity_count,
            })
        if snap.digest_sha256!=expected_digest:
            structured_errors.append({
                'family':fid,
                'issue':'digest',
                'expected':expected_digest,
                'actual':snap.digest_sha256,
                'algorithm':STRUCTURED_DIGEST_ALGORITHM,
            })

    if missing_fams:
        item=add_check(
            report,'STRUCTURED_SOURCE_DIRS','ERROR',
            'Structured canonical source directories are missing.',missing_fams
        ); source_errors.append(item)
    else:
        add_check(
            report,'STRUCTURED_SOURCE_DIRS','PASS',
            'All structured source family directories exist.'
        )

    if structured_errors:
        # Preserve the established detailed codes for actionable diagnostics.
        digest_details=[x for x in structured_errors if x.get('issue') in {
            'digest','digest-algorithm','missing-frozen-digest','snapshot'
        }]
        count_details=[x for x in structured_errors if x.get('issue')=='entity-count']
        if digest_details:
            item=add_check(
                report,'STRUCTURED_FAMILY_DIGEST','ERROR',
                'One or more structured families do not match the frozen digest-v2 snapshot.',
                digest_details
            ); source_errors.append(item)
        if count_details:
            item=add_check(
                report,'STRUCTURED_ENTITY_COUNT','ERROR',
                'One or more structured family entity counts do not match the frozen snapshot.',
                count_details
            ); source_errors.append(item)
    elif not missing_fams:
        add_check(
            report,'STRUCTURED_SOURCE_SNAPSHOT','PASS',
            f'{len(pub_fam)} structured families and {structured_entities} logical entities '
            'match the frozen digest-v2/count snapshot.',
            {
                'familyCount':len(pub_fam),
                'entityCount':structured_entities,
                'digestAlgorithm':STRUCTURED_DIGEST_ALGORITHM,
            }
        )

    if source_errors:
        add_check(
            report,'SOURCE_CORPUS_INTEGRITY','ERROR',
            'Canonical source corpus has drifted from the frozen publication snapshot.',
            {'blockingChecks':[x['code'] for x in source_errors]}
        )
    else:
        add_check(
            report,'SOURCE_CORPUS_INTEGRITY','PASS',
            'Canonical authored hashes, structured-family digests, required paths, and '
            'entity counts match the frozen publication snapshot.',
            {'frozenSourceCommit':pub_commit}
        )
    return report


def _generated_link_candidates(pub_rec: dict, asm_rec: dict, entity: dict, source_file: Path, family_root: Path):
    outdir=str(pub_rec.get('generatedOutputDir') or '').rstrip('/')
    name=_slug(entity.get('name') or '')
    rel_parent=source_file.parent.relative_to(family_root).as_posix()
    cands={f'{outdir}/{name}.md'}
    if rel_parent!='.': cands.add(f'{outdir}/{rel_parent}/{name}.md')
    cands.add(f'{outdir}/{source_file.stem}.md')
    return cands


def _resolve_source_image(source_repo_path: str, target: str) -> str | None:
    """Resolve a local image target to a repository-relative source path."""
    target=unquote(strip_query_fragment(target))
    if is_remote_asset_reference(target):
        return None
    if target.startswith(('modules/','worlds/','icons/')):
        return target.lstrip('/')
    if target.startswith('/'):
        return target.lstrip('/')
    base=PurePosixPath(source_repo_path).parent
    parts=[]
    for part in (base/PurePosixPath(target)).parts:
        if part in ('','.'): continue
        if part=='..':
            if not parts:
                raise ValueError(f'Asset reference escapes repository root: {source_repo_path}: {target}')
            parts.pop()
        else:
            parts.append(part)
    return '/'.join(parts)


def _publicationize_images(
    text: str,
    source_repo_path: str,
    mappings: list[dict],
    assets: list[dict],
    **context,
) -> str:
    """Rewrite reader-visible image targets to source/assembled-relative assets."""
    replacements={}
    for target in sorted(set(extract_images(text))):
        if is_remote_asset_reference(target):
            continue
        resolved=_resolve_source_image(source_repo_path,target)
        if resolved is None:
            continue
        mapped=map_asset_reference(resolved,mappings)
        if mapped is None:
            continue
        publication_rel=publication_asset_path(mapped)
        publication_ref=publication_markdown_reference(publication_rel)
        replacements[target]=publication_ref
        assets.append({
            **context,
            'sourcePath':source_repo_path,
            'sourceReference':target,
            'reference':mapped,
            'publicationPath':publication_rel,
            'publicationReference':publication_ref,
        })
    return rewrite_image_targets(text,replacements)


def _stage_publication_assets(repo_root: Path, source_root: Path, assets: list[dict], report: dict) -> dict[str,dict]:
    """Stage all publication-visible local assets into source/assets/."""
    registry={}
    collisions=[]
    missing=[]

    for item in assets:
        publication_rel=item.get('publicationPath')
        repo_rel=item.get('reference')
        if not publication_rel or not repo_rel:
            continue
        existing=registry.get(publication_rel)
        if existing and existing['source']!=repo_rel:
            a=repo_root/existing['source']; b=repo_root/repo_rel
            if a.is_file() and b.is_file() and sha256_file(a)==sha256_file(b):
                item.update({k:v for k,v in existing.items() if k!='source'})
                item['status']='staged-alias'
                item['aliasedToSource']=existing['source']
                continue
            collisions.append({
                'publicationPath':publication_rel,
                'firstSource':existing['source'],
                'secondSource':repo_rel,
            })
            item['status']='collision'
            continue

        if existing is None:
            staged=stage_publication_asset(repo_root,repo_rel,source_root,publication_rel)
            registry[publication_rel]=staged
        else:
            staged=existing
        item.update({k:v for k,v in staged.items() if k!='source'})
        item['sourceRepoPath']=repo_rel
        if staged.get('status')=='missing':
            missing.append({'source':repo_rel,'publicationPath':publication_rel})

    if collisions:
        add_check(report,'PUBLICATION_ASSET_COLLISION','ERROR',
                  'Multiple different source assets map to the same normalized publication path.',collisions)
    else:
        add_check(report,'PUBLICATION_ASSET_COLLISION','PASS',
                  'No conflicting publication asset paths were detected.')

    if missing:
        add_check(report,'ASSET_STAGING','ERROR',
                  f'{len(missing)} publication-visible repository assets could not be staged.',missing[:200])
    else:
        staged_count=sum(1 for v in registry.values() if v.get('status')=='staged')
        add_check(report,'ASSET_STAGING','PASS',
                  f'{staged_count} unique publication assets staged inside build/rulebook/source/assets/.')
    return registry


def _validate_assembled_assets(profile_outputs: dict[str,Path], source_root: Path, registry: dict[str,dict], report: dict) -> None:
    """Require every local assembled image to resolve inside the Step 4 corpus."""
    problems=[]; refs=[]
    source_abs=source_root.resolve()
    for profile_id,path in sorted(profile_outputs.items()):
        for target in extract_images(path.read_text(encoding='utf-8')):
            if is_remote_asset_reference(target):
                continue
            local=unquote(strip_query_fragment(target))
            candidate=(path.parent/local).resolve()
            if source_abs not in candidate.parents and candidate!=source_abs:
                problems.append({'profile':profile_id,'reference':target,'issue':'escapes-source-root'})
                continue
            rel=candidate.relative_to(source_root).as_posix()
            refs.append({'profile':profile_id,'reference':target,'resolvedPath':rel})
            if not candidate.is_file():
                problems.append({'profile':profile_id,'reference':target,'resolvedPath':rel,'issue':'missing'})
                continue
            provenance=registry.get(rel)
            if provenance is None:
                problems.append({'profile':profile_id,'reference':target,'resolvedPath':rel,'issue':'no-staging-provenance'})
                continue
            if provenance.get('sha256')!=sha256_file(candidate):
                problems.append({'profile':profile_id,'reference':target,'resolvedPath':rel,'issue':'staged-hash-mismatch'})

    if problems:
        add_check(report,'ASSET_RESOLUTION','ERROR',
                  f'{len(problems)} local image references in assembled profiles are not self-contained.',problems[:200])
    else:
        add_check(report,'ASSET_RESOLUTION','PASS',
                  f'{len(refs)} local image references across assembled profiles resolve inside build/rulebook/source/.',
                  {'localReferences':len(refs),'uniqueStagedAssets':len(registry)})


def materialize(repo_root: Path, outroot: Path, pub: dict, asm: dict, config: dict, base_report: dict | None=None) -> dict:
    if outroot.exists(): shutil.rmtree(outroot)
    source_root=outroot/'source'; meta_root=source_root/'metadata'; generated_root=source_root/'generated'; authored_root=source_root/'authored'; assembled_root=source_root/'assembled'
    for p in (meta_root,generated_root,authored_root,assembled_root): p.mkdir(parents=True,exist_ok=True)
    report=json.loads(json.dumps(base_report or new_report()))
    pub_commit,pub_auth_records,pub_family_records=publication_views(pub,config)
    pub_auth=pub_authored_by_path(pub_auth_records); pub_fam=pub_families_by_id(pub_family_records)
    asm_auth=asm_authored_by_path(asm); asm_fam=asm_families_by_id(asm)

    provenance=[]; source_hashes=[]; semantic_targets=[]; assets=[]; runtime_assets=[]; references=[]
    content_by_ref={}; target_audience={}; generated_link_targets={}
    asset_mappings=config.get('assets',{}).get('foundryRuntimeMappings',[])

    # Structured families first so legacy links from authored docs can resolve to entity semantic IDs.
    for fid,arec in asm_fam.items():
        prec=pub_fam[fid]; family_dir=repo_root/arec['sourcePath']
        actor_type=(prec.get('actorType') or arec.get('actorType') or '')
        declared_algorithm=prec.get('contentDigestAlgorithm')
        if declared_algorithm and declared_algorithm!=STRUCTURED_DIGEST_ALGORITHM:
            add_check(report,'STRUCTURED_DIGEST_CONTRACT','ERROR',f'{fid}: publication manifest declares a different structured-family digest algorithm.',{'declared':declared_algorithm,'required':STRUCTURED_DIGEST_ALGORITHM})
        try:
            snap=structured_family_snapshot(repo_root,arec['sourcePath'],actor_type)
        except SnapshotError as e:
            add_check(report,'STRUCTURED_FAMILY_SNAPSHOT','ERROR',f'{fid}: {e}')
            continue
        digest=snap.digest_sha256
        expected_digest=prec.get('contentDigestSha256')
        if expected_digest and digest!=expected_digest:
            add_check(report,'STRUCTURED_FAMILY_DIGEST','ERROR',f'{fid}: source digest mismatch.',{'expected':expected_digest,'actual':digest,'algorithm':STRUCTURED_DIGEST_ALGORITHM})
        logical=[(record.path,record.document) for record in snap.logical_records]
        folder_count=snap.foundry_folder_count
        expected=int(arec['entityCount'])
        if len(logical)!=expected:
            add_check(report,'STRUCTURED_ENTITY_COUNT','ERROR',f'{fid}: found {len(logical)} logical entities; expected {expected}.')
        else: add_check(report,f'COUNT_{fid.upper().replace("-","_")}','PASS',f'{fid}: {expected} logical entities.')
        logical.sort(key=lambda pair: source_sort_value(fid,pair[1],pair[0].relative_to(family_dir).as_posix(),arec.get('sort',[])))
        family_chunks=[f'::: {{#{"family:"+fid} .rb-collection data-family="{fid}" data-audience="{arec["audience"]}"}}','']
        semantic_targets.append({'semanticId':f'family:{fid}','kind':'family','audience':arec['audience'],'title':arec['title']}); target_audience[f'family:{fid}']=arec['audience']
        for idx,(p,doc) in enumerate(logical,1):
            try: md,metadata=render_entity(fid,doc,config['structured']['fastPlayCandidatePaths'])
            except Exception as e:
                add_check(report,'STRUCTURED_RENDER','ERROR',f'{p.relative_to(repo_root).as_posix()}: {e}'); continue
            metadata['sourcePath']=p.relative_to(repo_root).as_posix(); metadata['audience']=arec['audience']
            md=_publicationize_images(
                md,metadata['sourcePath'],asset_mappings,assets,
                sourceEntity=metadata['semanticId'],kind='structured-publication'
            )
            entity_out=generated_root/fid/f'{idx:04d}-{metadata["sourceId"]}.md'; _write_text(entity_out,md)
            family_chunks += [md.rstrip(),'']
            semantic_targets.append({'semanticId':metadata['semanticId'],'kind':'entity','audience':arec['audience'],'title':metadata['name'],'family':fid,'sourceId':metadata['sourceId']}); target_audience[metadata['semanticId']]=arec['audience']
            provenance.append({'kind':'structured-entity','family':fid,'sourcePath':metadata['sourcePath'],'sourceSha256':sha256_file(p),'sourceCommit':pub_commit,'semanticId':metadata['semanticId'],'outputPath':entity_out.relative_to(outroot).as_posix(),'outputSha256':sha256_file(entity_out)})
            source_hashes.append({'path':metadata['sourcePath'],'sha256':sha256_file(p)})
            for cand in _generated_link_candidates(prec,arec,doc,p,family_dir):
                if cand in generated_link_targets and generated_link_targets[cand]!=metadata['semanticId']:
                    generated_link_targets[cand]='__AMBIGUOUS__'
                else: generated_link_targets[cand]=metadata['semanticId']
            for ref in metadata.get('runtimeAssetRefs',[]):
                runtime_assets.append({'reference':ref,'sourceEntity':metadata['semanticId'],'kind':'foundry-runtime','status':'metadata-only'})
        family_chunks.append(':::')
        fam_md='\n'.join(family_chunks).rstrip()+'\n'; collection_path=generated_root/fid/'_collection.md'; _write_text(collection_path,fam_md)
        content_by_ref[f'family:{fid}']={'markdown':fam_md,'audience':arec['audience'],'semanticId':f'family:{fid}','title':arec['title']}
        provenance.append({'kind':'structured-family','family':fid,'sourcePath':arec['sourcePath'],'sourceDigestSha256':digest,'sourceCommit':pub_commit,'semanticId':f'family:{fid}','outputPath':collection_path.relative_to(outroot).as_posix(),'outputSha256':sha256_file(collection_path),'logicalEntityCount':len(logical),'foundryFolderCount':folder_count})

    generated_link_targets={k:v for k,v in generated_link_targets.items() if v!='__AMBIGUOUS__'}

    placement_to_chapter={r['assemblyInputId']:r['placement'] for r in asm.get('authoredInputs',[])}
    path_targets={r['path']:f"section:{r['placement']}" for r in asm.get('authoredInputs',[])}
    for arec in asm.get('authoredInputs',[]):
        path=arec['path']; prec=pub_auth.get(path)
        if prec is None:
            # Contract validation already records this; avoid fabricating content.
            continue
        src=repo_root/path
        try: text=src.read_text(encoding='utf-8'); norm=normalize_authored_markdown(path,text,arec)
        except Exception as e:
            add_check(report,'AUTHORED_NORMALIZE','ERROR',f'{path}: {e}'); continue
        norm,refs=rewrite_internal_links(norm,path,path_targets,generated_link_targets); references.extend(refs)
        norm=_publicationize_images(norm,path,asset_mappings,assets,kind='authored')
        out=authored_root/f'{arec["assemblyInputId"].replace(".","-")}.md'; _write_text(out,norm)
        sem=f"section:{arec['placement']}"; target_audience[sem]=arec['audience']
        content_by_ref[arec['assemblyInputId']]={'markdown':norm,'audience':arec['audience'],'semanticId':sem,'title':arec['title']}
        provenance.append({'kind':'authored','assemblyInputId':arec['assemblyInputId'],'sourcePath':path,'sourceSha256':sha256_file(src),'sourceCommit':pub_commit,'semanticId':sem,'outputPath':out.relative_to(outroot).as_posix(),'outputSha256':sha256_file(out),'assemblyMode':arec.get('assemblyMode')})
        source_hashes.append({'path':path,'sha256':sha256_file(src)})

    # Stage every reader-visible local asset into the self-contained Step 4 source corpus.
    staged_assets=_stage_publication_assets(repo_root,source_root,assets,report)

    unresolved=[r for r in references if not r.get('resolved')]
    if unresolved: add_check(report,'CROSS_REFERENCE_RESOLUTION','ERROR',f'{len(unresolved)} local Markdown links did not resolve to stable semantic targets.',unresolved[:200])
    else: add_check(report,'CROSS_REFERENCE_RESOLUTION','PASS',f'{len(references)} internal Markdown references resolved or no internal references were present.')

    # Assemble authoritative book topology.
    profile_outputs={}
    profiles={p['id']:p for p in asm.get('buildProfiles',[])}
    divider=asm.get('gmDivider',{})
    for pid,profile in profiles.items():
        include=set(profile.get('includeAudiences',[])); chunks=[]; inserted=False
        chunks += ['---',f'title: "{profile.get("title",pid)}"',f'profile: "{pid}"',f'source-commit: "{pub_commit}"','---','']
        for part in sorted(asm.get('bookStructure',[]),key=lambda p:(p.get('order',0),p.get('id',''))):
            paud=part.get('audience','player')
            if paud not in include: continue
            if pid=='complete-rulebook' and part.get('id')==divider.get('beforePart') and divider.get('requiredInCompleteBuild') and not inserted:
                chunks += [f'# {divider["title"]} {{#section:gm-material-divider .gm-divider data-audience="gm"}}','']; inserted=True
                semantic_targets.append({'semanticId':'section:gm-material-divider','kind':'divider','audience':'gm','title':divider['title']}); target_audience['section:gm-material-divider']='gm'
            # Part opener/front-matter fragments are primary assembly content.
            # For the GM boundary they are deliberately rendered after the
            # spoiler divider and before the Part V heading.
            for ref in part.get('openerRefs',[]):
                node=content_by_ref.get(ref)
                if not node:
                    add_check(report,'ASSEMBLY_CONTENT_MISSING','ERROR',f'{part["id"]}: openerRef {ref} has no normalized fragment.'); continue
                if node['audience'] not in include:
                    add_check(report,'ASSEMBLY_AUDIENCE_MISMATCH','ERROR',f'{part["id"]}: openerRef {ref} audience {node["audience"]} not allowed in {pid}.'); continue
                chunks += [node['markdown'].rstrip(),'']

            psem=f"section:{part['id']}"; chunks += [f'# {part["title"]} {{#{psem} .rb-part data-audience="{paud}"}}','']
            if not any(t.get('semanticId')==psem for t in semantic_targets): semantic_targets.append({'semanticId':psem,'kind':'part','audience':paud,'title':part['title']}); target_audience[psem]=paud
            for ch in sorted(part.get('chapters',[]),key=lambda c:(c.get('number',0),c.get('id',''))):
                csem=f"section:{ch['id']}"; chunks += [f'## Chapter {ch["number"]}: {ch["title"]} {{#{csem} .rb-chapter data-audience="{paud}"}}','']
                if not any(t.get('semanticId')==csem for t in semantic_targets): semantic_targets.append({'semanticId':csem,'kind':'chapter','audience':paud,'title':ch['title'],'number':ch['number']}); target_audience[csem]=paud
                for ref in ch.get('contentRefs',[]):
                    node=content_by_ref.get(ref)
                    if not node:
                        add_check(report,'ASSEMBLY_CONTENT_MISSING','ERROR',f'{ch["id"]}: contentRef {ref} has no normalized fragment.'); continue
                    if node['audience'] not in include:
                        add_check(report,'ASSEMBLY_AUDIENCE_MISMATCH','ERROR',f'{ch["id"]}: {ref} audience {node["audience"]} not allowed in {pid}.'); continue
                    chunks += [node['markdown'].rstrip(),'']
        raw_text='\n'.join(chunks).rstrip()+'\n'
        try:
            text=pandoc_safe_assembled_markdown(raw_text)
        except Exception as e:
            add_check(report,'BODY_YAML_DELIMITER_AMBIGUITY','ERROR',f'{pid}: could not sanitize assembled YAML/thematic-break boundaries: {e}')
            text=raw_text
        out=assembled_root/f'{pid}.md'; _write_text(out,text); profile_outputs[pid]=out

    yaml_problems=[]
    for profile_id,path in sorted(profile_outputs.items()):
        txt=path.read_text(encoding='utf-8')
        ambiguous=body_yaml_delimiter_ambiguities(txt)
        standalone=[i for i,line in enumerate(txt.splitlines(),start=1) if line.strip()=='---' and not line.startswith((' ','\t'))]
        if ambiguous or len(standalone)!=2:
            yaml_problems.append({
                'profile':profile_id,
                'ambiguousBodyLines':ambiguous,
                'standaloneDelimiterLines':standalone,
                'expectedStandaloneDelimiterCount':2,
            })
    if yaml_problems:
        add_check(report,'BODY_YAML_DELIMITER_AMBIGUITY','ERROR',
                  'Assembled profiles contain standalone body --- delimiters that may be parsed as YAML metadata.',yaml_problems)
    else:
        add_check(report,'BODY_YAML_DELIMITER_AMBIGUITY','PASS',
                  'Each assembled profile contains only its two opening YAML metadata delimiters; body thematic breaks are Pandoc-safe.')

    _validate_assembled_assets(profile_outputs,source_root,staged_assets,report)

    complete=profile_outputs.get('complete-rulebook'); player=profile_outputs.get('player-guide')
    if complete:
        n=complete.read_text(encoding='utf-8').count(config['semantics']['gmDivider'])
        add_check(report,'COMPLETE_GM_DIVIDER','PASS' if n==1 else 'ERROR',f'Complete rulebook contains GM divider {n} time(s).')
    if player:
        txt=player.read_text(encoding='utf-8'); bad=config['semantics']['gmDivider'] in txt or any('data-audience="gm"' in line for line in txt.splitlines())
        add_check(report,'PLAYER_PROFILE_AUDIENCE','ERROR' if bad else 'PASS','Player guide contains no GM-only nodes.' if not bad else 'Player guide contains GM-only material.')

    # Semantic target uniqueness across canonical fragments, not across assembled profiles (which intentionally repeat targets).
    targets_by_file={}
    for p in list(authored_root.glob('*.md'))+list(generated_root.glob('*/_collection.md')):
        targets_by_file[p.relative_to(outroot).as_posix()]=collect_targets(p.read_text(encoding='utf-8'))
    dupes=validate_unique_targets(targets_by_file)
    if dupes: add_check(report,'SEMANTIC_TARGET_UNIQUENESS','ERROR','Duplicate semantic targets in normalized corpus.',dupes[:200])
    else: add_check(report,'SEMANTIC_TARGET_UNIQUENESS','PASS',f'{sum(len(v) for v in targets_by_file.values())} canonical semantic targets are unique.')

    # Audience cross-reference rule for resolved semantic refs.
    leaks=[]
    for r in references:
        if not r.get('resolved'): continue
        source_path=r['source']; srec=asm_auth.get(source_path); saud=srec.get('audience') if srec else 'shared'; taud=target_audience.get(r.get('semanticTarget'))
        if taud and not audience_reference_allowed(saud,taud): leaks.append({**r,'sourceAudience':saud,'targetAudience':taud})
    if leaks: add_check(report,'AUDIENCE_REFERENCE_ISOLATION','ERROR','Player/shared references target GM-only nodes.',leaks)
    else: add_check(report,'AUDIENCE_REFERENCE_ISOLATION','PASS','No player/shared → GM semantic references detected.')

    provenance.sort(key=lambda x:(x.get('kind',''),x.get('sourcePath',''),x.get('semanticId','')))
    source_hashes=sorted({(x['path'],x['sha256']) for x in source_hashes})
    _write_json(meta_root/'provenance.json',provenance)
    _write_json(meta_root/'semantic-targets.json',sorted(semantic_targets,key=lambda x:x['semanticId']))
    _write_json(meta_root/'references.json',references)
    _write_json(meta_root/'assets.json',assets)
    _write_json(meta_root/'runtime-assets.json',runtime_assets)
    _write_json(meta_root/'source-hashes.json',[{'path':p,'sha256':h} for p,h in source_hashes])
    _write_json(meta_root/'validation.json',report)
    return report


def deterministic_build(repo_root: Path,outroot: Path,pub: dict,asm: dict,config: dict,base_report: dict)->dict:
    report=materialize(repo_root,outroot,pub,asm,config,base_report)
    if report['status']!='PASS': return report
    with tempfile.TemporaryDirectory(prefix='cybermancy-rulebook-determinism-') as td:
        second=Path(td)/'rulebook'
        report2=materialize(repo_root,second,pub,asm,config,base_report)
        # validation.json should itself be deterministic; all metadata paths are output-relative.
        same=tree_hash_manifest(outroot)==tree_hash_manifest(second)
        asset_same=tree_hash_manifest(outroot/'source'/'assets')==tree_hash_manifest(second/'source'/'assets')
    add_check(report,'ASSET_TREE_DETERMINISM','PASS' if asset_same and report2['status']=='PASS' else 'ERROR',
              'Two clean materializations produce byte-identical publication asset trees.' if asset_same else 'Publication asset tree differed between clean materializations.')
    add_check(report,'DETERMINISM','PASS' if same and report2['status']=='PASS' else 'ERROR','Two clean materializations are byte-identical.' if same else 'Second clean materialization differed from the first.')
    _write_json(outroot/'source'/'metadata'/'validation.json',report)
    return report
