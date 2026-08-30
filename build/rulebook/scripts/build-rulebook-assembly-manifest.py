#!/usr/bin/env python3
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation
from rulebook_freeze_artifacts import configure_assembly_markdown_consistency
from rulebook_step3_architecture import configure_class_package_architecture

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-assembly-manifest.py.impl")


def _configure(namespace):
    configure_class_package_architecture(namespace)
    configure_assembly_markdown_consistency(namespace)


if __name__ == "__main__":
    raise SystemExit(
        run_implementation(
            _PUBLIC,
            _IMPL,
            configure=_configure,
        )
    )
else:
    expose_implementation(
        globals(),
        _PUBLIC,
        _IMPL,
        __name__,
        configure=_configure,
    )
