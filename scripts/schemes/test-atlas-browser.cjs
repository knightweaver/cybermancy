const {chromium}=require(process.env.SCHEME_ATLAS_PLAYWRIGHT || 'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
const base=path.resolve(__dirname, '../../_site');
const data=JSON.parse(fs.readFileSync(base+'/gm/assets/schemes/schemes.json','utf8'));
(async()=>{const server=http.createServer((req,res)=>{let p=path.join(base,decodeURIComponent(req.url.split('?')[0]));if(p.endsWith('/'))p+='index.html';if(!fs.existsSync(p)){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.json':'application/json','.html':'text/html','.svg':'image/svg+xml','.png':'image/png'})[path.extname(p)]||'application/octet-stream');res.end(fs.readFileSync(p));});await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true,executablePath:process.env.SCHEME_ATLAS_BROWSER || undefined,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
const p=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
const ctl=k=>p.locator(`[data-sa=${k}]`);const count=(s)=>p.locator(s).count();const overview=async()=>{await ctl('overview').click();};
try{
await p.goto(origin+'/gm/world/scheme-atlas/');await p.waitForSelector('.sa-node');assert.equal(await count('.sa-node'),data.schemes.length);assert.equal(await count('.sa-edge'),data.relationships.length);assert.equal(await count('.sa-title'),0);

for(const type of ['directs','supports','exploits','opposes','competes'])assert.ok(await count(`.sa-edge[data-type=${type}]`)>0);
assert.equal(await p.locator('.sa-edge[data-type=opposes] path').first().getAttribute('marker-end').then(x=>x.includes('opposes')),true);
assert.equal(await p.locator('.sa-edge[data-type=competes] path').first().getAttribute('marker-start').then(x=>x.includes('competes')),true);
await p.locator('[data-id=D1]').click();assert.ok(await ctl('details').textContent().then(x=>x.includes('ferry operator')));
const expected=new Set(['D1']);for(const r of data.relationships)if(r.source==='D1'||r.target==='D1'){expected.add(r.source);expected.add(r.target);}
const expanded=await p.locator('.sa-node').evaluateAll(ns=>ns.filter(n=>n.querySelector('.sa-title')).map(n=>n.dataset.id));assert.deepEqual(new Set(expanded),expected);

await ctl('entity').selectOption('dominion');assert.ok(await ctl('status').textContent().then(x=>x.includes('hidden by filters')));await ctl('all-related').click();for(const id of expected)assert.equal(await count(`[data-id=${id}]`),1);
await ctl('neighbors').click();assert.equal(await count('.sa-node'),expected.size);
await ctl('entity').selectOption('');await overview();
await p.locator('[data-sa=types] input[value=opposes]').uncheck();assert.equal(await count('.sa-edge[data-type=opposes]'),0);await p.locator('[data-sa=types] input[value=opposes]').check();
await ctl('search').fill('zzzz-no-match');assert.equal(await count('.sa-node'),0);assert.ok(await ctl('status').textContent().then(x=>x.includes('No matches')));await ctl('search').fill('');
await p.locator('[data-id=CA1]').focus();await p.keyboard.press('Enter');assert.ok(await ctl('details').textContent().then(x=>x.includes('Golden Commonwealth')));await p.keyboard.press('Escape');assert.equal(await count('.sa-title'),0);
await ctl('panel').click();assert.equal(await ctl('details').isVisible(),false);await ctl('panel').click();
const tr=await ctl('scene').getAttribute('transform');await ctl('plus').click();assert.notEqual(await ctl('scene').getAttribute('transform'),tr);await ctl('fit').click();
await ctl('fullscreen').click();assert.equal(await p.locator('#scheme-atlas').evaluate(n=>n.classList.contains('sa-fullscreen')),true);await p.keyboard.press('Escape');assert.equal(await p.locator('#scheme-atlas').evaluate(n=>n.classList.contains('sa-fullscreen')),false);
// All selection neighborhoods and local rectangle collision resolution.
for(const scheme of data.schemes){await p.locator('[data-id='+scheme.id+']').evaluate(n=>n.dispatchEvent(new MouseEvent('click',{bubbles:true})));const overlaps=await p.locator('.sa-node').evaluateAll(ns=>{const boxes=ns.map(n=>{const b=n.querySelector('rect').getBoundingClientRect();return {id:n.dataset.id,x:b.x,y:b.y,w:b.width,h:b.height};});let out=[];for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];if(a.x<b.x+b.w-1&&a.x+a.w>b.x+1&&a.y<b.y+b.h-1&&a.y+a.h>b.y+1)out.push([a.id,b.id]);}return out;});assert.deepEqual(overlaps,[],scheme.id+' has overlapping nodes');}await overview();
// MkDocs instant navigation away and back.
await p.getByRole('link',{name:'Scheme Atlas Data Guide',exact:true}).first().click();await p.waitForSelector('h1');await p.getByRole('link',{name:'Scheme Atlas',exact:true}).first().click();await p.waitForSelector('.sa-node');assert.equal(await count('.sa-node'),data.schemes.length);assert.equal(await count('.sa-edge'),data.relationships.length);
// Narrow viewport; collapsed details and full screen retain useful controls.
await p.setViewportSize({width:760,height:1000});await ctl('fullscreen').click();assert.equal(await ctl('graph').isVisible(),true);await p.keyboard.press('Escape');
// Test multiple mission/rumor records and distinct queued/revealed flags in an isolated fixture.
const fixture=structuredClone(data);const s=fixture.schemes[0];s.awareness={selectedForIntroduction:true,revealed:true,knowledge:'Players heard only a transport rumor.'};s.missions.push({...s.missions[0],id:'D1-H2',title:'Second hook'});s.rumors=[{id:'D1-R1',title:'Transport rumor',description:'A test rumor.',status:'available',revealed:true,url:''},{id:'D1-R2',title:'Unheard rumor',description:'Another test rumor.',status:'draft',revealed:false,url:''}];
await p.route('**/assets/schemes/schemes.json',route=>route.fulfill({json:fixture}));await p.goto(origin+'/gm/world/scheme-atlas/');await p.waitForSelector('.sa-node');await p.locator('[data-id=D1]').click();const text=await ctl('details').textContent();assert.ok(text.includes('Missions / hooks (2)'));assert.ok(text.includes('Rumors (2)'));assert.ok(text.includes('Players heard only a transport rumor.'));assert.equal(await count('[data-id=D1] .sa-badge'),2);await ctl('awareness').selectOption('revealed');assert.equal(await count('.sa-node'),1);
assert.deepEqual(errors,[]);console.log('PASS: compact overview, all relationship markers, all collision-free selection neighborhoods, details, filters/overrides, keyboard, zoom, fullscreen, panel, instant navigation, responsive viewport, multiple mission/rumor records and awareness.');
}finally{await browser.close();server.close();}
})();
