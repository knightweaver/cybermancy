# Rulebook CLI output contract

All production Python entrypoints directly under `build/rulebook/scripts/` now use a shared output wrapper.

Default execution is intentionally terse:

```text
build-rulebook-source.py: PASS
```

On failure the script prints `FAIL`, retains the non-zero exit code, and emits the captured error/diagnostic lines needed to identify the failure. Routine progress and full report output are suppressed.

Use `--verbose` anywhere before a literal `--` separator to restore the previous full script output:

```powershell
python build\rulebook\scripts\build-rulebook-source.py validate --verbose
```

`-h` / `--help` remains full-output and includes a note describing the global `--verbose` option.

To avoid risky edits to ten independently evolved command-line parsers, the public `.py` files are stable wrappers. Their unchanged prior implementations are stored beside them as `.py.impl` files. The wrapper executes the implementation with the public script path preserved as `__file__`, so existing repository-root discovery and import-based regression tests retain their previous behavior. `.py.impl` files are implementation sources, not command-line entrypoints.
