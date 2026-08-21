# Rulebook script notes

commit Cybermancy changes
        ↓
rebuild inventory
        ↓
rebuild Step 2 publication manifest
        ↓
rebuild Step 3 assembly manifest
        ↓
python build/rulebook/scripts/build-rulebook-source.py validate
        ↓
python build/rulebook/scripts/build-rulebook-source.py build


1. Build the rulebook inventory:
`python.exe .\scripts\build-rulebook-inventory.py --repo-root ..\..\  `

2. Rebuild the rulebook publication manifest
`python rebuild-rulebook-publication-manifest.py ^
  --template cybermancy-rulebook-publication-manifest-v1.2.json ^
  --inventory rulebook-inventory.json ^
  --inventory-csv rulebook-inventory.csv ^
  --inventory-report rulebook-inventory-report.md ^
  --output-dir .`

`python rebuild-rulebook-publication-manifest.py --template cybermancy-rulebook-publication-manifest-v1.2.json   --inventory rulebook-inventory.json --inventory-csv rulebook-inventory.csv --inventory-report rulebook-inventory-report.md --output-dir .`

3. Rebuild the rulebook assembly manifest
`python .\scripts\build-rulebook-assembly-manifest.py`

4. Validate the build rulebook sources
`python pyCybermancy/build-rulebook-source.py validate \
  --publication-manifest cybermancy-rulebook-publication-manifest-v1.1.json \
  --assembly-manifest cybermancy-rulebook-assembly-manifest-v1.1.json \
  --config cybermancy-rulebook-normalization-config-v1.0.json \
  --repo-root . \
  --output-root build/rulebook`

`python pyCybermancy/build-rulebook-source.py validate --publication-manifest cybermancy-rulebook-publication-manifest-v1.1.json --assembly-manifest cybermancy-rulebook-assembly-manifest-v1.1.json --config cybermancy-rulebook-normalization-config-v1.0.json --repo-root . --output-root build/rulebook`

5. Build the rulebook source

 - Same command as above, but with "build" rather than "validate"