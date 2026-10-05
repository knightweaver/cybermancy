/* GM-only, read-only SVG atlas. No external graph dependency or browser writes. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const TYPES = ['directs', 'supports', 'exploits', 'opposes', 'competes'];
  let serial = 0;
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const svgEl = (tag, attrs = {}, text) => {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function wrap(text, width = 30) {
    const lines = [''];
    for (const word of text.split(/\s+/)) {
      if ((lines.at(-1) + ' ' + word).trim().length > width && lines.at(-1)) lines.push(word);
      else lines[lines.length - 1] = (lines.at(-1) + ' ' + word).trim();
    }
    return lines;
  }
  async function init(root) {
    if (!root || root.dataset.initialized) return;
    root.dataset.initialized = 'true';
    const q = key => root.querySelector(`[data-sa="${key}"]`);
    const svg = q('svg'), scene = q('scene'), panel = q('details');
    const prefix = `sa-${++serial}-`;
    let data;
    try {
      const response = await fetch(new URL(root.dataset.source, document.baseURI));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      data = await response.json();
      if (data.audience !== 'gm' || data.schemaVersion !== 1) throw new Error('Unsupported scheme data');
    } catch (error) {
      q('status').textContent = `Unable to load scheme atlas: ${error.message}. Reload to retry.`;
      delete root.dataset.initialized;
      return;
    }
    if (!root.isConnected) return;
    const schemes = new Map(data.schemes.map(s => [s.id, s]));
    const entities = new Map(data.entities.map(e => [e.id, e]));
    let selected = null, neighborsOnly = false, override = false;
    let points = new Map(), visible = [], edges = [], labels = [];
    let camera = {x:0,y:0,k:1}, bounds = {x:0,y:0,w:1000,h:700};
    let drag = null, suppressClick = false;
    const types = new Set(TYPES);
    for (const entity of data.entities) {
      const option = el('option', entity.name); option.value = entity.id; q('entity').append(option);
      const legend = el('span'); const swatch = el('i', undefined, 'sa-swatch');
      swatch.style.background = entity.color; legend.append(swatch, document.createTextNode(entity.name)); q('legend').append(legend);
    }
    for (const type of TYPES) {
      const label = el('label'), input = el('input'); input.type = 'checkbox'; input.value = type; input.checked = true;
      label.append(input, document.createTextNode(type)); q('types').append(label);
      input.addEventListener('change', () => { input.checked ? types.add(type) : types.delete(type); override = false; render(); });
    }
    const defs = svgEl('defs');
    for (const [name, color] of [['directs','#9cb0c8'],['supports','#7dccb0'],['exploits','#f2c35c'],['opposes','#f47f91'],['competes','#bca6da']]) {
      const marker = svgEl('marker', {id:prefix+name,viewBox:'0 0 12 12',refX:10,refY:6,markerWidth:9,markerHeight:9,orient:'auto-start-reverse',markerUnits:'userSpaceOnUse'});
      marker.append(svgEl('path', {d:['opposes','competes'].includes(name)?'M 10 0 L 10 12':'M 0 1 L 10 6 L 0 11 Z',stroke:color,'stroke-width':2,fill:['opposes','competes'].includes(name)?'none':color}));
      defs.append(marker);
    }
    svg.prepend(defs);
    function related(id) {
      return data.relationships.filter(e => e.source === id || e.target === id);
    }
    function neighborhood() {
      const ids = new Set(selected ? [selected] : []);
      if (selected) for (const e of related(selected)) { ids.add(e.source); ids.add(e.target); }
      return ids;
    }
    function matches(s) {
      const search = q('search').value.trim().toLowerCase();
      const awareness = q('awareness').value;
      return (!q('entity').value || s.entity === q('entity').value)
        && (!q('approval').value || s.approval === q('approval').value)
        && (!search || JSON.stringify(s).toLowerCase().includes(search) || entities.get(s.entity).name.toLowerCase().includes(search))
        && (!awareness || (awareness === 'queued' ? s.awareness.selectedForIntroduction : awareness === 'revealed' ? s.awareness.revealed : !s.awareness.revealed));
    }
    function layout(expanded) {
      points = new Map(); labels = [];
      const groups = data.entities;
      // Five Council columns and three Cabal columns; independents form the lower band.
      // Compact spacing is deliberate: overview IDs stay readable in ordinary docs width.
      for (let i = 0; i < groups.length; i++) {
        const e = groups[i]; const independent = i >= 8;
        const col = independent ? i - 8 : i;
        const x = 45 + col * 132, baseY = independent ? 470 : 65;
        labels.push({x:x-28,y:baseY-22,text:e.id === 'aurum' ? 'Aurum Rex / Helios' : e.name.split(' ')[0]});
        const list = visible.filter(s => s.entity === e.id).sort((a,b) => (a.layer === b.layer ? 0 : a.layer === 'strategic' ? -1 : 1));
        list.forEach((s,j) => {
          const lines = expanded.has(s.id) ? wrap(s.title) : [];
          const w = lines.length ? 230 : 70, h = lines.length ? 38 + lines.length*16 : 36;
          points.set(s.id, {x,y:baseY+j*66,w,h,lines});
        });
      }
      // Bring immediate neighbors around the selected scheme's original anchor.
      // Other entities keep compact positions and yield to expanded rectangles.
      if (selected && points.has(selected)) {
        const anchor=points.get(selected);
        const offsets=[[-255,-110],[0,-120],[255,-110],[-255,10],[255,10],[-255,130],[0,130],[255,130]];
        const neighbors=visible.filter(s=>expanded.has(s.id)&&s.id!==selected);
        neighbors.forEach((s,i)=>{
          const [dx,dy]=offsets[i] || [((i-8)%3-1)*255,250+Math.floor((i-8)/3)*120];
          const p=points.get(s.id);p.x=anchor.x+dx;p.y=anchor.y+dy;
        });
      }
      // Resolve rectangles locally, preserving the selected node as the fixed anchor.
      const ordered = visible.slice().sort((a,b) => (a.id === selected ? -1 : b.id === selected ? 1 : expanded.has(a.id) === expanded.has(b.id) ? 0 : expanded.has(a.id) ? -1 : 1));
      const placed = [];
      for (const s of ordered) {
        const p = points.get(s.id);
        let attempts = 0;
        while (placed.some(v => Math.abs(p.x-v.x) < (p.w+v.w)/2+16 && Math.abs(p.y-v.y) < (p.h+v.h)/2+18) && attempts++ < 200) p.y += 24;
        placed.push(p);
      }
      const ps = [...points.values()];
      if (ps.length) {
        const minX=Math.min(...ps.map(p=>p.x-p.w/2))-25, maxX=Math.max(...ps.map(p=>p.x+p.w/2))+25;
        const minY=Math.min(0,...ps.map(p=>p.y-p.h/2))-25,maxY=Math.max(...ps.map(p=>p.y+p.h/2))+40;
        bounds={x:minX,y:minY,w:maxX-minX,h:maxY-minY};
      } else bounds={x:0,y:0,w:1000,h:700};
    }
    function transform() { scene.setAttribute('transform',`translate(${camera.x} ${camera.y}) scale(${camera.k})`); }
    function fit() {
      const r=svg.getBoundingClientRect();
      camera.k=Math.max(.2,Math.min(1.4,(r.width-35)/bounds.w,(r.height-35)/bounds.h));
      camera.x=(r.width-bounds.w*camera.k)/2-bounds.x*camera.k;
      camera.y=(r.height-bounds.h*camera.k)/2-bounds.y*camera.k; transform();
    }
    function zoom(factor, cx=svg.clientWidth/2, cy=svg.clientHeight/2) {
      const k=Math.max(.2,Math.min(3,camera.k*factor));
      camera.x=cx-(cx-camera.x)*k/camera.k; camera.y=cy-(cy-camera.y)*k/camera.k; camera.k=k; transform();
    }
    function section(title, text) { panel.append(el('h3',title),el('p',text || 'None recorded.')); }
    function records(title, list) {
      panel.append(el('h3',`${title} (${list.length})`));
      if (!list.length) { panel.append(el('p','None recorded.')); return; }
      for (const item of list) {
        panel.append(el('p',item.title),el('p',`${item.status} · ${item.revealed ? 'Revealed' : 'Not revealed'}`,'sa-meta'),el('p',item.description));
        if (item.url) {
          const url = new URL(item.url, document.baseURI);
          if (['https:','http:'].includes(url.protocol)) { const a=el('a','Open document'); a.href=url.href; panel.append(a); }
        }
      }
    }
    function details() {
      panel.replaceChildren();
      if (!selected) { panel.append(el('h2','Select a scheme'),el('p','Choose a colored identifier to expand its title and all immediate neighbors. The overview displays every relationship permitted by the filters.')); return; }
      const s=schemes.get(selected), entity=entities.get(s.entity);
      panel.append(el('h2',`${s.id} · ${s.title}`),el('p',`${entity.name} · ${entity.affiliation} · ${s.layer} · ${s.scope}`,'sa-meta'));
      section('Status',`${s.approval} · ${s.awareness.selectedForIntroduction?'Queued for introduction':'Not selected for introduction'} · ${s.awareness.revealed?'Revealed to players':'Not revealed'}`);
      section('Objective',s.objective); section('Plan',s.plan); section('Consequences',s.consequences);
      if (s.projects.length) section('Projects',s.projects.join('; '));
      if (s.notes) section('Vulnerabilities / canon notes',s.notes);
      records('Missions / hooks',s.missions); records('Rumors',s.rumors);
      section('Player knowledge',s.awareness.knowledge);
      panel.append(el('h3','Relationships'));
      for (const edge of related(s.id)) {
        const out=edge.source===s.id, other=schemes.get(out?edge.target:edge.source);
        const hidden=!edges.includes(edge);
        const b=el('button',`${out?'→':'←'} ${edge.type} · ${other.id}: ${other.title}${hidden?' [hidden by filters]':''}${edge.conditional?' [conditional]':''}`);
        b.type='button'; b.addEventListener('click',()=>select(other.id)); panel.append(b);
        if (edge.note) panel.append(el('p',edge.note,'sa-meta'));
      }
      if (!related(s.id).length) panel.append(el('p','No scheme relationships recorded.'));
    }
    function select(id) {
      selected=id; override=false; render();
      const ps=[...neighborhood()].map(key=>points.get(key)).filter(Boolean);
      const left=Math.min(...ps.map(p=>p.x-p.w/2)),right=Math.max(...ps.map(p=>p.x+p.w/2));
      const top=Math.min(...ps.map(p=>p.y-p.h/2)),bottom=Math.max(...ps.map(p=>p.y+p.h/2));
      camera.k=Math.min(1.15,(svg.clientWidth-40)/(right-left),(svg.clientHeight-40)/(bottom-top));
      camera.x=svg.clientWidth/2-(left+right)/2*camera.k;camera.y=svg.clientHeight/2-(top+bottom)/2*camera.k;transform();
      panel.scrollTop=0;
    }
    function endpoint(p, target) {
      const dx=target.x-p.x,dy=target.y-p.y;
      const ratio=Math.min(dx? p.w/2/Math.abs(dx):Infinity,dy?p.h/2/Math.abs(dy):Infinity);
      return {x:p.x+dx*ratio,y:p.y+dy*ratio};
    }
    function render() {
      const near=neighborhood();
      visible=data.schemes.filter(s => (matches(s) || s.id===selected || override&&near.has(s.id)) && (!neighborsOnly || !selected || near.has(s.id)));
      const ids=new Set(visible.map(s=>s.id));
      edges=data.relationships.filter(e=>ids.has(e.source)&&ids.has(e.target)&&(types.has(e.type)||override&&near.has(e.source)&&near.has(e.target)));
      const expanded=new Set(selected ? visible.filter(s=>near.has(s.id)).map(s=>s.id) : []);
      layout(expanded); scene.replaceChildren();
      if (!selected) {
        scene.append(svgEl('text',{x:12,y:18,class:'sa-band-title'},'COUNCIL'),svgEl('text',{x:660,y:18,class:'sa-band-title'},'CABAL'),svgEl('text',{x:12,y:425,class:'sa-band-title'},'INDEPENDENT MEGACORPS'));
        for (const label of labels) scene.append(svgEl('text',{x:label.x,y:label.y,class:'sa-group-title'},label.text));
      }
      const edgeLayer=svgEl('g'); scene.append(edgeLayer);
      for (const e of edges) {
        const p=points.get(e.source),t=points.get(e.target),a=endpoint(p,t),b=endpoint(t,p);
        const peers=edges.filter(v=>(v.source===e.source&&v.target===e.target)||(v.source===e.target&&v.target===e.source));
        const offset=(peers.indexOf(e)-(peers.length-1)/2)*24;
        const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;
        const mx=(a.x+b.x)/2-dy/len*offset,my=(a.y+b.y)/2+dx/len*offset;
        const active=!selected||e.source===selected||e.target===selected;
        const group=svgEl('g',{class:'sa-edge','data-type':e.type,'data-source':e.source,'data-target':e.target,tabindex:0,role:'img','aria-label':`${e.source} ${e.type} ${e.target}${e.conditional?' (conditional)':''}`,opacity:active?1:.12});
        group.append(svgEl('title',{},`${e.source} ${e.type} ${e.target}${e.conditional?' (conditional)':''}${e.note?' — '+e.note:''}`));
        const path=svgEl('path',{d:`M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`,'marker-end':`url(#${prefix+e.type})`});
        if(e.type==='competes') path.setAttribute('marker-start',`url(#${prefix+e.type})`);
        group.append(path);
        if(selected&&active) group.append(svgEl('text',{x:mx,y:my-5,'text-anchor':'middle',class:'sa-edge-label'},e.type+(e.conditional?' ?':'')));
        edgeLayer.append(group);
      }
      for (const s of visible) {
        const p=points.get(s.id),entity=entities.get(s.entity);
        const node=svgEl('g',{class:'sa-node','data-id':s.id,transform:`translate(${p.x-p.w/2} ${p.y-p.h/2})`,tabindex:0,role:'button','aria-label':`${s.id}: ${s.title}${s.awareness.selectedForIntroduction?', queued':''}${s.awareness.revealed?', revealed':''}`,'aria-pressed':s.id===selected,opacity:!selected||near.has(s.id)?1:.22});
        node.append(svgEl('title',{},`${s.id}: ${s.title} — ${entity.name}`),svgEl('rect',{width:p.w,height:p.h,rx:8,fill:entity.color}),svgEl('text',{x:12,y:23},s.id));
        p.lines.forEach((line,i)=>node.append(svgEl('text',{x:12,y:43+i*16,class:'sa-title'},line)));
        if(s.awareness.selectedForIntroduction) node.append(svgEl('text',{x:p.w-(s.awareness.revealed?28:14),y:-3,class:'sa-badge',style:'fill:#e8eef6'},'◆'));
        if(s.awareness.revealed) node.append(svgEl('text',{x:p.w-14,y:-3,class:'sa-badge',style:'fill:#e8eef6'},'●'));
        node.addEventListener('click',()=>{if(!suppressClick)select(s.id);});
        node.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select(s.id);root.querySelector(`[data-id="${s.id}"]`)?.focus();}});
        scene.append(node);
      }
      details(); transform();
      const hidden=selected?related(selected).filter(e=>!edges.includes(e)).length:0;
      q('status').textContent=`${data.schemes.length} schemes · ${visible.length} visible · ${edges.length} relationships · ${data.schemes.filter(s=>s.awareness.selectedForIntroduction).length} queued · ${data.schemes.filter(s=>s.awareness.revealed).length} revealed${hidden?` · ${hidden} selected relationships hidden by filters`:''}${!visible.length?' · No matches':''}`;
      q('neighbors').setAttribute('aria-pressed',neighborsOnly);
      q('all-related').disabled=!selected;
    }
    for(const key of ['entity','awareness','approval'])q(key).addEventListener('change',()=>{override=false;render();fit();});
    q('search').addEventListener('input',()=>{override=false;render();fit();});
    q('overview').addEventListener('click',()=>{selected=null;neighborsOnly=false;override=false;render();fit();});
    q('neighbors').addEventListener('click',()=>{neighborsOnly=!neighborsOnly;render();fit();});
    q('all-related').addEventListener('click',()=>{override=true;render();fit();});
    q('fit').addEventListener('click',fit);q('plus').addEventListener('click',()=>zoom(1.25));q('minus').addEventListener('click',()=>zoom(.8));
    q('panel').addEventListener('click',()=>{const hidden=root.classList.toggle('sa-panel-hidden');q('panel').textContent=hidden?'Show details':'Hide details';q('panel').setAttribute('aria-expanded',!hidden);});
    q('fullscreen').addEventListener('click',()=>{const full=root.classList.toggle('sa-fullscreen');q('fullscreen').setAttribute('aria-pressed',full);q('fullscreen').textContent=full?'Exit full screen':'Full screen';fit();});
    root.addEventListener('keydown',event=>{if(event.key==='Escape'){if(root.classList.contains('sa-fullscreen')){root.classList.remove('sa-fullscreen');q('fullscreen').setAttribute('aria-pressed','false');q('fullscreen').textContent='Full screen';}else {selected=null;neighborsOnly=false;override=false;render();}fit();}});
    svg.addEventListener('wheel',event=>{event.preventDefault();const r=svg.getBoundingClientRect();zoom(event.deltaY<0?1.1:1/1.1,event.clientX-r.left,event.clientY-r.top);},{passive:false});
    svg.addEventListener('pointerdown',event=>{if(event.button!==0||event.target.closest('.sa-node'))return;drag={x:event.clientX,y:event.clientY,cx:camera.x,cy:camera.y};suppressClick=false;svg.setPointerCapture(event.pointerId);});
    svg.addEventListener('pointermove',event=>{if(!drag)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y;if(Math.hypot(dx,dy)>4)suppressClick=true;camera.x=drag.cx+dx;camera.y=drag.cy+dy;transform();});
    const endDrag=()=>{drag=null;setTimeout(()=>{suppressClick=false;},0);};svg.addEventListener('pointerup',endDrag);svg.addEventListener('pointercancel',endDrag);
    const observer=new ResizeObserver(()=>{if(!selected)fit();}); observer.observe(q('graph'));
    // Material replaces the content on instant navigation. Disconnect observers for removed roots.
    const removal=new MutationObserver(()=>{if(!root.isConnected){observer.disconnect();removal.disconnect();}});removal.observe(document.body,{childList:true,subtree:true});
    render();fit();
  }
  const mount=()=>init(document.getElementById('scheme-atlas'));
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
  if(typeof document$!=='undefined')document$.subscribe(mount);
})();
