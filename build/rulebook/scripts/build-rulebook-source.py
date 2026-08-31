#!/usr/bin/env python3
from pathlib import Path

from rulebook_cli import expose_implementation, run_implementation
from rulebook_git_source_identity import configure_step4_authored_source_identity
from rulebook_step4_class_publication_images import (
    configure_step4_class_publication_images,
)
from rulebook_step4_class_relationships import configure_step4_class_relationships
from rulebook_step4_domain_semantics import configure_step4_domain_semantics
from rulebook_step4_encounter_semantics import configure_step4_encounter_semantics
from rulebook_step4_feature_equivalence import configure_step4_feature_equivalence
from rulebook_step4_feature_publication_equivalence import (
    configure_step4_feature_publication_equivalence,
)
from rulebook_step4_ice_publication_image_overrides import (
    configure_step4_ice_publication_image_overrides,
)
from rulebook_step4_ice_publication_images import (
    configure_step4_ice_publication_images,
)
from rulebook_step4_ice_semantics import configure_step4_ice_semantics
from rulebook_step4_prose_boundaries import configure_step4_prose_boundaries

_PUBLIC = Path(__file__).resolve()
_IMPL = _PUBLIC.with_name("build-rulebook-source.py.impl")


def _configure(namespace):
    configure_step4_authored_source_identity(namespace)
    configure_step4_class_relationships(namespace)
    configure_step4_class_publication_images(namespace)
    configure_step4_domain_semantics(namespace)
    configure_step4_prose_boundaries(namespace)
    configure_step4_ice_semantics(namespace)
    configure_step4_ice_publication_image_overrides(namespace)
    configure_step4_ice_publication_images(namespace)
    configure_step4_encounter_semantics(namespace)
    # Audit the final reader-safe standalone Feature projection first.
    configure_step4_feature_equivalence(namespace)
    # Then apply the reviewed/approved publication representative decisions.
    # This preserves every canonical entity while marking the deterministic
    # Chapter 32 representative set and reader-neutral family entries.
    configure_step4_feature_publication_equivalence(namespace)


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
