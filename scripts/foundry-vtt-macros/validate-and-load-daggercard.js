// Cybermancy - Daggercard Adversary & Environment Importer
// Purpose:
// - Load Daggercard JSON bundles from a folder (recursively)
// - Translate adversary/environment cards into Foundryborne Daggerheart Actors
// - Validate translated Actors
// - Import to World or Actor Compendium
//
// Expected Daggercard schema:
// {
//   "version": 2,
//   "cards": [
//     {
//       "name": "...",
//       "category": "adversary" | "environment",
//       "tier": 1,
//       "type": "...",
//       "description": "...",
//       "motivesTactics": [...],          // adversary
//       "stats": { ... },                // adversary; optional for environment
//       "features": [ ... ],             // adversary
//       "difficulty": 14,                // environment optional shortcut
//       "impulses": [ ... ] | "...",     // environment
//       "notes": "..." | [ ... ],        // environment
//       "art": {
//         "portrait": "modules/.../portrait.webp",   // adversary
//         "token": "modules/.../token.webp",         // adversary
//         "image": "worlds/.../scene.png"            // environment
//       }
//     }
//   ]
// }

(async () => {
  const CONFIG = {
    defaultFolderRootAdversaries: "Adversaries",
    defaultFolderRootEnvironments: "Environments",
    fallbackAdversaryImg: "icons/svg/mystery-man.svg",
    fallbackEnvironmentImg: "icons/svg/hazard.svg",
    defaultAttackImg: "icons/skills/melee/unarmed-punch-fist-yellow-red.webp",
    defaultFeatureImg: "icons/svg/aura.svg",
    useHostileRingForAdversaries: true
  };

  const esc = foundry.utils.escapeHTML;
  const dup = foundry.utils.deepClone ?? foundry.utils.duplicate;

  const isObj = v => v && typeof v === "object" && !Array.isArray(v);
  const isStr = v => typeof v === "string" && v.trim().length > 0;
  const isNum = v => typeof v === "number" && Number.isFinite(v);
  const slug = s => String(s ?? "").trim().toLowerCase();

  function randomId() {
    return foundry.utils.randomID();
  }

  function normalizeHtml(text) {
    if (!isStr(text)) return "";
    const t = text.trim();
    if (t.startsWith("<")) return t;
    return `<p>${esc(t)}</p>`;
  }

  function toSentenceList(value) {
    if (Array.isArray(value)) return value.filter(isStr).join(", ");
    if (isStr(value)) return value;
    return "";
  }

  function toHtmlList(value) {
    if (Array.isArray(value)) {
      const items = value.filter(isStr).map(v => `<li>${esc(v)}</li>`).join("");
      return items ? `<ul>${items}</ul>` : "";
    }
    if (isStr(value)) return normalizeHtml(value);
    return "";
  }

  function normalizeRange(value) {
    const map = {
      "melee": "melee",
      "very close": "veryClose",
      "veryclose": "veryClose",
      "close": "close",
      "far": "far",
      "very far": "veryFar",
      "veryfar": "veryFar"
    };
    const k = slug(value).replace(/\s+/g, " ");
    return map[k] ?? "melee";
  }

  function normalizeActionType(value) {
    const k = slug(value);
    if (k === "passive") return "passive";
    if (k === "reaction") return "reaction";
    return "action";
  }

  function parseDamageType(token) {
    const k = slug(token);
    const map = {
      "phy": "physical",
      "physical": "physical",
      "mag": "magical",
      "magic": "magical",
      "magical": "magical"
    };
    return map[k] ?? null;
  }

  function parseDamageFormula(input) {
    // Supports shapes like:
    // 1d12+2 phy
    // 2d8
    // 4 phy
    // 2 stress
    if (!isStr(input)) {
      return {
        parts: [],
        includeBase: false,
        direct: false
      };
    }

    const raw = input.trim();
    const m = raw.match(/^(\d+d\d+|\d+)(?:\s*([+-])\s*(\d+))?(?:\s+([A-Za-z]+))?$/i);

    if (!m) {
      return {
        parts: [{
          value: {
            custom: { enabled: true, formula: raw },
            dice: "d6",
            bonus: null,
            multiplier: "flat",
            flatMultiplier: 1
          },
          applyTo: "hitPoints",
          type: [],
          resultBased: false,
          valueAlt: {
            multiplier: "prof",
            flatMultiplier: 1,
            dice: "d6",
            bonus: null,
            custom: { enabled: false, formula: "" }
          },
          base: false
        }],
        includeBase: false,
        direct: false
      };
    }

    const base = m[1];
    const sign = m[2];
    const bonusRaw = m[3];
    const typeToken = m[4];

    let dice = "d6";
    let bonus = null;
    let custom = { enabled: false, formula: "" };

    if (/^\d+d\d+$/i.test(base)) {
      dice = base.toLowerCase().replace(/^1?d/i, "d");
    } else if (/^\d+$/.test(base)) {
      custom = { enabled: true, formula: base };
    }

    if (bonusRaw) {
      const n = Number(bonusRaw);
      bonus = sign === "-" ? -n : n;
    }

    const dmgType = parseDamageType(typeToken);

    return {
      parts: [{
        value: {
          custom,
          dice,
          bonus,
          multiplier: "flat",
          flatMultiplier: 1
        },
        applyTo: "hitPoints",
        type: dmgType ? [dmgType] : [],
        resultBased: false,
        valueAlt: {
          multiplier: "prof",
          flatMultiplier: 1,
          dice: "d6",
          bonus: null,
          custom: { enabled: false, formula: "" }
        },
        base: false
      }],
      includeBase: false,
      direct: false
    };
  }

  function parseExperienceList(list) {
    const out = {};
    if (!Array.isArray(list)) return out;

    for (const entry of list) {
      if (!isStr(entry)) continue;
      const m = entry.match(/^(.*?)(?:\s*\+\s*(-?\d+))?$/);
      const name = m?.[1]?.trim();
      const value = Number(m?.[2] ?? 0);
      if (!name) continue;
      out[randomId()] = { name, value };
    }
    return out;
  }

  function buildDefaultAdversaryAttack(card) {
    const weapon = card?.stats?.weapon ?? {};
    return {
      name: isStr(weapon.name) ? weapon.name : "Attack",
      roll: {
        bonus: isNum(card?.stats?.attack) ? card.stats.attack : 0,
        type: "attack",
        trait: null,
        difficulty: null,
        advState: "neutral",
        diceRolling: {
          multiplier: "prof",
          flatMultiplier: 1,
          dice: "d6",
          compare: null,
          treshold: null
        },
        useDefault: false
      },
      range: normalizeRange(weapon.range),
      damage: parseDamageFormula(weapon.damage),
      img: CONFIG.defaultAttackImg,
      type: "attack",
      chatDisplay: false,
      _id: randomId(),
      systemPath: "actions",
      baseAction: false,
      description: "",
      originItem: { type: "itemCollection" },
      actionType: "action",
      cost: [],
      uses: {
        value: null,
        max: null,
        recovery: null,
        consumeOnSuccess: false
      },
      target: {
        type: "any",
        amount: null
      },
      effects: [],
      save: {
        trait: null,
        difficulty: null,
        damageMod: "none"
      }
    };
  }

  function buildFeatureAction(feature) {
    return {
      type: "effect",
      _id: randomId(),
      systemPath: "actions",
      description: normalizeHtml(feature.description),
      chatDisplay: true,
      actionType: normalizeActionType(feature.action),
      cost: [],
      uses: {
        value: null,
        max: "",
        recovery: null,
        consumeOnSuccess: false
      },
      effects: [],
      target: {
        type: "any",
        amount: null
      },
      name: isStr(feature.name) ? feature.name : "Feature",
      img: CONFIG.defaultFeatureImg,
      range: "",
      baseAction: false,
      originItem: { type: "itemCollection" }
    };
  }

  function buildFeatureItem(feature) {
    const actionId = randomId();
    const action = buildFeatureAction(feature);
    action._id = actionId;

    return {
      name: isStr(feature.name) ? feature.name : "Feature",
      type: "feature",
      _id: randomId(),
      img: CONFIG.defaultFeatureImg,
      system: {
        description: normalizeHtml(feature.description),
        resource: null,
        actions: {
          [actionId]: action
        },
        originItemType: null,
        attribution: {},
        multiclassOrigin: false
      },
      effects: [],
      folder: null,
      sort: 0,
      flags: {},
      ownership: { default: 0 }
    };
  }

  function buildPrototypeTokenForAdversary(card, portraitPath, tokenPath) {
    return {
      name: card.name,
      displayName: 0,
      actorLink: false,
      width: 1,
      height: 1,
      texture: {
        src: tokenPath || portraitPath || CONFIG.fallbackAdversaryImg,
        anchorX: 0.5,
        anchorY: 0.5,
        offsetX: 0,
        offsetY: 0,
        fit: "contain",
        scaleX: 1,
        scaleY: 1,
        rotation: 0,
        tint: "#ffffff",
        alphaThreshold: 0.75
      },
      lockRotation: false,
      rotation: 0,
      alpha: 1,
      disposition: -1,
      displayBars: 0,
      bar1: { attribute: "resources.hitPoints" },
      bar2: { attribute: "resources.stress" },
      light: {
        negative: false,
        priority: 0,
        alpha: 0.5,
        angle: 360,
        bright: 0,
        color: null,
        coloration: 1,
        dim: 0,
        attenuation: 0.5,
        luminosity: 0.5,
        saturation: 0,
        contrast: 0,
        shadows: 0,
        animation: { type: null, speed: 5, intensity: 5, reverse: false },
        darkness: { min: 0, max: 1 }
      },
      sight: {
        enabled: false,
        range: 0,
        angle: 360,
        visionMode: "basic",
        color: null,
        attenuation: 0.1,
        brightness: 0,
        saturation: 0,
        contrast: 0
      },
      detectionModes: [],
      occludable: { radius: 0 },
      ring: {
        enabled: !!CONFIG.useHostileRingForAdversaries,
        colors: {
          ring: CONFIG.useHostileRingForAdversaries ? "#8f0000" : null,
          background: null
        },
        effects: 1,
        subject: {
          scale: 0.8,
          texture: null
        }
      },
      turnMarker: {
        mode: 1,
        animation: null,
        src: null,
        disposition: false
      },
      movementAction: null,
      flags: {},
      randomImg: false,
      appendNumber: false,
      prependAdjective: false
    };
  }

  function buildPrototypeTokenForEnvironment(card, imagePath) {
    return {
      name: card.name,
      displayName: 0,
      actorLink: false,
      width: 1,
      height: 1,
      texture: {
        src: imagePath || CONFIG.fallbackEnvironmentImg,
        anchorX: 0.5,
        anchorY: 0.5,
        offsetX: 0,
        offsetY: 0,
        fit: "contain",
        scaleX: 1,
        scaleY: 1,
        rotation: 0,
        tint: "#ffffff",
        alphaThreshold: 0.75
      },
      lockRotation: false,
      rotation: 0,
      alpha: 1,
      disposition: -1,
      displayBars: 0,
      bar1: { attribute: "resources.hitPoints" },
      bar2: { attribute: "resources.stress" },
      light: {
        negative: false,
        priority: 0,
        alpha: 0.5,
        angle: 360,
        bright: 0,
        color: null,
        coloration: 1,
        dim: 0,
        attenuation: 0.5,
        luminosity: 0.5,
        saturation: 0,
        contrast: 0,
        shadows: 0,
        animation: { type: null, speed: 5, intensity: 5, reverse: false },
        darkness: { min: 0, max: 1 }
      },
      sight: {
        enabled: false,
        range: 0,
        angle: 360,
        visionMode: "basic",
        color: null,
        attenuation: 0.1,
        brightness: 0,
        saturation: 0,
        contrast: 0
      },
      detectionModes: [],
      occludable: { radius: 0 },
      ring: {
        enabled: false,
        colors: { ring: null, background: null },
        effects: 1,
        subject: { scale: 1, texture: null }
      },
      turnMarker: {
        mode: 1,
        animation: null,
        src: null,
        disposition: false
      },
      movementAction: null,
      flags: {},
      randomImg: false,
      appendNumber: false,
      prependAdjective: false
    };
  }

  function validateDaggercardCard(card) {
    const errors = [];
    const warnings = [];

    if (!isStr(card?.name)) errors.push(`missing "name"`);
    if (!isStr(card?.category)) errors.push(`missing "category"`);
    if (!isNum(card?.tier)) warnings.push(`missing/invalid "tier"`);

    const category = slug(card?.category);

    if (category === "adversary") {
      if (!isObj(card?.stats)) errors.push(`adversary missing "stats"`);
      if (!isNum(card?.stats?.difficulty)) errors.push(`adversary missing stats.difficulty`);
      if (!Array.isArray(card?.stats?.thresholds) || card.stats.thresholds.length < 2) errors.push(`adversary missing stats.thresholds[major,severe]`);
      if (!isNum(card?.stats?.hitPoints)) errors.push(`adversary missing stats.hitPoints`);
      if (!isNum(card?.stats?.stress)) errors.push(`adversary missing stats.stress`);
      if (!isObj(card?.stats?.weapon)) errors.push(`adversary missing stats.weapon`);
      if (!isStr(card?.stats?.weapon?.name)) errors.push(`adversary missing stats.weapon.name`);
      if (!isStr(card?.stats?.weapon?.range)) errors.push(`adversary missing stats.weapon.range`);
      if (!isStr(card?.stats?.weapon?.damage)) errors.push(`adversary missing stats.weapon.damage`);
      if (!Array.isArray(card?.features)) warnings.push(`adversary missing/invalid features[]`);
      if (!isStr(card?.art?.portrait)) warnings.push(`adversary missing art.portrait`);
      if (!isStr(card?.art?.token)) warnings.push(`adversary missing art.token`);
    } else if (category === "environment") {
      if (!isNum(card?.difficulty) && !isNum(card?.stats?.difficulty)) warnings.push(`environment missing difficulty`);
      if (!isStr(card?.art?.image)) warnings.push(`environment missing art.image`);
    } else {
      errors.push(`unsupported category "${card?.category}"`);
    }

    return { errors, warnings };
  }

  function validateTranslatedActor(doc) {
    const errors = [];
    const warnings = [];

    if (!isStr(doc?.name)) errors.push(`actor missing name`);
    if (!isStr(doc?.type)) errors.push(`actor missing type`);
    if (!isObj(doc?.system)) errors.push(`actor missing system`);

    if (doc?.type === "adversary") {
      if (!isNum(doc?.system?.difficulty)) errors.push(`adversary missing system.difficulty`);
      if (!isObj(doc?.system?.damageThresholds)) errors.push(`adversary missing system.damageThresholds`);
      if (!isObj(doc?.system?.resources?.hitPoints)) errors.push(`adversary missing resources.hitPoints`);
      if (!isObj(doc?.system?.resources?.stress)) errors.push(`adversary missing resources.stress`);
      if (!isObj(doc?.system?.attack)) errors.push(`adversary missing system.attack`);
      if (!Array.isArray(doc?.items)) warnings.push(`adversary missing items[]`);
    }

    if (doc?.type === "environment") {
      if (!isNum(doc?.system?.difficulty)) warnings.push(`environment missing system.difficulty`);
      if (!isNum(doc?.system?.tier)) warnings.push(`environment missing system.tier`);
    }

    if (!isStr(doc?.img)) warnings.push(`missing actor img`);
    if (!isObj(doc?.prototypeToken?.texture) || !isStr(doc?.prototypeToken?.texture?.src)) warnings.push(`missing token art`);

    return { errors, warnings };
  }

  function transformAdversaryCardToActor(card) {
    const portraitPath = card?.art?.portrait || CONFIG.fallbackAdversaryImg;
    const tokenPath = card?.art?.token || portraitPath || CONFIG.fallbackAdversaryImg;

    return {
      name: card.name,
      img: portraitPath,
      type: "adversary",
      folder: null,
      system: {
        difficulty: card.stats.difficulty,
        damageThresholds: {
          major: card.stats.thresholds?.[0] ?? 0,
          severe: card.stats.thresholds?.[1] ?? 0
        },
        resources: {
          hitPoints: { value: 0, max: card.stats.hitPoints ?? 0, isReversed: true },
          stress: { value: 0, max: card.stats.stress ?? 0, isReversed: true }
        },
        motivesAndTactics: toSentenceList(card.motivesTactics),
        resistance: {
          physical: { resistance: false, immunity: false, reduction: 0 },
          magical: { resistance: false, immunity: false, reduction: 0 }
        },
        type: card.type ?? "standard",
        notes: "",
        hordeHp: 1,
        experiences: parseExperienceList(card.stats.experience),
        bonuses: {
          roll: {
            attack: { bonus: 0, dice: [] },
            action: { bonus: 0, dice: [] },
            reaction: { bonus: 0, dice: [] }
          },
          damage: {
            physical: { bonus: 0, dice: [] },
            magical: { bonus: 0, dice: [] }
          }
        },
        tier: card.tier ?? 1,
        description: normalizeHtml(card.description),
        attack: buildDefaultAdversaryAttack(card),
        attribution: {
          source: "Cybermancy Daggercard",
          page: null,
          artist: ""
        },
        criticalThreshold: 20,
        rules: {
          conditionImmunities: {
            hidden: false,
            restrained: false,
            vulnerable: false
          }
        }
      },
      flags: {},
      prototypeToken: buildPrototypeTokenForAdversary(card, portraitPath, tokenPath),
      items: Array.isArray(card.features) ? card.features.map(buildFeatureItem) : [],
      effects: [],
      ownership: { default: 0 }
    };
  }

  function transformEnvironmentCardToActor(card) {
    const imagePath = card?.art?.image || CONFIG.fallbackEnvironmentImg;

    return {
      folder: null,
      name: card.name,
      type: "environment",
      img: imagePath,
      system: {
        attribution: {},
        description: normalizeHtml(card.description),
        tier: card.tier ?? 1,
        difficulty: card.difficulty ?? card?.stats?.difficulty ?? 0,
        potentialAdversaries: {},
        notes: Array.isArray(card.notes) ? toHtmlList(card.notes) : normalizeHtml(card.notes),
        impulses: Array.isArray(card.impulses) ? card.impulses.join(", ") : (card.impulses ?? ""),
        type: card.type ?? "general"
      },
      prototypeToken: buildPrototypeTokenForEnvironment(card, imagePath),
      items: Array.isArray(card.features) ? card.features.map(buildFeatureItem) : [],
      effects: [],
      flags: {},
      ownership: { default: 0 }
    };
  }

  function transformCard(card) {
    const category = slug(card?.category);
    if (category === "adversary") return transformAdversaryCardToActor(card);
    if (category === "environment") return transformEnvironmentCardToActor(card);
    throw new Error(`Unsupported Daggercard category: ${card?.category}`);
  }

  async function fetchJsonFromDataPath(path) {
    const assets = foundry.utils?.getRoute?.("assets");
    if (assets) {
      const url = `${assets}?path=${encodeURIComponent(path)}`;
      const r = await fetch(url, { cache: "no-store" });
      if (r.ok) return await r.json();
    }
    const r2 = await fetch(path, { cache: "no-store" });
    if (!r2.ok) throw new Error(`HTTP ${r2.status} for ${path}`);
    return await r2.json();
  }

  async function* walkDataTree(dir) {
    const browse = await FilePicker.browse("data", dir);
    for (const d of browse.dirs) yield* walkDataTree(d);
    for (const f of browse.files) {
      if (f.toLowerCase().endsWith(".json")) yield f;
    }
  }

  async function ensureWorldFolderPath(names, type = "Actor") {
    let parentId = null;
    let folderDoc = null;
    for (const name of names) {
      folderDoc = game.folders.find(f => f.type === type && f.name === name && ((f.parent?.id ?? null) === parentId)) || null;
      if (!folderDoc) {
        folderDoc = await Folder.create({ name, type, parent: parentId });
      }
      parentId = folderDoc.id;
    }
    return folderDoc;
  }

  async function refreshPackFolders(pack) {
    try {
      if (typeof pack.getIndex === "function") await pack.getIndex({ fields: ["folder"] });
    } catch (_e) {}
  }

  async function ensureCompendiumFolderPath(pack, names) {
    let parentId = null;
    let folder = null;

    for (const name of names) {
      const existing = pack.folders ? Array.from(pack.folders) : [];
      folder = existing.find(f => f.name === name && ((f.parent?.id ?? null) === parentId)) || null;
      if (!folder) {
        if (typeof pack.createFolder === "function") {
          folder = await pack.createFolder({ name, parent: parentId });
        } else {
          folder = await Folder.create({ name, type: "Compendium", parent: parentId, pack: pack.collection });
        }
        await refreshPackFolders(pack);
      }
      parentId = folder.id;
    }

    return folder;
  }

  async function importActorDoc(docData, { toWorld = false, pack = null } = {}) {
    const categoryRoot = docData.type === "environment"
      ? CONFIG.defaultFolderRootEnvironments
      : CONFIG.defaultFolderRootAdversaries;

    const subtype = docData?.system?.type || docData.type || "Misc";
    const folderPath = [categoryRoot, String(subtype)];

    if (toWorld || !pack) {
      const folder = await ensureWorldFolderPath(folderPath, "Actor");
      docData.folder = folder?.id ?? null;
      return await Actor.create(docData, { renderSheet: false });
    }

    const compFolder = await ensureCompendiumFolderPath(pack, folderPath);
    if (compFolder?.id) docData.folder = compFolder.id;

    const DocCls = pack.documentClass ?? game.actors.documentClass;
    const doc = new DocCls(docData);
    return await pack.importDocument(doc);
  }

  function detectDaggercardBundle(json) {
    return isObj(json) && Array.isArray(json.cards);
  }

  function buildSummaryTable(results) {
    const rows = results.map((r, i) => {
      const msgs = [];
      if (r.errors.length) msgs.push(...r.errors.map(e => `❌ ${e}`));
      if (r.warnings.length) msgs.push(...r.warnings.map(w => `⚠️ ${w}`));
      const status = r.errors.length ? "ERR" : (r.warnings.length ? "WARN" : "OK");
      const color = status === "OK" ? "#3bb273" : status === "WARN" ? "#f0ad4e" : "#d9534f";
      return `
        <tr data-index="${i}">
          <td><input type="checkbox" name="sel" value="${i}" ${status !== "ERR" ? "checked" : "disabled"}></td>
          <td><code>${esc(r.file)}</code></td>
          <td><code>${esc(r.cardName)}</code></td>
          <td style="color:${color};font-weight:600;">${status}</td>
          <td>${msgs.map(m => `<div>${esc(m)}</div>`).join("") || "<span style='opacity:.7'>(none)</span>"}</td>
        </tr>
      `;
    }).join("");

    return `
      <form class="cybermancy-daggercard-import">
        <style>
          .cybermancy-daggercard-import table { width:100%; border-collapse:collapse; }
          .cybermancy-daggercard-import th, .cybermancy-daggercard-import td { border-bottom:1px solid #444; padding:.35rem .5rem; vertical-align:top; }
          .cybermancy-daggercard-import thead th { position:sticky; top:0; background:#1e1e1e; }
          .cybermancy-daggercard-import .toolbar { display:flex; gap:.5rem; margin-bottom:.5rem; align-items:center; }
        </style>
        <div class="toolbar">
          <button type="button" data-action="select-all">Select All Valid</button>
          <button type="button" data-action="select-none">Select None</button>
        </div>
        <div style="max-height:420px; overflow:auto;">
          <table>
            <thead>
              <tr>
                <th style="width:2rem;"></th>
                <th>File</th>
                <th>Card</th>
                <th>Status</th>
                <th>Messages</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </form>
    `;
  }

  async function openDialogAndRun() {
    const actorPacks = Array.from(game.packs).filter(p => p.documentName === "Actor");
    const packOptions = ['<option value="">(Import to World)</option>']
      .concat(actorPacks.map(p => `<option value="${p.collection}">${esc(p.title)} — ${esc(p.collection)}</option>`))
      .join("");

    const content = `
      <form>
        <div class="form-group">
          <label>Start Folder (data path)</label>
          <div class="flexrow">
            <input type="text" name="folder" placeholder="modules/cybermancy/... or worlds/..."/>
            <button type="button" class="filepicker"><i class="fas fa-folder-open"></i></button>
          </div>
        </div>
        <div class="form-group">
          <label>Target Actor Compendium</label>
          <select name="pack">${packOptions}</select>
        </div>
        <div class="form-group">
          <label class="checkbox"><input type="checkbox" name="dryRun" checked /> Dry Run (validate/translate only)</label>
        </div>
      </form>
    `;

    return await new Promise(resolve => {
      const dlg = new Dialog({
        title: "Cybermancy Daggercard Import",
        content,
        buttons: {
          run: {
            label: "Run",
            callback: html => {
              const folder = html.find('input[name="folder"]').val()?.trim();
              const pack = html.find('select[name="pack"]').val()?.trim();
              const dryRun = html.find('input[name="dryRun"]')[0].checked;
              if (!folder) return ui.notifications?.error("Select a folder.");
              resolve({ folder, pack, dryRun });
            }
          },
          cancel: { label: "Cancel", callback: () => resolve(null) }
        },
        default: "run",
        render: html => {
          html.find("button.filepicker").on("click", async () => {
            const fp = new FilePicker({
              type: "folder",
              current: "data",
              callback: path => html.find('input[name="folder"]').val(path)
            });
            fp.browse("data");
          });
        }
      });
      dlg.render(true);
    });
  }

  async function run({ folder, pack, dryRun = true } = {}) {
    const results = [];
    const translated = [];

    for await (const file of walkDataTree(folder)) {
      try {
        const json = await fetchJsonFromDataPath(file);
        if (!detectDaggercardBundle(json)) continue;

        for (const card of json.cards) {
          const sourceCheck = validateDaggercardCard(card);
          let actorDoc = null;
          let errors = [...sourceCheck.errors];
          let warnings = [...sourceCheck.warnings];

          if (!errors.length) {
            try {
              actorDoc = transformCard(card);
              const translatedCheck = validateTranslatedActor(actorDoc);
              errors.push(...translatedCheck.errors);
              warnings.push(...translatedCheck.warnings);
            } catch (e) {
              errors.push(String(e.message ?? e));
            }
          }

          const entry = {
            file,
            cardName: card?.name ?? "(unnamed)",
            card,
            actorDoc,
            errors,
            warnings
          };
          results.push(entry);
          if (!errors.length && actorDoc) translated.push(entry);
        }
      } catch (err) {
        results.push({
          file,
          cardName: "(file error)",
          card: null,
          actorDoc: null,
          errors: [String(err.message ?? err)],
          warnings: []
        });
      }
    }

    if (!results.length) {
      ui.notifications?.warn("No Daggercard JSON files found.");
      return { summary: { total: 0, ok: 0, withErrors: 0, withWarnings: 0 }, results };
    }

    const content = buildSummaryTable(results);
    let chosenIndexes = null;

await new Promise(resolve => {
  const buttons = {
    importSelected: {
      label: dryRun ? "Close" : "Import Selected",
      callback: html => {
        if (!dryRun) {
          const checks = html[0].querySelectorAll('input[type="checkbox"][name="sel"]:checked');
          chosenIndexes = Array.from(checks).map(c => Number(c.value));
        }
        resolve();
      }
    },
    cancel: {
      label: "Cancel",
      callback: () => resolve()
    }
  };

  if (!dryRun) {
    buttons.importAllValid = {
      label: "Import All Valid",
      callback: () => {
        chosenIndexes = results
          .map((r, i) => ({ r, i }))
          .filter(x => x.r.errors.length === 0)
          .map(x => x.i);
        resolve();
      }
    };
  }

  const dlg = new Dialog({
    title: `Cybermancy Daggercard Import (${results.length} card${results.length !== 1 ? "s" : ""})`,
    content,
    buttons,
    render: html => {
      const form = html.find("form.cybermancy-daggercard-import");
      form.on("click", 'button[data-action="select-all"]', ev => {
        ev.preventDefault();
        form.find('tbody tr').each((_, tr) => {
          const statusCell = tr.children[3]?.textContent?.trim();
          const cb = tr.querySelector('input[type="checkbox"]');
          if (cb && statusCell !== "ERR") cb.checked = true;
        });
      });
      form.on("click", 'button[data-action="select-none"]', ev => {
        ev.preventDefault();
        form.find('input[type="checkbox"]').prop("checked", false);
      });
    },
    default: "importSelected"
  });

  dlg.render(true);
});

    const summary = {
      total: results.length,
      ok: results.filter(r => r.errors.length === 0).length,
      withWarnings: results.filter(r => r.errors.length === 0 && r.warnings.length > 0).length,
      withErrors: results.filter(r => r.errors.length > 0).length
    };

    if (dryRun || !Array.isArray(chosenIndexes)) {
      ui.notifications?.info(`Daggercard import dry run: total ${summary.total}, ok ${summary.ok}, errors ${summary.withErrors}`);
      return { summary, results };
    }

    const targetPack = pack ? game.packs.get(pack) : null;
    if (pack && !targetPack) {
      ui.notifications?.error(`Actor compendium not found: ${pack}`);
      return { summary, results };
    }
    if (targetPack && targetPack.documentName !== "Actor") {
      ui.notifications?.error(`Target pack is not an Actor compendium: ${pack}`);
      return { summary, results };
    }
    if (targetPack?.locked) {
      ui.notifications?.error(`Target compendium is locked: ${targetPack.metadata.label}`);
      return { summary, results };
    }

    let imported = 0;
    for (const i of chosenIndexes) {
      const row = results[i];
      if (!row?.actorDoc || row.errors.length) continue;

      try {
        await importActorDoc(dup(row.actorDoc), {
          toWorld: !targetPack,
          pack: targetPack
        });
        imported++;
      } catch (e) {
        console.error(`Failed importing ${row.cardName} from ${row.file}`, e);
      }
    }

    if (targetPack && typeof targetPack.getIndex === "function") {
      await targetPack.getIndex({ reload: true });
    }

    ui.notifications?.info(`Imported ${imported} Actor${imported !== 1 ? "s" : ""} from Daggercard.`);
    return { summary, results, imported };
  }

  window.CybermancyDaggercardImport = { run };

  try {
    const opts = await openDialogAndRun();
    if (opts) await run(opts);
  } catch (e) {
    console.error("Cybermancy Daggercard Import macro error:", e);
    ui.notifications?.error(`Daggercard import failed: ${e.message ?? e}`);
  }
})();