#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const MEDIA_EXTENSION = /\.(?:png|webp|jpe?g|svg|gif|bmp|tiff?|avif|ico)(?:[?#].*)?$/i;
const IMAGE_FIELD_NAMES = new Set([
  "img", "src", "image", "icon", "portrait", "token", "texture"
]);

const CYBERMANCY_ROOT_PREFIXES = [
  "modules/cybermancy/",
  "worlds/cybermancer/",
  "worlds/cybermancy/"
];

const ASSET_PREFIXES = [
  {
    prefix: "modules/cybermancy/assets/",
    kind: "module",
    canonicalRuntimePrefix: true
  },
  {
    prefix: "worlds/cybermancer/assets/",
    kind: "legacy-world",
    canonicalRuntimePrefix: false
  },
  {
    prefix: "worlds/cybermancy/assets/",
    kind: "legacy-world",
    canonicalRuntimePrefix: false
  },
  {
    prefix: "assets/",
    kind: "repository-relative",
    canonicalRuntimePrefix: false
  }
];

function usage() {
  console.log(`Cybermancy runtime asset validator

Usage:
  node tools/validate-runtime-assets.mjs [options]

Options:
  --repo-root <path>  Repository root. Defaults to the current working directory.
  --strict-prefix     Fail references that resolve into /assets but do not use
                      modules/cybermancy/assets/... at runtime.
  --json              Emit the validation report as JSON.
  --help              Show this help.

Default validation scope:
  - scans every *.json file below src/packs/
  - recognizes Cybermancy module/world/repository asset references
  - requires every recognized Cybermancy runtime image/token reference to map
    to an exact, case-sensitive file below repository /assets
  - reports legacy world/repository-relative prefixes without failing unless
    --strict-prefix is supplied

Foundry/Daggerheart/core image references such as icons/svg/aura.svg are outside
this validator's ownership scope and are ignored.
`);
}

function parseArgs(argv) {
  const args = {
    repoRoot: process.cwd(),
    strictPrefix: false,
    json: false
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    }
    if (arg === "--strict-prefix") {
      args.strictPrefix = true;
      continue;
    }
    if (arg === "--json") {
      args.json = true;
      continue;
    }
    if (arg === "--repo-root") {
      const value = argv[i + 1];
      if (!value) throw new Error("--repo-root requires a path");
      args.repoRoot = value;
      i += 1;
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return args;
}

function toPosix(value) {
  return String(value).replaceAll("\\", "/");
}

function stripQueryAndFragment(value) {
  return value.split(/[?#]/, 1)[0];
}

function safeDecodePath(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function jsonPointerJoin(pointer, key) {
  const escaped = String(key).replaceAll("~", "~0").replaceAll("/", "~1");
  return `${pointer}/${escaped}`;
}

function imageField(pointer) {
  const leaf = pointer.split("/").at(-1) ?? "";
  return IMAGE_FIELD_NAMES.has(leaf);
}

function looksLikeMediaPath(value) {
  return MEDIA_EXTENSION.test(value);
}

function classifyReference(rawValue, pointer) {
  if (typeof rawValue !== "string") return null;

  const value = toPosix(rawValue.trim());
  if (!value) return null;

  for (const entry of ASSET_PREFIXES) {
    if (value.startsWith(entry.prefix)) {
      return {
        status: "candidate",
        raw: rawValue,
        normalized: value,
        prefix: entry.prefix,
        kind: entry.kind,
        canonicalRuntimePrefix: entry.canonicalRuntimePrefix,
        repoRelative: "assets/" + value.slice(entry.prefix.length)
      };
    }
  }

  const cybermancyRoot = CYBERMANCY_ROOT_PREFIXES.find(prefix => value.startsWith(prefix));
  if (cybermancyRoot && (looksLikeMediaPath(value) || imageField(pointer))) {
    return {
      status: "outside-assets",
      raw: rawValue,
      normalized: value,
      prefix: cybermancyRoot,
      kind: "cybermancy-outside-assets",
      canonicalRuntimePrefix: false,
      repoRelative: null
    };
  }

  return null;
}

async function walkFiles(root, predicate) {
  const files = [];

  async function visit(directory) {
    const entries = await fs.readdir(directory, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));

    for (const entry of entries) {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        await visit(fullPath);
      } else if (entry.isFile() && predicate(fullPath)) {
        files.push(fullPath);
      }
    }
  }

  await visit(root);
  return files;
}

async function buildAssetIndex(assetRoot) {
  const files = await walkFiles(assetRoot, () => true);
  const exact = new Set();
  const lower = new Map();

  for (const file of files) {
    const rel = toPosix(path.relative(assetRoot, file));
    exact.add(rel);

    const key = rel.toLowerCase();
    const variants = lower.get(key) ?? [];
    variants.push(rel);
    lower.set(key, variants);
  }

  return { files, exact, lower };
}

function walkJson(value, pointer, visit) {
  if (typeof value === "string") {
    visit(value, pointer);
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((entry, index) => walkJson(entry, jsonPointerJoin(pointer, index), visit));
    return;
  }

  if (value && typeof value === "object") {
    for (const [key, entry] of Object.entries(value)) {
      walkJson(entry, jsonPointerJoin(pointer, key), visit);
    }
  }
}

function normalizeRepoAssetPath(repoRelative) {
  const withoutSuffix = stripQueryAndFragment(toPosix(repoRelative));
  const decoded = safeDecodePath(withoutSuffix);
  const normalized = path.posix.normalize(decoded).replace(/^\.\//, "");
  return normalized;
}

function evaluateReference(reference, assetIndex, strictPrefix) {
  if (reference.status === "outside-assets") {
    return {
      severity: "error",
      code: "CYBERMANCY_ASSET_OUTSIDE_CANONICAL_ROOT",
      message: "Cybermancy runtime image/token reference is not underneath /assets",
      target: null
    };
  }

  const normalizedRepoPath = normalizeRepoAssetPath(reference.repoRelative);
  const assetRel = normalizedRepoPath.startsWith("assets/")
    ? normalizedRepoPath.slice("assets/".length)
    : normalizedRepoPath;

  if (
    !normalizedRepoPath.startsWith("assets/") ||
    !assetRel ||
    assetRel === "." ||
    assetRel.startsWith("../") ||
    path.posix.isAbsolute(assetRel)
  ) {
    return {
      severity: "error",
      code: "CYBERMANCY_ASSET_PATH_ESCAPE",
      message: "Cybermancy runtime reference does not resolve safely underneath /assets",
      target: normalizedRepoPath
    };
  }

  if (!assetIndex.exact.has(assetRel)) {
    const caseVariants = assetIndex.lower.get(assetRel.toLowerCase()) ?? [];
    if (caseVariants.length) {
      return {
        severity: "error",
        code: "CYBERMANCY_ASSET_CASE_MISMATCH",
        message: `Asset path case does not match the tracked file: ${caseVariants.join(", ")}`,
        target: normalizedRepoPath
      };
    }

    return {
      severity: "error",
      code: "CYBERMANCY_ASSET_MISSING",
      message: "Referenced Cybermancy runtime asset is missing from /assets",
      target: normalizedRepoPath
    };
  }

  if (!reference.canonicalRuntimePrefix) {
    return {
      severity: strictPrefix ? "error" : "warning",
      code: strictPrefix
        ? "CYBERMANCY_ASSET_NONCANONICAL_PREFIX"
        : "CYBERMANCY_ASSET_LEGACY_PREFIX",
      message: strictPrefix
        ? "Reference resolves, but runtime prefix is not modules/cybermancy/assets/..."
        : "Reference resolves, but uses a legacy/non-module runtime prefix",
      target: normalizedRepoPath
    };
  }

  return {
    severity: "ok",
    code: "CYBERMANCY_ASSET_RESOLVED",
    message: "Reference resolves to /assets",
    target: normalizedRepoPath
  };
}

function summarizeBy(rows, selector) {
  const result = {};
  for (const row of rows) {
    const key = selector(row);
    result[key] = (result[key] ?? 0) + 1;
  }
  return Object.fromEntries(Object.entries(result).sort(([a], [b]) => a.localeCompare(b)));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = path.resolve(args.repoRoot);
  const packRoot = path.join(root, "src", "packs");
  const assetRoot = path.join(root, "assets");

  const [packStat, assetStat] = await Promise.all([
    fs.stat(packRoot).catch(() => null),
    fs.stat(assetRoot).catch(() => null)
  ]);

  if (!packStat?.isDirectory()) {
    throw new Error(`Canonical pack root not found: ${packRoot}`);
  }
  if (!assetStat?.isDirectory()) {
    throw new Error(`Canonical asset root not found: ${assetRoot}`);
  }

  const [jsonFiles, assetIndex] = await Promise.all([
    walkFiles(packRoot, file => file.toLowerCase().endsWith(".json")),
    buildAssetIndex(assetRoot)
  ]);

  const parseErrors = [];
  const references = [];
  let folderRecords = 0;
  let documentRecords = 0;

  for (const file of jsonFiles) {
    const sourceRel = toPosix(path.relative(root, file));
    let document;

    try {
      document = JSON.parse(await fs.readFile(file, "utf8"));
    } catch (error) {
      parseErrors.push({
        source: sourceRel,
        code: "INVALID_JSON",
        message: error instanceof Error ? error.message : String(error)
      });
      continue;
    }

    if (String(document?._key ?? "").startsWith("!folders!")) folderRecords += 1;
    else documentRecords += 1;

    walkJson(document, "", (value, pointer) => {
      const reference = classifyReference(value, pointer || "/");
      if (!reference) return;

      const evaluation = evaluateReference(reference, assetIndex, args.strictPrefix);
      references.push({
        source: sourceRel,
        pointer: pointer || "/",
        reference: reference.normalized,
        prefixKind: reference.kind,
        canonicalRuntimePrefix: reference.canonicalRuntimePrefix,
        target: evaluation.target,
        severity: evaluation.severity,
        code: evaluation.code,
        message: evaluation.message
      });
    });
  }

  const errors = [
    ...parseErrors.map(error => ({ ...error, severity: "error" })),
    ...references.filter(row => row.severity === "error")
  ];
  const warnings = references.filter(row => row.severity === "warning");
  const resolved = references.filter(row => row.severity === "ok");
  const uniqueTargets = new Set(
    references
      .filter(row => row.target)
      .map(row => row.target)
  );

  const report = {
    schema: "cybermancy-runtime-asset-validation-v1",
    status: errors.length ? "FAIL" : "PASS",
    strictPrefix: args.strictPrefix,
    repositoryRoot: root,
    canonicalPackRoot: "src/packs",
    canonicalAssetRoot: "assets",
    jsonFilesScanned: jsonFiles.length,
    documentRecords,
    folderRecords,
    assetFilesIndexed: assetIndex.files.length,
    referenceOccurrences: references.length,
    uniqueResolvedTargets: uniqueTargets.size,
    referencesByPrefixKind: summarizeBy(references, row => row.prefixKind),
    referencesByResult: summarizeBy(references, row => row.severity),
    errors,
    warnings
  };

  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(`Cybermancy runtime asset validation ${report.status}`);
    console.log(` - canonical JSON files scanned: ${report.jsonFilesScanned}`);
    console.log(` - document records: ${documentRecords}`);
    console.log(` - folder records: ${folderRecords}`);
    console.log(` - /assets files indexed: ${report.assetFilesIndexed}`);
    console.log(` - Cybermancy runtime asset references: ${report.referenceOccurrences}`);
    console.log(` - unique /assets targets referenced: ${report.uniqueResolvedTargets}`);

    for (const [kind, count] of Object.entries(report.referencesByPrefixKind)) {
      console.log(` - prefix ${kind}: ${count}`);
    }

    if (warnings.length) {
      console.log(` - noncanonical/legacy references (non-blocking): ${warnings.length}`);
    }

    if (errors.length) {
      console.error("");
      console.error(`Validation errors (${errors.length}):`);
      for (const error of errors) {
        if (error.pointer) {
          console.error(
            ` - [${error.code}] ${error.source}${error.pointer}: ${error.reference} -> ${error.message}`
          );
        } else {
          console.error(
            ` - [${error.code}] ${error.source}: ${error.message}`
          );
        }
      }
    }

    if (warnings.length) {
      console.warn("");
      console.warn(
        "Legacy/non-module prefixes resolve successfully. Run with --strict-prefix when the Foundry module migration is ready to require modules/cybermancy/assets/... everywhere."
      );
      for (const warning of warnings.slice(0, 25)) {
        console.warn(
          ` - ${warning.source}${warning.pointer}: ${warning.reference}`
        );
      }
      if (warnings.length > 25) {
        console.warn(` - ... ${warnings.length - 25} additional legacy references omitted`);
      }
    }
  }

  process.exit(errors.length ? 1 : 0);
}

main().catch(error => {
  console.error("Cybermancy runtime asset validation FAILED");
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exit(2);
});
