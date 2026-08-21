#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

from rulebook_normalize.manifest import load_json, candidate_collections, ManifestError, resolve_pointer
from rulebook_normalize.pipeline import manifest_contract_report, repository_preflight, deterministic_build
from rulebook_normalize.validate import new_report, add_check, sum_expected_family_counts


def load_config(path: Path): return load_json(path)


def inspect(args):
    pub=load_json(Path(args.publication_manifest)); asm=load_json(Path(args.assembly_manifest))
    result={'publicationCandidates':candidate_collections(pub),'assemblyCandidates':candidate_collections(asm)}
    print(json.dumps(result,indent=2,ensure_ascii=False)); return 0


def preflight(args, include_repo=True):
    config=load_config(Path(args.config)); report=new_report()
    pub_path=Path(args.publication_manifest); asm_path=Path(args.assembly_manifest)
    if not pub_path.exists(): add_check(report,'PUBLICATION_MANIFEST_PRESENT','BLOCKED',f'Required frozen manifest not found: {pub_path}')
    else: add_check(report,'PUBLICATION_MANIFEST_PRESENT','PASS',str(pub_path))
    if not asm_path.exists(): add_check(report,'ASSEMBLY_MANIFEST_PRESENT','BLOCKED',f'Required frozen manifest not found: {asm_path}')
    else: add_check(report,'ASSEMBLY_MANIFEST_PRESENT','PASS',str(asm_path))
    expected_sum=sum_expected_family_counts(config)
    add_check(report,'EXPECTED_STRUCTURED_COUNT','PASS' if expected_sum==config['baseline']['expectedLogicalEntities'] else 'ERROR',f"Configured family counts sum to {expected_sum}; baseline expects {config['baseline']['expectedLogicalEntities']}.")
    if not (pub_path.exists() and asm_path.exists()): return report,None,None,config
    pub=load_json(pub_path); asm=load_json(asm_path)
    bindings=config.get('manifestAdapter',{}); unresolved=[]
    for manifest_name,doc,section in (('publication',pub,bindings.get('publication',{})),('assembly',asm,bindings.get('assembly',{}))):
        for key,ptr in section.items():
            if key=='notes': continue
            if ptr is None: unresolved.append(f'{manifest_name}.{key}')
            else:
                try: resolve_pointer(doc,ptr)
                except ManifestError as e: add_check(report,'MANIFEST_BINDING_INVALID','ERROR',str(e))
    if unresolved:
        add_check(report,'MANIFEST_BINDINGS','BLOCKED','Manifest files are present but strict adapter bindings are not configured.',unresolved)
        return report,pub,asm,config
    add_check(report,'MANIFEST_BINDINGS','PASS','All configured JSON pointers resolve.')
    contract=manifest_contract_report(pub,asm,config)
    for item in contract['checks']:
        if item['status']=='PASS': add_check(report,item['code'],'PASS',item['message'],item.get('details'))
        elif item['status']=='WARNING': add_check(report,item['code'],'WARNING',item['message'],item.get('details'))
        elif item['status']=='BLOCKED': add_check(report,item['code'],'BLOCKED',item['message'],item.get('details'))
        else: add_check(report,item['code'],'ERROR',item['message'],item.get('details'))
    if include_repo and report['status']=='PASS': repository_preflight(Path(args.repo_root),pub,asm,config,report)
    return report,pub,asm,config


def command_validate(args):
    report,_,_,_=preflight(args,include_repo=True)
    print(json.dumps(report,indent=2,ensure_ascii=False)); return 0 if report['status']=='PASS' else 2


def command_build(args):
    report,pub,asm,config=preflight(args,include_repo=True)
    outroot=Path(args.output_root)
    if report['status']!='PASS':
        meta=outroot/'source'/'metadata'; meta.mkdir(parents=True,exist_ok=True)
        (meta/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2,ensure_ascii=False)); return 2
    report=deterministic_build(Path(args.repo_root),outroot,pub,asm,config,report)
    print(json.dumps(report,indent=2,ensure_ascii=False)); return 0 if report['status']=='PASS' else 2


def parser():
    p=argparse.ArgumentParser(description='Cybermancy Step 4 rulebook normalizer')
    sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('build','validate','inspect-manifests'):
        s=sub.add_parser(name); s.add_argument('--publication-manifest',required=True); s.add_argument('--assembly-manifest',required=True)
        if name!='inspect-manifests':
            s.add_argument('--config',required=True); s.add_argument('--repo-root',default='.'); s.add_argument('--output-root',default='build/rulebook')
    return p


def main():
    args=parser().parse_args()
    if args.cmd=='inspect-manifests': return inspect(args)
    if args.cmd=='validate': return command_validate(args)
    if args.cmd=='build': return command_build(args)
    return 2

if __name__=='__main__': raise SystemExit(main())
