python -m unittest discover -s build\rulebook\scripts\tests -p "test_step6_integration_equipment.py" -v

# Step 1 — fresh inventory at current HEAD
python build\rulebook\scripts\build-rulebook-inventory.py

# Step 2 — refresh the frozen publication manifest
# Preserves the existing authority decisions and recomputes source/family digests
python build\rulebook\scripts\build-rulebook-publication-manifest.py

# Step 3 — rebuild the assembly manifest from the new Step 2 manifest
python build\rulebook\scripts\build-rulebook-assembly-manifest.py

# Step 4 — regenerate the compatible normalization artifacts/config
python build\rulebook\scripts\build-rulebook-normalization-artifacts.py

# Step 4 — validate and rebuild normalized publication source
python build\rulebook\scripts\build-rulebook-source.py validate
python build\rulebook\scripts\build-rulebook-source.py build