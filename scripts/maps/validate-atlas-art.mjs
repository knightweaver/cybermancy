import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const manifestPath = path.join(root, "art-production", "seattle-lore", "cybermancy-seattle-lore-art-manifest-v0.1.json");
const sharedImageDir = path.join(root, "docs", "_shared", "assets", "images", "locations");
const gmAtlasDir = path.join(root, "docs", "gm-facing", "assets", "atlas");
const datasetNames = ["regions.geojson", "districts.geojson", "context.geojson"];
const publicAssetPrefix = "images/locations/";
const readJson = async (filePath) => JSON.parse(await readFile(filePath, "utf8"));

const manifest = await readJson(manifestPath);
const enabledItems = (manifest.items ?? []).filter((item) => String(item.enabled).toLowerCase() === "true");
const sharedFiles = new Set(await readdir(sharedImageDir));
const manifestKeys = new Set();
const manifestOutputs = new Set();
const failures = [];
const fail = (message) => failures.push(message);

for (const item of enabledItems) {
  const key = `${item.source_dataset}::${String(item.source_feature_id)}`;
  if (!datasetNames.includes(item.source_dataset)) {
    fail(`Manifest item ${item.record_id}: unsupported source_dataset ${item.source_dataset}`);
    continue;
  }
  if (manifestKeys.has(key)) fail(`Duplicate manifest source key: ${key}`);
  manifestKeys.add(key);
  if (!item.output_filename) {
    fail(`Manifest item ${item.record_id}: output_filename is required`);
    continue;
  }
  if (manifestOutputs.has(item.output_filename)) fail(`Duplicate manifest output filename: ${item.output_filename}`);
  manifestOutputs.add(item.output_filename);
  if (!sharedFiles.has(item.output_filename)) fail(`Manifest output missing from shared location art: ${item.output_filename}`);
}

for (const filename of datasetNames) {
  const dataset = await readJson(path.join(gmAtlasDir, filename));
  const byId = new Map(dataset.features.map((feature) => [String(feature.id), feature]));

  for (const item of enabledItems.filter((entry) => entry.source_dataset === filename)) {
    const feature = byId.get(String(item.source_feature_id));
    if (!feature) {
      fail(`${filename}: manifest feature ${item.source_feature_id} not found`);
      continue;
    }
    const expectedAsset = `${publicAssetPrefix}${item.output_filename}`;
    if (feature.properties?.image_asset !== expectedAsset) {
      fail(`${filename} feature ${feature.id}: image_asset must be "${expectedAsset}"`);
    }
  }

  for (const feature of dataset.features) {
    const imageAsset = feature.properties?.image_asset;
    if (!imageAsset) continue;
    if (!imageAsset.startsWith(publicAssetPrefix)) {
      fail(`${filename} feature ${feature.id}: unexpected image_asset path "${imageAsset}"`);
      continue;
    }
    const outputFilename = imageAsset.slice(publicAssetPrefix.length);
    if (!sharedFiles.has(outputFilename)) fail(`${filename} feature ${feature.id}: shared image not found: ${outputFilename}`);
    if (!manifestKeys.has(`${filename}::${String(feature.id)}`)) fail(`${filename} feature ${feature.id}: image_asset has no enabled manifest mapping`);
  }
}

for (const filename of sharedFiles) {
  if (filename.toLowerCase().endsWith(".webp") && !manifestOutputs.has(filename)) {
    fail(`Shared location image has no enabled manifest mapping: ${filename}`);
  }
}

if (failures.length) {
  failures.forEach((message) => console.error(`FAIL ${message}`));
  process.exitCode = 1;
} else {
  console.log(`OK Seattle atlas art: ${enabledItems.length} manifest items, ${manifestOutputs.size} mapped assets, ${[...sharedFiles].filter((name) => name.toLowerCase().endsWith(".webp")).length} shared WebP files`);
}
