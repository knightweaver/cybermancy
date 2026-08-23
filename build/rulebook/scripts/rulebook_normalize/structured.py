from __future__ import annotations
import html
import json
import re
from typing import Any
from .markdown import html_to_markdown, html_to_plain_text


_CRITICAL_EFFECT_RE = re.compile(
    r'^\s*Critical\s+Effect\s*:\s*(.+?)\s*$',
    re.IGNORECASE,
)


def get_in(obj: Any, dotted: str, default=None):
    cur = obj
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def is_foundry_folder(doc: dict) -> bool:
    key = doc.get('_key')
    return isinstance(key, str) and '!folders!' in key


def stable_id(doc: dict) -> str:
    value = doc.get('_id')
    if isinstance(value, str) and value:
        return value
    key = doc.get('_key')
    if isinstance(key, str) and key:
        tail = key.rsplit('!', 1)[-1]
        if tail and tail != key:
            return tail
    raise ValueError('STRUCTURED_ID_MISSING')


def semantic_entity_id(family: str, doc: dict) -> str:
    return f'entity:{family}:{stable_id(doc)}'


def clean_text(value: Any) -> str:
    if value is None:
        return ''
    s = str(value)
    return html_to_markdown(s).strip() if '<' in s and '>' in s else html.unescape(s).strip()


def clean_description(value: Any) -> str:
    """Normalize structured description fields to one plain publication string."""
    if value is None:
        return ''
    return html_to_plain_text(str(value))


def _fmt(v: Any) -> str:
    if isinstance(v, bool): return 'Yes' if v else 'No'
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    if isinstance(v, (str, int, float)): return str(v)
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def find_fast_play(doc: dict, paths: list[str]):
    for path in paths:
        fp = get_in(doc, path)
        if isinstance(fp, dict) and fp:
            return path, fp
    return None, None


def render_fast_play(fp: dict) -> str:
    prompts = fp.get('prompts', [])
    goal = fp.get('goal')
    lines = ['::: {.fast-play data-audience="gm"}']
    for p in prompts:
        if not isinstance(p, dict): continue
        label, text = p.get('label'), p.get('text')
        if label and text: lines += [f'**{label}:** {clean_text(text)}', '']
    if goal: lines.append(f'**Goal:** {clean_text(goal)}')
    lines.append(':::')
    return '\n'.join(lines)


def _damage_text(attack: dict) -> str:
    parts = get_in(attack, 'damage.parts', [])
    if not isinstance(parts, list) or not parts: return ''
    out=[]
    for part in parts:
        if not isinstance(part, dict): continue
        val=part.get('value',{}) if isinstance(part.get('value'),dict) else {}
        dice=val.get('dice'); bonus=val.get('bonus')
        formula = ''
        if dice: formula += str(dice)
        if bonus not in (None, '', 0, 0.0):
            try:
                b=float(bonus); formula += ('+' if b>=0 else '-') + _fmt(abs(b))
            except Exception: formula += str(bonus)
        types=part.get('type') or []
        dtype=', '.join(map(str,types)) if isinstance(types,list) else str(types)
        out.append(' '.join(x for x in [formula or '—', dtype] if x))
    return '; '.join(out)


def render_attack(attack: dict) -> str:
    if not isinstance(attack, dict) or not attack: return ''
    name=attack.get('name') or 'Attack'
    roll=attack.get('roll') if isinstance(attack.get('roll'),dict) else {}
    bonus=roll.get('bonus'); trait=roll.get('trait')
    rng=attack.get('range')
    dmg=_damage_text(attack)
    rows=[]
    if trait: rows.append(('Trait', trait))
    if bonus not in (None,''): rows.append(('Attack Bonus', f"{float(bonus):+g}" if isinstance(bonus,(int,float)) else bonus))
    if rng: rows.append(('Range', rng))
    if dmg: rows.append(('Damage', dmg))
    lines=[f'**{clean_text(name)}**', '', '| Attack | Value |', '|---|---|']
    lines += [f'| {a} | {_fmt(b)} |' for a,b in rows]
    return '\n'.join(lines)


def _iter_actions(node: Any):
    if isinstance(node, dict):
        for v in node.values():
            if isinstance(v, dict): yield v
    elif isinstance(node, list):
        for v in node:
            if isinstance(v, dict): yield v


def publication_trait(family: str, doc: dict):
    """Resolve the semantic attack Trait used by publication sorting/rendering."""
    if family == 'weapons':
        return get_in(doc, 'system.attack.roll.trait')
    return get_in(doc, 'system.trait')


def classify_action(family: str, action: dict) -> tuple[str, str]:
    """Translate Foundry action naming into explicit publication semantics."""
    raw_name = str(action.get('name') or 'Action').strip()
    if family == 'weapons':
        match = _CRITICAL_EFFECT_RE.match(raw_name)
        if match:
            return 'critical-effect', match.group(1).strip()
    return 'action', raw_name


def render_action(
    action: dict,
    semantic_type: str = 'action',
    display_name: str | None = None,
) -> str:
    name=display_name or action.get('name') or 'Action'
    desc=clean_description(action.get('description',''))
    kind=action.get('actionType') or action.get('type')
    rng=action.get('range')
    dmg=_damage_text(action)
    meta=[]
    if kind: meta.append(str(kind).replace('_',' ').title())
    if rng: meta.append(f'Range {rng}')
    if dmg: meta.append(f'Damage {dmg}')
    lines=[f'::: {{.feature data-feature-type="{semantic_type}"}}', f'**{clean_text(name)}**' + (f" — *{' · '.join(meta)}*" if meta else '')]
    if desc: lines += ['', desc]
    lines.append(':::')
    return '\n'.join(lines)


def weapon_feature_name(feature: dict) -> str:
    value = feature.get('name') or feature.get('label') or feature.get('value')
    return clean_text(value) if value not in (None, '') else 'Feature'


def _system_description(doc: dict):
    value = get_in(doc, 'system.description')
    if isinstance(value, dict):
        return value.get('value') or ''
    if value not in (None, ''):
        return value
    return get_in(doc, 'system.description.value', '')


def collect_source_warnings(family: str, doc: dict) -> list[dict]:
    """Return non-blocking source-quality warnings for Step 4 validation."""
    warnings=[]
    sid=stable_id(doc)
    name=doc.get('name') or get_in(doc,'identity.name') or sid

    if family == 'weapons' and not _nonempty(publication_trait(family, doc)):
        warnings.append({
            'code':'WEAPON_TRAIT_MISSING',
            'message':f'{name}: weapon attack Trait is missing; it will sort after populated Traits.',
            'details':{
                'family':family,
                'sourceId':sid,
                'name':name,
                'field':'system.attack.roll.trait',
            },
        })
    return warnings


def render_embedded_feature(item: dict) -> str:
    name=item.get('name') or 'Feature'
    desc=clean_description(_system_description(item) or item.get('description',''))
    typ=item.get('type') or 'feature'
    lines=[f'::: {{.feature data-feature-type="{typ}"}}', f'**{clean_text(name)}**']
    if desc: lines += ['', desc]
    actions=get_in(item,'system.actions')
    for action in _iter_actions(actions):
        adesc=clean_description(action.get('description',''))
        if adesc and adesc != desc:
            lines += ['', f'*Action:* {adesc}']
    lines.append(':::')
    return '\n'.join(lines)


def _nonempty(v: Any) -> bool:
    return v not in (None, '', [], {})


def _primitive_leaves(obj: Any, prefix: str=''):
    if isinstance(obj, dict):
        for k in sorted(obj):
            v=obj[k]; p=f'{prefix}.{k}' if prefix else k
            yield from _primitive_leaves(v,p)
    elif isinstance(obj, list):
        if all(not isinstance(x,(dict,list)) for x in obj):
            if obj: yield prefix, obj
        else:
            for i,v in enumerate(obj): yield from _primitive_leaves(v,f'{prefix}[{i}]')
    elif _nonempty(obj):
        yield prefix,obj


SYSTEM_EXCLUDE_PREFIXES = (
    'description', 'tier', 'level', 'type', 'role', 'classification', 'difficulty',
    'burden', 'trait', 'range', 'cost', 'price', 'attack', 'actions', 'features',
    'motivesAndTactics', 'impulses', 'potentialAdversaries', 'experiences',
    'damageThresholds', 'resources', 'weaponFeatures', 'armorFeatures', 'attribution',
    'equipped', 'secondary', 'attached', 'originItemType', 'multiclassOrigin'
)


def _additional_mechanics(system: dict) -> list[tuple[str,Any]]:
    rows=[]
    for path,v in _primitive_leaves(system):
        base=path.split('.',1)[0].split('[',1)[0]
        if base in SYSTEM_EXCLUDE_PREFIXES: continue
        # Foundry implementation wiring does not belong in reader-facing mechanics.
        if any(tok in path for tok in ('systemPath','chatDisplay','_id','img','originItem','baseAction','useDefault')): continue
        rows.append((path,v))
    return rows


def _classification(doc: dict):
    return get_in(doc,'system.type') or get_in(doc,'system.role') or get_in(doc,'system.classification') or get_in(doc,'identity.classification')


def source_sort_value(family: str, doc: dict, source_rel: str, sort_fields: list[str]) -> tuple:
    name=str(doc.get('name') or '').casefold()
    folder='/'.join(source_rel.replace('\\','/').split('/')[:-1]).casefold()
    vals=[]
    for field in sort_fields:
        if field=='name': v=name
        elif field=='tier': v=get_in(doc,'system.tier', get_in(doc,'identity.tier', 999))
        elif field=='trait':
            trait=publication_trait(family,doc)
            # Missing Traits are deterministic but sort after populated Traits.
            v=(1,'') if not _nonempty(trait) else (0,str(trait).casefold())
        elif field=='classification': v=_classification(doc) or ''
        elif field=='source-folder': v=folder
        elif field=='level-or-tier': v=get_in(doc,'system.level', get_in(doc,'system.tier',999))
        elif field=='parent-class-or-source-folder':
            v=(get_in(doc,'system.class') or get_in(doc,'system.parentClass') or folder)
        else: v=get_in(doc,field,'')
        if isinstance(v,str): v=v.casefold()
        vals.append(v)
    vals += [name, stable_id(doc)]
    return tuple(vals)


_RE_MD_IMAGE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+["\'][^"\']*["\'])?\)')
_RE_HTML_IMAGE = re.compile(r'<img\b[^>]*?\bsrc\s*=\s*["\']([^"\']+)["\'][^>]*>', re.I)


def collect_runtime_asset_refs(doc: dict) -> list[str]:
    """Collect Foundry/runtime image wiring for provenance only."""
    refs=[]
    def walk(v: Any, key: str=''):
        if isinstance(v,dict):
            for k,x in v.items(): walk(x,k)
        elif isinstance(v,list):
            for x in v: walk(x,key)
        elif isinstance(v,str) and key in {'img','src','texture'} and v:
            refs.append(v)
    walk(doc)
    return sorted(set(refs))


def collect_publication_asset_refs(rendered_markdown: str) -> list[str]:
    """Collect only images actually emitted into normalized reader content."""
    refs=[]
    refs.extend(m.group(1) for m in _RE_MD_IMAGE.finditer(rendered_markdown))
    refs.extend(m.group(1) for m in _RE_HTML_IMAGE.finditer(rendered_markdown))
    return sorted(set(refs))


def render_entity(family: str, doc: dict, fast_play_paths: list[str]) -> tuple[str, dict]:
    sid=stable_id(doc)
    name=doc.get('name') or get_in(doc,'identity.name')
    if not isinstance(name,str) or not name.strip(): raise ValueError(f'Entity {sid} has no name')
    sem=f'entity:{family}:{sid}'
    warnings=collect_source_warnings(family,doc)
    lines=[f'### {clean_text(name)} {{#{sem} .rb-entity data-family="{family}" data-source-id="{sid}"}}','']

    identity_desc=get_in(doc,'identity.description')
    system_desc=_system_description(doc)
    desc=clean_description(identity_desc or system_desc or '')
    if desc: lines += [desc,'']

    system=doc.get('system') if isinstance(doc.get('system'),dict) else {}
    scalar_specs=[
        ('Tier', get_in(doc,'identity.tier') or system.get('tier')),
        ('Level', system.get('level')),
        ('Classification', _classification(doc)),
        ('Difficulty', get_in(doc,'mechanics.difficulty') or system.get('difficulty')),
        ('Burden', system.get('burden')),
        ('Trait', publication_trait(family,doc)),
        ('Range', system.get('range')),
        ('Cost', system.get('cost') or system.get('price')),
    ]
    rows=[(a,b) for a,b in scalar_specs if _nonempty(b)]
    thresholds=system.get('damageThresholds') if isinstance(system.get('damageThresholds'),dict) else {}
    for k in ('major','severe'):
        if _nonempty(thresholds.get(k)): rows.append((f'{k.title()} Threshold',thresholds[k]))
    resources=system.get('resources') if isinstance(system.get('resources'),dict) else {}
    for key,label in (('hitPoints','HP'),('stress','Stress')):
        r=resources.get(key) if isinstance(resources.get(key),dict) else {}
        if _nonempty(r.get('max')): rows.append((label,r.get('max')))
    if rows:
        lines += ['::: {.stat-block}','| Stat | Value |','|---|---|']
        lines += [f'| {a} | {_fmt(b)} |' for a,b in rows]
        lines += [':::','']

    motives=system.get('motivesAndTactics') or get_in(doc,'design.motivesAndTactics')
    if motives:
        if isinstance(motives,list): motives=', '.join(map(str,motives))
        lines += [f'**Motives & Tactics:** {clean_text(motives)}','']
    impulses=system.get('impulses') or get_in(doc,'mechanics.impulses')
    if impulses:
        if isinstance(impulses,list): impulses=', '.join(map(str,impulses))
        lines += [f'**Impulses:** {clean_text(impulses)}','']
    potential=system.get('potentialAdversaries') or get_in(doc,'mechanics.potentialAdversaries')
    if potential:
        if isinstance(potential,list): potential=', '.join(map(str,potential))
        lines += [f'**Potential Adversaries:** {clean_text(potential)}','']
    experiences=system.get('experiences')
    if isinstance(experiences,dict) and experiences:
        exp=[]
        for e in experiences.values():
            if isinstance(e,dict) and e.get('name'): exp.append(f"{e['name']} +{e.get('value',0)}")
        if exp: lines += [f"**Experiences:** {', '.join(exp)}",'']

    attack=system.get('attack')
    if isinstance(attack,dict) and attack:
        lines += ['#### Attack','',render_attack(attack),'']

    action_names=[]
    critical_effect_names=[]
    actions=list(_iter_actions(system.get('actions')))
    if family == 'weapons':
        ordinary=[]; critical=[]
        for action in actions:
            semantic_type,display_name=classify_action(family,action)
            if semantic_type=='critical-effect':
                critical.append((action,display_name)); critical_effect_names.append(display_name)
            else:
                ordinary.append((action,display_name)); action_names.append(display_name)
        if ordinary:
            lines += ['#### Actions','']
            for action,display_name in ordinary:
                lines += [render_action(action,'action',display_name),'']
        if critical:
            lines += ['#### Critical Effects','']
            for action,display_name in critical:
                lines += [render_action(action,'critical-effect',display_name),'']
    elif actions:
        lines += ['#### Actions','']
        for action in actions:
            lines += [render_action(action),'']

    # Item-family feature nodes.
    weapon_feature_names=[]
    for feature_key in ('weaponFeatures','armorFeatures','features'):
        features=system.get(feature_key)
        vals=list(_iter_actions(features)) if isinstance(features,dict) else (features if isinstance(features,list) else [])
        if vals:
            lines += [f'#### {feature_key.replace("Features"," Features").replace("weapon","Weapon").replace("armor","Armor").strip()}','']
            for f in vals:
                if not isinstance(f,dict): continue
                if family=='weapons' and feature_key=='weaponFeatures':
                    fname=weapon_feature_name(f)
                    feature_type='weapon-feature'
                    weapon_feature_names.append(fname)
                else:
                    fname=f.get('name') or f.get('label') or f.get('value') or 'Feature'
                    feature_type='feature'
                rules=f.get('rules') or f.get('description') or get_in(f,'system.description') or get_in(f,'system.description.value') or ''
                lines += [f'::: {{.feature data-feature-type="{feature_type}"}}',f'**{clean_text(fname)}**']
                if rules: lines += ['',clean_text(rules)]
                lines += [':::','']

    # Actor embedded feature items are the authoritative actor feature payload.
    embedded=doc.get('items')
    if isinstance(embedded,list) and embedded:
        rendered=[render_embedded_feature(x) for x in embedded if isinstance(x,dict) and x.get('type') in {'feature','domainCard','subclass','class'}]
        if rendered:
            lines += ['#### Features','']
            for r in rendered: lines += [r,'']

    fp_path,fp=find_fast_play(doc,fast_play_paths)
    fast_meta=None
    if fp:
        lines += ['#### Fast Play','',render_fast_play(fp),'']
        fast_meta={'sourcePath':fp_path,'featureRefs':[ref for p in fp.get('prompts',[]) if isinstance(p,dict) for ref in p.get('featureRefs',[]) if isinstance(ref,str)]}

    additional=_additional_mechanics(system)
    if additional:
        lines += ['#### Additional Mechanics','', '| Field | Value |','|---|---|']
        for path,v in additional:
            lines.append(f'| `{path}` | {_fmt(v).replace("|","\\|")} |')
        lines.append('')

    rendered_markdown='\n'.join(lines).rstrip()+'\n'
    metadata={
        'semanticId':sem,'sourceId':sid,'name':name,'family':family,
        'fastPlay':fast_meta,
        'warnings':warnings,
        # Only images actually emitted into normalized reader content are
        # publication assets. Foundry image wiring is retained separately as
        # non-blocking runtime provenance.
        'assetRefs':collect_publication_asset_refs(rendered_markdown),
        'runtimeAssetRefs':collect_runtime_asset_refs(doc),
    }
    if family=='weapons':
        metadata['weaponSemantics']={
            'trait':publication_trait(family,doc),
            'weaponFeatures':weapon_feature_names,
            'actions':action_names,
            'criticalEffects':critical_effect_names,
        }
    return rendered_markdown,metadata