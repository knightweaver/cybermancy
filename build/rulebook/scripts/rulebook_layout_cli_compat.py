from __future__ import annotations

from typing import Any


STEP4_CLASS_RELATIONSHIP_SCHEMA = "cybermancy-step4-structured-entities-v1.3"


def configure_layout_machine_output(namespace: dict[str, Any]) -> None:
    """Preserve Step 6 machine output and current Step 4 sidecar compatibility.

    The public rulebook CLIs are terse by default. The Equipment `--all` flow,
    however, launches the same layout CLI recursively and parses each child's
    legacy JSON stdout. Those machine-to-machine child invocations therefore
    explicitly request `--verbose`; direct user invocations remain terse.

    Step 4 v1.3 adds Class/Subclass relationship semantics without changing the
    accepted Equipment publication fields, so Equipment readers continue to
    accept v1.1/v1.2 while also accepting v1.3.
    """
    from rulebook_layout import equipment_batch, equipment_bootstrap

    supported = namespace.get("SUPPORTED_SIDECAR_SCHEMAS")
    if isinstance(supported, set):
        supported.add(STEP4_CLASS_RELATIONSHIP_SCHEMA)
    equipment = namespace.get("EQUIPMENT_SIDECAR_SCHEMAS")
    if isinstance(equipment, set):
        equipment.add(STEP4_CLASS_RELATIONSHIP_SCHEMA)
    equipment_bootstrap.SIDECAR_SCHEMAS.add(STEP4_CLASS_RELATIONSHIP_SCHEMA)

    if getattr(equipment_batch, "_rulebook_verbose_child_patch", False):
        return

    original_child_command = equipment_batch._child_command

    def child_command(*args: Any, **kwargs: Any) -> list[str]:
        command = list(original_child_command(*args, **kwargs))
        if "--verbose" not in command:
            command.append("--verbose")
        return command

    equipment_batch._child_command = child_command
    equipment_batch._rulebook_verbose_child_patch = True
