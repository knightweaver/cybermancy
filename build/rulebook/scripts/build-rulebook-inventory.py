#!/usr/bin/env python3
import sys
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-inventory.py.impl")
_STRICT_IMPL = _PUBLIC.with_name("rulebook_inventory_strict.py")

if __name__ == "__main__":
    implementation = _STRICT_IMPL if "--strict" in sys.argv[1:] else _IMPL
    raise SystemExit(run_implementation(_PUBLIC, implementation))
else:
    expose_implementation(globals(), _PUBLIC, _IMPL, __name__)
