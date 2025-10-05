// tools/convert-icons.mjs
// Node 18+ recommended
import fs from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";
import sharp from "sharp";
import pc from "picocolors";

/**
 * ---- CONFIG ----
 * inputDir:  where your downloaded icons live (svg/png)
 * outputDir: where .webp files will be written
 * sizePx:    set to a number to force square size (e.g., 256 or 512), or null to keep original
 * quality:   0–100 (85–90 is a good starting point)
 */
const inputDir  = "assets/icons_src";    // e.g., game-icons.net downloads
const outputDir = "public/icons_webp";   // where Foundry will load from
const sizePx    = 256;                   // set to null to keep source size
const quality   = 90;                    // WebP quality
const concurrency = 8;                   // parallel conversions

async function ensureDir(p) {
  await fs.mkdir(p, { recursive: true });
}

function relOutPath(file) {
  const rel = path.relative(inputDir, file);
  const out = path.join(outputDir, rel).replace(/\.(png|svg)$/i, ".webp");
  return out;
}

/**
 * Convert one file → .webp
 */
async function convertFile(inPath) {
  const outPath = relOutPath(inPath);
  await ensureDir(path.dirname(outPath));

  // Skip if output is newer than input (simple incremental build)
  try {
    const [inStat, outStat] = await Promise.all([
      fs.stat(inPath),
      fs.stat(outPath)
    ]);
    if (outStat.mtimeMs >= inStat.mtimeMs) {
      console.log(pc.dim(`skip  ${path.relative(process.cwd(), outPath)} (up-to-date)`));
      return;
    }
  } catch {
    // If stat fails for outPath we simply continue to convert
  }

  // Build sharp pipeline
  // For SVG, set a higher density so downsizing is crisp.
  const isSvg = /\.svg$/i.test(inPath);
  const input = isSvg ? sharp(inPath, { density: 384 }) : sharp(inPath);

  let pipeline = input;
  if (sizePx) {
    // Game icons are usually square; cover ensures square output
    pipeline = pipeline.resize(sizePx, sizePx, { fit: "cover" });
  }

  // Alpha channels preserved; near-lossless works well for flat icons.
  pipeline = pipeline.webp({
    quality,
    effort: 6,         // 0–6, higher = smaller but slower
    alphaQuality: 90,  // transparency quality
    lossless: false    // set true if you want fully lossless (bigger files)
  });

  await pipeline.toFile(outPath);
  console.log(pc.green(`made  ${path.relative(process.cwd(), outPath)}`));
}

/**
 * Runner
 */
async function main() {
  const patterns = [
    path.join(inputDir, "**/*.png").replaceAll("\\", "/"),
    path.join(inputDir, "**/*.svg").replaceAll("\\", "/"),
  ];
  const files = await fg(patterns, { dot: false });

  if (files.length === 0) {
    console.log(pc.yellow(`No .svg or .png found under: ${inputDir}`));
    return;
  }

  console.log(pc.cyan(`Converting ${files.length} file(s) → ${outputDir} as .webp`));
  await ensureDir(outputDir);

  // Simple concurrency control
  let i = 0;
  async function worker() {
    while (i < files.length) {
      const idx = i++;
      try {
        await convertFile(files[idx]);
      } catch (err) {
        console.error(pc.red(`fail  ${files[idx]}\n${err?.stack || err}`));
      }
    }
  }

  await Promise.all(Array.from({ length: concurrency }, worker));
  console.log(pc.bold(pc.green("Done.")));
}

main().catch(err => {
  console.error(pc.red(err?.stack || err));
  process.exit(1);
});
