// image-browser.mjs
import express from "express";
import path from "node:path";
import { promises as fs } from "node:fs";
import process from "node:process";

const baseDirArg = process.argv[2];
if (!baseDirArg) {
  console.error("Usage: node image-browser.mjs <root-folder> [port]");
  process.exit(1);
}
const baseDir = path.resolve(baseDirArg);
const PORT = Number(process.argv[3] || process.env.PORT || 3000);

// Image extensions to include (case-insensitive)
const IMAGE_EXTS = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".avif", ".tif", ".tiff",
]);

async function walkImages(dir) {
  const out = [];
  async function recur(current) {
    let entries;
    try {
      entries = await fs.readdir(current, { withFileTypes: true });
    } catch {
      return;
    }
    await Promise.all(entries.map(async (ent) => {
      const full = path.join(current, ent.name);
      if (ent.isDirectory()) {
        await recur(full);
      } else if (ent.isFile()) {
        const ext = path.extname(ent.name).toLowerCase();
        if (IMAGE_EXTS.has(ext)) {
          const rel = path.relative(baseDir, full);
          // normalize to forward slashes for URLs and clipboard consistency
          out.push(rel.split(path.sep).join("/"));
        }
      }
    }));
  }
  await recur(dir);
  // stable order: shorter paths first, then lexicographic
  out.sort((a, b) => (a.length - b.length) || a.localeCompare(b));
  return out;
}

const app = express();

// Serve files under /files/<relative-path>
app.use("/files", express.static(baseDir, { index: false, fallthrough: false }));

// API to list images (relative paths from baseDir)
app.get("/api/images", async (_req, res) => {
  try {
    const imgs = await walkImages(baseDir);
    res.json({ root: baseDir, count: imgs.length, images: imgs });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

// Minimal UI
app.get("/", (_req, res) => {
  res.type("html").send(`<!DOCTYPE html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Image Browser</title>
<style>
  :root { --size: 180px; --gap: 8px; --font: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
  body { margin: 0; font-family: var(--font); background:#0f1115; color:#e6e8ef; }
  header { position: sticky; top: 0; background: #0f1115f2; backdrop-filter: blur(6px); padding: 10px 12px; border-bottom: 1px solid #232633; display:flex; gap:16px; align-items:center; z-index: 1;}
  .stat { opacity: 0.8; font-size: 12px; }
  .controls { display:flex; gap:12px; align-items:center; }
  input[type="range"] { width: 260px; }
  #grid { padding: 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(var(--size), 1fr)); gap: var(--gap); }
  figure { margin: 0; background: #151822; border: 1px solid #232633; border-radius: 10px; overflow: hidden; display:flex; flex-direction:column; }
  figure:hover { outline: 2px solid #3d7bfd; outline-offset: -2px; }
  .thumb { width: 100%; height: min(28vw, calc(var(--size) * 1.2)); object-fit: contain; background: #0b0d13; }
  figcaption { font-size: 11px; padding: 6px 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; opacity: 0.85; }
  .toolbar { display:flex; gap:10px; align-items:center; flex-wrap: wrap; }
  .btn { cursor:pointer; border:1px solid #2b2f3d; background:#171a24; color:#e6e8ef; padding:6px 10px; border-radius:8px; font-size:12px; }
  .btn:hover { border-color:#3d7bfd; }
  #toast { position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%); background: #0d6efd; color:white; padding:8px 12px; border-radius:8px; font-size:12px; opacity:0; transition: opacity .15s ease; pointer-events:none; }
  #toast.show { opacity: 1; }
  #filter { min-width: 220px; }
</style>
<body>
  <header>
    <div class="toolbar">
      <label>Size <input id="size" type="range" min="80" max="480" step="4" value="180"></label>
      <input id="filter" type="text" placeholder="Filter (path contains)...">
      <button id="clear" class="btn" title="Reset filters">Reset</button>
      <span id="stats" class="stat"></span>
    </div>
  </header>
  <main id="grid" aria-live="polite"></main>
  <div id="toast" role="status" aria-live="polite"></div>
<script>
  const grid = document.getElementById('grid');
  const size = document.getElementById('size');
  const stats = document.getElementById('stats');
  const filter = document.getElementById('filter');
  const clearBtn = document.getElementById('clear');
  const toast = document.getElementById('toast');

  function setSize(v){ document.documentElement.style.setProperty('--size', v+'px'); localStorage.setItem('imgSize', v); }
  size.addEventListener('input', e => setSize(e.target.value));
  const savedSize = localStorage.getItem('imgSize'); if (savedSize) { size.value = savedSize; setSize(savedSize); }

  function showToast(msg){ toast.textContent = msg; toast.classList.add('show'); clearTimeout(showToast._t); showToast._t = setTimeout(()=>toast.classList.remove('show'), 900); }

  function encPath(p){ return p.split('/').map(encodeURIComponent).join('/'); }

  let ALL = [];
  async function load(){
    const r = await fetch('/api/images');
    const data = await r.json();
    ALL = data.images || [];
    stats.textContent = \`\${data.count ?? ALL.length} images\`;
    render();
  }

  function render(){
    const q = (filter.value || '').toLowerCase();
    const items = q ? ALL.filter(p => p.toLowerCase().includes(q)) : ALL;
    stats.textContent = \`\${items.length} / \${ALL.length} images\`;
    grid.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (const rel of items){
      const fig = document.createElement('figure');
      const img = document.createElement('img');
      img.loading = 'lazy';
      img.decoding = 'async';
      img.className = 'thumb';
      img.src = '/files/' + encPath(rel);
      img.alt = rel;
      img.title = rel + '\\n(click to copy relative path)';
      img.addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(rel); showToast('Copied: ' + rel); }
        catch { showToast('Clipboard blocked by browser settings'); }
      });
      const cap = document.createElement('figcaption');
      cap.textContent = rel;
      fig.append(img, cap);
      frag.appendChild(fig);
    }
    grid.appendChild(frag);
  }

  filter.addEventListener('input', render);
  clearBtn.addEventListener('click', () => { filter.value=''; render(); });

  load();
</script>
</body>
</html>`);
});

app.listen(PORT, () => {
  console.log(`[image-browser] Serving ${baseDir}`);
  console.log(`[image-browser] URL: http://localhost:${PORT}/`);
  console.log(`[image-browser] Click an image to copy its RELATIVE path from the chosen root.`);
});
