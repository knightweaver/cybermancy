import { isDeepStrictEqual } from "node:util";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const mode = process.argv.includes("--write") ? "write" : "check";
const root = process.cwd();
const datasetNames = ["regions.geojson", "districts.geojson", "context.geojson"];
const validAudiences = new Set(["gm", "player"]);
const validMapScopes = new Set(["regional", "seattle", "both"]);
const validContextCategories = new Set([
  "landmark",
  "transit",
  "corporate",
  "hazard",
  "settlement",
  "event",
  "route",
]);
const privatePropertyNames = new Set(["adventure_hooks", "events"]);

const readJson = async (filePath) => JSON.parse(await readFile(filePath, "utf8"));

const publicProperties = (properties) => Object.fromEntries(
  Object.entries(properties).filter(([key]) => (
    key !== "audience"
      && !key.startsWith("gm_")
      && !privatePropertyNames.has(key)
  )),
);

const publicDataset = (dataset) => ({
  ...dataset,
  features: dataset.features
    .filter((feature) => feature.properties.audience === "player")
    .map((feature) => ({
      ...feature,
      properties: publicProperties(feature.properties),
    })),
});

const validateDataset = (dataset, filename) => {
  if (dataset.type !== "FeatureCollection" || !Array.isArray(dataset.features)) {
    throw new Error(`${filename}: expected a GeoJSON FeatureCollection`);
  }

  const ids = new Set();
  for (const feature of dataset.features) {
    if (feature.id === undefined || feature.id === null || feature.id === "") {
      throw new Error(`${filename}: every feature requires a stable id`);
    }
    if (ids.has(feature.id)) throw new Error(`${filename}: duplicate feature id ${feature.id}`);
    ids.add(feature.id);

    const audience = feature.properties?.audience;
    if (!validAudiences.has(audience)) {
      throw new Error(`${filename} feature ${feature.id}: audience must be "gm" or "player"`);
    }

    if (filename === "context.geojson") {
      if (!validContextCategories.has(feature.properties.category)) {
        throw new Error(`${filename} feature ${feature.id}: invalid context category ${feature.properties.category}`);
      }
      if (!validMapScopes.has(feature.properties.map_scope)) {
        throw new Error(`${filename} feature ${feature.id}: map_scope must be "regional", "seattle", or "both"`);
      }
    }
  }
};

const writeJsonAtomically = async (filePath, value) => {
  await mkdir(path.dirname(filePath), { recursive: true });
  const temporaryPath = `${filePath}.tmp`;
  await writeFile(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await rename(temporaryPath, filePath);
};

let failures = 0;

for (const filename of datasetNames) {
  const gmPath = path.join(root, "docs", "gm-facing", "assets", "atlas", filename);
  const playerPath = path.join(root, "docs", "player-facing", "assets", "atlas", filename);
  const gmData = await readJson(gmPath);
  const playerData = await readJson(playerPath);
  validateDataset(gmData, filename);
  const expectedPlayerData = publicDataset(gmData);

  if (isDeepStrictEqual(expectedPlayerData, playerData)) {
    console.log(`OK ${filename}`);
    continue;
  }

  if (mode === "write") {
    await writeJsonAtomically(playerPath, expectedPlayerData);
    console.log(`SYNCED ${filename}`);
  } else {
    console.error(`DRIFT ${filename}: run npm run atlas:sync`);
    failures += 1;
  }
}

if (failures > 0) process.exitCode = 1;
