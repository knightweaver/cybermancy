import {readFileSync, existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const fail = message => { throw new Error(message); };
const requireValue = (ok, message) => { if (!ok) fail(message); };
const read = path => readFileSync(resolve(root,path),'utf8');
const data = JSON.parse(read('docs/gm-facing/assets/schemes/schemes.json'));
const types = new Set(['directs','supports','exploits','opposes','competes']);
const entities = new Map(), schemes = new Map(), ids = new Set();
const unique = (id, scope) => { requireValue(typeof id==='string' && /^[A-Za-z0-9][A-Za-z0-9-]*$/.test(id),`Invalid ${scope} ID: ${id}`); requireValue(!ids.has(`${scope}:${id}`),`Duplicate ${scope} ID: ${id}`); ids.add(`${scope}:${id}`); };
const text = (record, key, allowEmpty=false) => requireValue(typeof record[key]==='string' && (allowEmpty || record[key].trim().length),`Missing text ${record.id}.${key}`);
requireValue(data.schemaVersion===1 && data.audience==='gm','Scheme data must be version 1 and GM-only');
requireValue(Array.isArray(data.entities) && Array.isArray(data.schemes) && Array.isArray(data.relationships),'Missing data arrays');
for(const e of data.entities){
  unique(e.id,'entity');text(e,'name');
  requireValue(['council','cabal','independent'].includes(e.affiliation),`Invalid affiliation: ${e.id}`);
  requireValue(/^#[0-9a-fA-F]{6}$/.test(e.color),`Invalid entity color: ${e.id}`);entities.set(e.id,e);
}
for(const s of data.schemes){
  unique(s.id,'scheme');requireValue(entities.has(s.entity),`Unknown entity: ${s.id}`);
  for(const key of ['title','scope','objective','plan','consequences'])text(s,key);
  text(s,'notes',true);
  requireValue(['corporate','strategic'].includes(s.layer),`Invalid layer: ${s.id}`);
  requireValue(['approved','proposed','retired'].includes(s.approval),`Invalid approval: ${s.id}`);
  requireValue(Array.isArray(s.projects) && s.projects.every(p=>typeof p==='string'),'Invalid projects: '+s.id);
  requireValue(s.awareness && typeof s.awareness.selectedForIntroduction==='boolean' && typeof s.awareness.revealed==='boolean' && typeof s.awareness.knowledge==='string',`Invalid awareness: ${s.id}`);
  for(const kind of ['missions','rumors']){
    requireValue(Array.isArray(s[kind]),`Missing ${kind}: ${s.id}`);
    for(const record of s[kind]){
      unique(record.id,'record');for(const key of ['title','description','status'])text(record,key);text(record,'url',true);
      const statuses=kind==='missions'?['draft-hook','available','active','completed','failed','withdrawn']:['draft','available','retired'];
      requireValue(statuses.includes(record.status),`Invalid ${kind} status: ${record.id}`);
      requireValue(typeof record.revealed==='boolean',`Invalid exposure: ${record.id}`);
      requireValue(!record.revealed||s.awareness.revealed,`Revealed record requires revealed scheme: ${record.id}`);
      requireValue(!record.revealed||s.awareness.knowledge.trim(),`Revealed record requires player knowledge: ${record.id}`);
      if(record.url)requireValue(!/^(?:javascript|data|file):/i.test(record.url),`Unsafe record URL: ${record.id}`);
    }
  }
  schemes.set(s.id,s);
}
const signatures=new Set();
for(const r of data.relationships){
  unique(r.id,'relationship');
  requireValue(schemes.has(r.source)&&schemes.has(r.target)&&r.source!==r.target,`Invalid endpoints: ${r.id}`);
  requireValue(types.has(r.type),`Unknown type: ${r.id}`);text(r,'note',true);
  requireValue(typeof r.conditional==='boolean',`Missing conditional flag: ${r.id}`);
  requireValue(!r.conditional||r.note.trim(),`Conditional relationship needs an explanation: ${r.id}`);
  const pair=r.type==='competes'?[r.source,r.target].sort().join(':'):`${r.source}:${r.target}`;
  const key=r.type+':'+pair;requireValue(!signatures.has(key),`Duplicate relation: ${r.id}`);signatures.add(key);
}
const gm=read('mkdocs.gm.yml');
for(const p of ['world/scheme-atlas.md','world/scheme-atlas-workflow.md','js/scheme-atlas.js','styles/scheme-atlas.css']){
  requireValue(existsSync(resolve(root,'docs/gm-facing',p)),`Missing GM asset: ${p}`);
  requireValue(gm.includes(p),`GM configuration missing ${p}`);
  requireValue(!existsSync(resolve(root,'docs/player-facing',p)),`Scheme asset must not exist in Player docs: ${p}`);
}
requireValue(!existsSync(resolve(root,'docs/player-facing/assets/schemes/schemes.json')),'Scheme data must not exist in Player docs');
for(const config of ['mkdocs.player.yml','mkdocs.player.staged.yml'])if(existsSync(resolve(root,config)))requireValue(!read(config).includes('scheme-atlas')&&!read(config).includes('assets/schemes'),'Player configuration references GM schemes');
console.log(`Scheme atlas PASS: ${schemes.size} schemes, ${entities.size} entities, ${data.relationships.length} relationships, ${data.schemes.reduce((n,s)=>n+s.missions.length,0)} mission records.`);
