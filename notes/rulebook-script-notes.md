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
`python.exe .\build\rulebook\scripts\build-rulebook-inventory.py --repo-root ..\..\  `

2. Rebuild the rulebook publication manifest
`python build\rulebook\scripts\build-rulebook-publication-manifest.py`

3. Rebuild the rulebook assembly manifest
`python .\build\rulebook\scripts\build-rulebook-assembly-manifest.py`

4. Validate the build rulebook sources
`python build\rulebook\scripts\build-rulebook-source.py validate --verbose`

`python pyCybermancy/build-rulebook-source.py build`

5. Build the rulebook source

 - Same command as above, but with "build" rather than "validate"