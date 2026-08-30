# Cybermancy build tooling

Routine Cybermancy rulebook maintenance is documented in
[`rulebook/MAINTENANCE-WORKFLOW.md`](rulebook/MAINTENANCE-WORKFLOW.md).

From the repository root, use the supported maintenance entrypoint:

```powershell
python build\rulebook\scripts\maintain-rulebook.py status
```

The maintenance runbook documents the supported `prepare`, `build`, and `release`
workflows, as well as the underlying diagnostic commands.
