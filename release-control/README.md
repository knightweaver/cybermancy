# Cybermancy release control

Release-control JSON is added only **after** the exact runtime candidate for that
version has been manually qualified in a clean Foundry installation.

For the current Foundry 14 / Daggerheart 2 release line:

1. Merge the release-preparation PR containing the new semantic version, download
   URL, release notes, and any release-pipeline changes.
2. Let **Build Cybermancy Release Candidate** create
   `cybermancy-runtime-candidate-v<version>` from the merged `main` commit.
3. Download and install that exact runtime ZIP in the qualification target
   (currently Foundry 14.368 / Daggerheart 2.10.5).
4. Record the successful candidate workflow run ID, artifact name, inner runtime
   ZIP SHA-256, and clean-install qualification result.
5. Add `release-control/v<version>.json` with `publish: true` and
   `qualification.status: "PASS"`.
6. Merge that release-control file to `main`. **Publish Cybermancy Release**
   resolves the release-control JSON changed by that push, rebuilds and validates
   the runtime, proves equivalence with the exact qualified candidate, and
   publishes the semantic GitHub release.

For a manual `workflow_dispatch`, supply the release-control path explicitly.
The publish workflow does not fall back to an older control file.

The compatibility manifest records supported **major versions** only. Exact point
versions used for qualification belong in test evidence or release notes, not in
Foundry/Daggerheart compatibility constraints.
