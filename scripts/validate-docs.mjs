#!/usr/bin/env node
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";
import Ajv from "ajv";
import addFormats from "ajv-formats";

const ajv = new Ajv({ strict: false, allErrors: true, allowUnionTypes: true });
addFormats(ajv);

// load schemas
const base = JSON.parse(readFileSync("schemas/base.fvtt.json", "utf8"));
const item = JSON.parse(readFileSync("schemas/item.dh.json", "utf8"));
const actor = JSON.parse(readFileSync("schemas/actor.dh.json", "utf8"));
const domain = JSON.parse(readFileSync("schemas/domain.dh.json", "utf8"));
const folder = JSON.parse(readFileSync("schemas/folder.fvtt.json", "utf8"));

ajv.addSchema(base).addSchema(item).addSchema(actor).addSchema(domain).addSchema(folder);

const roots = [
  { dir: "src-data/items", schema: "item.dh.json" },
  { dir: "src-data/actors", schema: "actor.dh.json" },
  { dir: "src-data/domains", schema: "domain.dh.json" },
  { dir: "src-data/folders", schema: "folder.fvtt.json" }
];

let failCount = 0;
function walk(dir, cb) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, cb);
    else if (st.isFile() && extname(p) === ".json") cb(p);
  }
}

for (const { dir, schema } of roots) {
  try {
    walk(dir, (p) => {
      const data = JSON.parse(readFileSync(p, "utf8"));
      const validate = ajv.getSchema(schema);
      if (!validate) throw new Error(`Schema not found: ${schema}`);
      const ok = validate(data);
      if (!ok) {
        failCount++;
        console.error(`❌ Schema errors in ${p}`);
        for (const e of validate.errors) console.error("  -", e.instancePath || "/", e.message);
      } else {
        console.log(`✅ ${p}`);
      }
    });
  } catch (e) {
    // allow missing optional trees
    if (!/no such file/i.test(String(e))) throw e;
  }
}

if (failCount) {
  console.error(`\nValidation failed with ${failCount} file(s) in error.`);
  process.exit(1);
} else {
  console.log("\nAll schemas validated clean.");
}
