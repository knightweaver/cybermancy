#!/usr/bin/env python3
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation
from rulebook_freeze_artifacts import configure_publication_snapshot_summary

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-publication-manifest.py.impl")

if __name__ == "__main__":
    raise SystemExit(
        run_implementation(
            _PUBLIC,
            _IMPL,
            configure=configure_publication_snapshot_summary,
        )
    )
else:
    expose_implementation(
        globals(),
        _PUBLIC,
        _IMPL,
        __name__,
        configure=configure_publication_snapshot_summary,
    )
