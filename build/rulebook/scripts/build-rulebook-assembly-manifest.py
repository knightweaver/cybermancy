#!/usr/bin/env python3
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation
from rulebook_step3_architecture import configure_class_package_architecture

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-assembly-manifest.py.impl")

if __name__ == "__main__":
    raise SystemExit(
        run_implementation(
            _PUBLIC,
            _IMPL,
            configure=configure_class_package_architecture,
        )
    )
else:
    expose_implementation(
        globals(),
        _PUBLIC,
        _IMPL,
        __name__,
        configure=configure_class_package_architecture,
    )
