#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

function sha12(s){ return crypto.createHash("sha1").update(s).digest("hex").slice(0,12); }
function asArray(v){ return Array.isArray(v) ? v : (v == null ? [] : [v]); }
function parseDamage(s){
  // "d10+3" => { dice:"d10", bonus:3 }
  const m = String(s||"").trim().match(/^(\w*\d*d\d+)(?:\s*([+\-])\s*(\d+))?$/i);
  if(!m) return { dice:"d6", bonus:0 };
  const dice = m[1];
  const bonus = m[2] ? (m[2]==="-"? -1:1) * parseInt(m[3],10) : 0;
  return { dice, bonus };
}

function buildAttack(d){
  const dmg = parseDamage(d.damage);
  const dmgTypes = asArray(d.damageType && d.damageType !== "" ? d.damageType : "physical");
  return {
    name: "Attack",
    img: d.attackImg || "icons/skills/melee/blood-slash-foam-red.webp",
    systemPath: "attack",
    type: "attack",
    range: d.range || "melee",
    target: { type: "any", amount: Number.isFinite(d.numtargets)? d.numtargets : 1 },
    roll: {
      trait: d.trait || "strength",
      type: "attack",
      difficulty: null,
      bonus: null,
      advState: "neutral",
      diceRolling: { multiplier: "prof", flatMultiplier: 1, dice: "d6" }
    },
    damage: {
      parts: [{
        value: {
          dice: dmg.dice, bonus: dmg.bonus,
          multiplier: "prof", flatMultiplier: 1, custom: { enabled:false, formula:"" }
        },
        type: dmgTypes,
        applyTo: d.damageTo || "hitPoints",
        resultBased: false,
        valueAlt: { multiplier:"prof", flatMultiplier:1, dice:"d6", bonus:null, custom:{enabled:false, formula:""} },
        base: false
      }],
      includeBase: false
    },
    chatDisplay: true,
    actionType: "action",
    _id: sha12(`${d.name}:attack`)
  };
}

function buildEffectAction(d, label, kind = "effect", actionType = "reaction"){
  const id = sha12(`${d.name}:action:${label}`);
  return [id, {
    type: kind,
    actionType,
    chatDisplay: true,
    name: label,
    description: d.actionDescriptions?.[label] ?? "",
    img: d.actionIcons?.[label] ?? d.img ?? "icons/skills/melee/blade-tip-smoke-green.webp",
    _id: id,
    effects: [],
    systemPath: "actions",
    cost: [],
    uses: { value: null, max: null, recovery: null, consumeOnSuccess: false },
    target: { type: "any", amount: null },
    range: d.range || "melee"
  }];
}

function compileDescriptor(desc){
  const system = {
    description: desc.description ?? "",
    tier: desc.tier ?? 1,
    equipped: !!desc.equipped,
    secondary: !!desc.secondary,
    burden: desc.burden ?? "twoHanded"
  };

  if ((desc.primaryAction ?? "attack") === "attack") {
    system.attack = buildAttack(desc);
  }

  const actions = Object.fromEntries(
    asArray(desc.actions).map(label => buildEffectAction(desc, label))
  );
  if (Object.keys(actions).length) system.actions = actions;

  return {
    name: desc.name,
    type: desc.type || "weapon",
    img: desc.img,
    system,
    effects: []
  };
}

async function main(){
  const inPath = process.argv[2];
  const outPath = process.argv[3] || path.join(process.cwd(), "out.item.json");
  if (!inPath) {
    console.error("Usage: node compile-descriptor.mjs <descriptor.json> [out.json]");
    process.exit(1);
  }
  const desc = JSON.parse(await fs.readFile(inPath, "utf8"));
  const item = compileDescriptor(desc);
  await fs.writeFile(outPath, JSON.stringify(item, null, 2), "utf8");
  console.log("Wrote", outPath);
}
main().catch(e => { console.error(e); process.exit(1); });
