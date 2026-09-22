#!/usr/bin/env node

import { extractPack } from "@foundryvtt/foundryvtt-cli";
import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";

const ROOT = process.cwd();
const manifest = JSON.parse(
  await fs.readFile(path.join(ROOT, "module.json"), "utf8")
);
const errors = [];
const results = [];

async function readJsonDocuments(directory) {
  const result = new Map();
  const entries = await fs.readdir(directory);
  for (const name of entries.sort()) {
    if (!name.toLowerCase().endsWith(".json")) continue;
    const doc = JSON.parse(await fs.readFile(path.join(directory, name), "utf8"));
    if (!doc._id) {
      errors.push(`${directory}/${name}: missing _id`);
      continue;
    }
    if (result.has(doc._id)) {
      errors.push(`${directory}: duplicate _id ${doc._id}`);
      continue;
    }
    result.set(doc._id, doc);
  }
  return result;
}

function comparable(doc) {
  return {
    _id: doc._id ?? null,
    _key: doc._key ?? null,
    name: doc.name ?? null,
    type: doc.type ?? null,
    folder: doc.folder ?? null
  };
}

function compareIdentity(source, extracted, context) {
  const a = comparable(source);
  const b = comparable(extracted);
  for (const key of Object.keys(a)) {
    if (a[key] !== b[key]) {
      errors.push(
        `${context}: ${key} mismatch; source=${JSON.stringify(a[key])} extracted=${JSON.stringify(b[key])}`
      );
    }
  }
}

const tempRoot = await fs.mkdtemp(
  path.join(os.tmpdir(), "cybermancy-pack-validation-")
);

try {
  let totalSource = 0;
  let totalExtracted = 0;

  for (const pack of manifest.packs ?? []) {
    const compiledRel = pack.path;
    const compiledAbs = path.join(ROOT, compiledRel);
    const sourceAbs = path.join(ROOT, "src", compiledRel);

    try {
      const stat = await fs.stat(compiledAbs);
      if (!stat.isDirectory()) {
        errors.push(`${pack.name}: compiled pack is not a directory: ${compiledRel}`);
        continue;
      }
    } catch {
      errors.push(`${pack.name}: compiled pack missing: ${compiledRel}`);
      continue;
    }

    const sourceDocs = await readJsonDocuments(sourceAbs);
    totalSource += sourceDocs.size;

    const extractDir = path.join(tempRoot, pack.name);
    await fs.mkdir(extractDir, { recursive: true });
    await extractPack(compiledAbs, extractDir, {
      yaml: false,
      transformName: doc => `${doc._id}.json`
    });

    const extractedDocs = await readJsonDocuments(extractDir);
    totalExtracted += extractedDocs.size;

    if (extractedDocs.size !== sourceDocs.size) {
      errors.push(
        `${pack.name}: extracted count ${extractedDocs.size} != source count ${sourceDocs.size}`
      );
    }

    const sourceIds = [...sourceDocs.keys()].sort();
    const extractedIds = [...extractedDocs.keys()].sort();
    if (JSON.stringify(sourceIds) !== JSON.stringify(extractedIds)) {
      const sourceSet = new Set(sourceIds);
      const extractedSet = new Set(extractedIds);
      const missing = sourceIds.filter(id => !extractedSet.has(id)).slice(0, 10);
      const extra = extractedIds.filter(id => !sourceSet.has(id)).slice(0, 10);
      errors.push(
        `${pack.name}: stable-ID set mismatch; missing=${JSON.stringify(missing)} extra=${JSON.stringify(extra)}`
      );
    }

    for (const id of sourceIds) {
      const extracted = extractedDocs.get(id);
      if (!extracted) continue;
      compareIdentity(sourceDocs.get(id), extracted, `${pack.name}/${id}`);
    }

    results.push({
      packName: pack.name,
      documentType: pack.type,
      sourcePath: path.relative(ROOT, sourceAbs).replaceAll("\\", "/"),
      compiledPath: compiledRel.replaceAll("\\", "/"),
      sourceEntryCount: sourceDocs.size,
      extractedEntryCount: extractedDocs.size
    });
  }

  const reportDir = path.join(ROOT, "build", "release");
  await fs.mkdir(reportDir, { recursive: true });
  const summary = {
    status: errors.length ? "FAIL" : "PASS",
    compiler: "@foundryvtt/foundryvtt-cli",
    declaredCompendiumCount: (manifest.packs ?? []).length,
    totalSourceEntries: totalSource,
    totalExtractedEntries: totalExtracted,
    packResults: results,
    generatedPacksAreDerivative: true
  };

  await fs.writeFile(
    path.join(reportDir, "compiled-packs.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );

  if (errors.length) {
    console.error("Cybermancy compiled-pack validation FAILED");
    for (const error of errors) console.error(` - ${error}`);
    process.exit(1);
  }

  console.log("Cybermancy compiled-pack validation PASS");
  console.log(` - Compendia: ${summary.declaredCompendiumCount}`);
  console.log(` - Source entries: ${totalSource}`);
  console.log(` - Re-extracted compiled entries: ${totalExtracted}`);
} finally {
  await fs.rm(tempRoot, { recursive: true, force: true });
}
