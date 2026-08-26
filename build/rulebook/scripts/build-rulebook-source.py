#!/usr/bin/env python3
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation
from rulebook_step4_class_publication_images import (
    configure_step4_class_publication_images,
)
from rulebook_step4_class_relationships import configure_step4_class_relationships

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-source.py.impl")


def _configure(namespace):
    configure_step4_class_relationships(namespace)
    configure_step4_class_publication_images(namespace)


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
