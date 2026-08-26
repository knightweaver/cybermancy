#!/usr/bin/env python3
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-inventory.py.impl")

if __name__ == "__main__":
    raise SystemExit(run_implementation(_PUBLIC, _IMPL))
else:
    expose_implementation(globals(), _PUBLIC, _IMPL, __name__)
