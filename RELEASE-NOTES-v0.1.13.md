# Cybermancy v0.1.13

Pre-migration baseline release of the Cybermancy Daggerheart extension.

## Compatibility

- Foundry VTT 13
- Daggerheart 1

Compatibility metadata intentionally uses major versions rather than point
releases.

## Release baseline

This release establishes the clean-install baseline immediately before the
Foundry 14 / Daggerheart 2 migration work.

It includes the current compiled Cybermancy Compendia, canonical runtime artwork,
Cybermancy runtime initialization, custom Domain registration, styles, templates,
and localization resources.

The release archive is published only after the exact candidate artifact has
passed clean-install qualification. The published ZIP is the same artifact that
was manually qualified; a fresh rebuild must match it except for ephemeral
LevelDB `LOG` and `LOG.old` content.
