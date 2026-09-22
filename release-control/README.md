# Cybermancy release control

Release-control JSON is added only **after** the exact runtime candidate has been
manually qualified in a clean Foundry installation.

For the v0.1.13 baseline:

1. Merge the release-preparation PR.
2. Let **Build Cybermancy Release Candidate** create the runtime artifact.
3. Download and install that exact ZIP in a clean Foundry 13 / Daggerheart 1 instance.
4. Record the successful candidate workflow run ID, artifact name, and ZIP SHA-256.
5. Add `release-control/v0.1.13.json` with `qualification.status = "PASS"`.
6. Merging that control file to `main` triggers **Publish Cybermancy Release**.

The compatibility manifest records supported **major versions** only. Exact point
versions used for qualification belong in test evidence or release notes, not in
Foundry/Daggerheart compatibility constraints.
