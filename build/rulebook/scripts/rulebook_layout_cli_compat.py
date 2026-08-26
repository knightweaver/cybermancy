from __future__ import annotations

from typing import Any


def configure_layout_machine_output(namespace: dict[str, Any]) -> None:
    """Preserve JSON stdout for Step 6's internal Equipment child processes.

    The public rulebook CLIs are terse by default. The Equipment `--all` flow,
    however, launches the same layout CLI recursively and parses each child's
    legacy JSON stdout. Those machine-to-machine child invocations therefore
    explicitly request `--verbose`; direct user invocations remain terse.
    """
    from rulebook_layout import equipment_batch

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
