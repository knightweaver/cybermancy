# Cybermancy script guide

11/9/2025 At this point I have all the documentation process working, including:
 - Scripts to take a CSV (or Excel file) with new items listings across all the object types in Foundry  
 - Scripts to take a set of JSON files output with the foundrycli unpack command and reskin them
 - Scripts to run the ChatGPT APIs to generate icon images in bulk and cheaply
 - Commands to unpack all the contents of the Cybermancy compendia
 - Scripts to autogenerate a complete set of Cybermancy docs from the foundrycli unpacked compendia

Below I plan to catalog all the scripts, their usage, their command line calls, and any future plans.  I will attempt to do so in the order of the script's importance for ongoing Cybermancy content development work, but we'll see how good that order is.  This is far enough along that as of completing this documentation exercise, I plan to stop script and code development except for fixing any bugs or issues that arise.

---

## <u>Most commonly used scripts and commands:</u>

## Foundrycli Commands

Foundry-cli is an open source project to help Foundry Compendia content makers unpack and re-pack Compendia for various purposes, among these are documentation efforts like mine.

Look a the current configuration:
 - `fvtt configure view`

For our project that should output this:
```
Current Configuration: {
  currentPackageId: 'cybermancy',
  currentPackageType: 'Module',
  dataPath: 'E:\\FoundryVTT',
  installPath: 'E:\\Program Files\\Foundry Virtual Tabletop'
}
```
Unpack a specific compendia (note how the package path maps to the compendia configuration in the modules.json file, "packs/system/classes.db" in this example:
 - `fvtt package unpack -n "system/classes" --outputDirectory "src/packs/system/classes"`

---
## `generate-docs.py`

Builds Cybermancy documentation in Markdown and CSV.

- **Input**: All item/system JSONs under `src/packs/`
- **Output**:
  - Markdown detail pages in `docs/`
  - CSV indexes in `docs/data/`
- **Features**:
  - Tier-based sorting
  - Action/effect summary rendering
  - Folder mapping for UUID display

### Example cli usages:
 - Generate all docs:
   - `py .\pyCybermancy\generate-docs.py`
 - Generate the docs just for one type:
   - `py .\pyCybermancy\generate-docs.py --type classes`

---

# Mkdocs-material commands

Mkdocs-Material is the general open source package and approach that is used to generate the final docs from the prior 2 steps.  The installation command and the command for testing it out locally are below, but generally this is run via the Github Actions "docs.yml"

`pip install mkdocs mkdocs-material mkdocs-include-markdown-plugin mkdocs-macros-plugin`

`python -m mkdocs serve --config-file mkdocs.player.yml --dev-addr 127.0.0.1:8001`

---

---

## <u>Additional and legacy utility scripts</u>

---

## `batch-image-generation-on-OpenAI.py`

Generates Cybermancy item icons using the OpenAI image API.  Generally usage is to generate a .csv file with the following headers

| name | Description | Style                              | Effect                   | Image Root Name                    | Organ (optional)          |
|------| ----------- |------------------------------------|--------------------------|--------------------------|---------------------------|
| foo | bar | General category<br/>(e.g. "Item") | specific<br/>subcategory | smart-gun<br/>(no .webp) | (only used<br/>by cybernetics) |


- **Input**: CSV/JSON of items with `name`, `description`, `effect`, `style`, and `organ`
- **Logic**:
  - Builds prompts using style/effect palettes
  - Special rendering logic for cybernetics
- **Output**: `.webp` images

` py .\batch-image-generation-on-OpenAI.py --input .\cybernetic-img-request-list.csv --outdir cybernetics`

Full help info:

```
usage: batch-image-generation-on-OpenAI.py [-h] --input INPUT --outdir OUTDIR [--model MODEL] [--size SIZE] [--delay DELAY] [--max-items MAX_ITEMS] [--seed SEED] [--overwrite] [--name-key NAME_KEY] [--desc-key DESC_KEY] [--effect-key EFFECT_KEY] [--img-key IMG_KEY] [--style-key STYLE_KEY]
                                           [--organ-key ORGAN_KEY] [--log-level LOG_LEVEL]

Batch-generate Cybermancy icons via OpenAI Images API (per-row styles).

options:
  -h, --help            show this help message and exit
  --input, -i INPUT     Path to input CSV or JSON.
  --outdir, -o OUTDIR   Output directory for .webp files.
  --model MODEL         Image model.
  --size SIZE           Image size (e.g., 1024x1024).
  --delay DELAY         Delay between requests.
  --max-items MAX_ITEMS
                        0 = all.
  --seed SEED           Optional seed.
  --overwrite           Overwrite existing outputs.
  --name-key NAME_KEY
  --desc-key DESC_KEY
  --effect-key EFFECT_KEY
  --img-key IMG_KEY
  --style-key STYLE_KEY
  --organ-key ORGAN_KEY
  --log-level LOG_LEVEL
```
---

## `feature-descriptor-to-loadable.py`

Builds loadable JSON for Daggerheart/Cybermancy Features and Domain Cards.

This became the main converter function to take the content of my cybermancy-item.xlsx spreadsheet and generate loadable JSON. 

- **Input**: CSV, JSON, or Excel
- **Includes**: Full action block builder, folder routing
- **Output**: JSONs organized by domain/class/subclass
- **Supports**: Actions, damage, saves, costs, rolls, uses

### Example cli usages:
` py .\feature-descriptor-to-loadable.py -o ammo-items --sheet Ammo .\cybermancy-object-list.xlsx`

Full help info:

```usage: feature-descriptor-to-loadable.py [-h] -o OUT [--sheet SHEET] descriptor

Build Daggerheart Feature/Domain Card Items with configured Action from CSV/JSON/Excel descriptors.

positional arguments:
  descriptor     CSV, JSON (array/object), or Excel (.xlsx/.xlsm/.xls)

options:
  -h, --help     show this help message and exit
  -o, --out OUT  Output directory
  --sheet SHEET  Excel sheet name or 0-based index when reading .xlsx/.xlsm/.xls
  ```

#### NOTE: check out the cybermancy-items.xlsx file to see how the sheets are built.

---

## `organize-by-tier.py`

Moves item JSON files into subfolders by numeric tier.  A simple helper function to organize the loadable JSON files, such that they can be moved into sensible folders in Foundry easily (by Tier).

- **Input**: Folder of JSON files
- **Options**:
  - `--format` for folder names
  - `--unknown-dir` for missing tiers
  - `--dry-run`, `--verbose`

Full help info:
```usage: organize-by-tier.py [-h] [--glob GLOB] [--format FORMAT] [--unknown-dir UNKNOWN_DIR] [--dry-run] [--verbose] root

Organize Cybermancy JSON items by tier.

positional arguments:
  root                  Folder containing JSON item files

options:
  -h, --help            show this help message and exit
  --glob GLOB           Glob for item files relative to root (default: *.json)
  --format FORMAT       Subfolder naming format (default: "tier-{tier}")
  --unknown-dir UNKNOWN_DIR
                        If set, files without a numeric tier go here (subfolder name)
  --dry-run             Show planned moves without changing files
  --verbose             Print each move
  ```
---
## `batch-marketing-blurb-generator.py`

Creates short poetic marketing blurbs for cybernetic implants.  This was a mostly throw-away script to fulfill a particular task and has not been generalized like the other scripts.  To use this for a different task currently requires editing the code as there are no command line options.

- **Input**: CSV with `cybernetic-upgrade-name`, `description`, `corp`
- **Output**: New CSV with an added `marketing_blurb` column
- **Model**: OpenAI GPT-4o
- **Tone**: Randomly chosen from 5 thematic styles

---

## `convert_and_resize_png_to_webp.py`

Batch converts `.png` images to `.webp` with resizing.  Pretty straight-forward utility function that I needed when I shifted from manually triggered image and icon generation to .webp and batch calls to the API.

- **Input**: PNG images in a folder
- **Options**: `--width`, `--height`, `--dpi`, `--recursive`
- **Output**: Overwrites original PNGs with `.webp`

Full help info:
```
usage: convert_and_resize_png_to_webp.py [-h] --width WIDTH --height HEIGHT [--dpi DPI] [--recursive] [--quality QUALITY] [--lossless] folder

Resize all PNGs in a folder and convert to .webp (replacing originals).

positional arguments:
  folder                Folder containing PNG images

options:
  -h, --help            show this help message and exit
  --width, -W WIDTH     Target width in pixels
  --height, -H HEIGHT   Target height in pixels
  --dpi DPI             Target DPI metadata (may be ignored by some tools)
  --recursive, -r       Recurse into subfolders
  --quality, -q QUALITY
                        WEBP quality (0-100, ignored if --lossless)
  --lossless            Use lossless WebP
  ```
---

## `retitle_items_and_zip.py`

Renames Foundry item files using a CSV mapping.

One of the 3 approaches I took to seed the Cybermancy compendia was to "reskin" the Daggerheart items, by just changing the name, description, and images.  A good example of this approach was the armor, which translated very well.  

This approach was favored, when the original DH items seemed well balanced already for Cybermancy (e.g. armor)

- **Input**: Original JSON files + CSV with `old_name`, `new_name`, `new_description`, `img-path`
- **Output**: New JSON files in a clean folder with safe filenames

Full help info:
```
usage: retitle_items_and_zip.py [-h] [-o OUTPUT_DIR] input_dir mapping_csv

Retitle Daggerheart armor items for Cybermancy.

positional arguments:
  input_dir             Folder containing original armor JSON files.
  mapping_csv           CSV mapping file (old_name,new_name,new_description,img-path).

options:
  -h, --help            show this help message and exit
  -o, --output-dir OUTPUT_DIR
                        Output folder for transformed JSON files.

```
---

## `setup-cybermancy-docs.py`

Bootstraps the full Cybermancy documentation directory structure.  Just a utility script to create all the folders needed by the Mkdocs-Material approach to the documentation.

- **Creates**:
  - `src/packs/{items,system,adventure}`
  - `docs/{player-facing,gm-facing}`
  - Markdown index stubs for all sections
- **Usage**: Run once per new repo

---

## `convert-descriptors-to-loadable.py`

Maps flat descriptors to a Foundry JSON template. 

I believe that this has been superceded by the feature-descriptor-to-loadable.py file, but I'm too much of a pack-rat to delete it from the project yet.  The concept of this approach was to have a template JSON file and then 

- **Input**: CSV or JSON array + template JSON
- **Features**:
  - JSON path support in headers
  - `{{ColumnName}}` interpolation in template
- **Output**: `.json` files per row

---

## `convert-loot-json-to-csv.py`

Converts Cybermancy loot items from JSON to CSV.

This script was one of my steps for reskinning DH content to Cybermancy.  This script took the foundrycli unpacked JSON files and loaded their content into a csv for easier editing.  Given that the reskinning is all done, I doubt that this script will be used again.

- **Input**: `loot_cybermancy_generated.json`
- **Output**: `loot_cybermancy_generated.csv`
- **Adds**: `img-path` field for Foundry usage

---