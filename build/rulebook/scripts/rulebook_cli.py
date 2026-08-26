from __future__ import annotations

import contextlib
import io
import re
import sys
import traceback
import types
from pathlib import Path
from typing import Any, Callable

ConfigureHook = Callable[[dict[str, Any]], None]
_ERROR_RE = re.compile(r"\b(?:ERROR|FAIL(?:ED)?|FATAL|EXCEPTION|TRACEBACK)\b", re.IGNORECASE)


def _load_namespace(
    public_path: Path,
    implementation_path: Path,
    module_name: str,
    configure: ConfigureHook | None = None,
) -> dict[str, Any]:
    """Load an implementation while preserving the public script's __file__ contract."""
    source = implementation_path.read_text(encoding="utf-8")
    module = types.ModuleType(module_name)
    namespace = module.__dict__
    namespace.update(
        {
            "__file__": str(public_path),
            "__package__": None,
            "__builtins__": __builtins__,
        }
    )

    # Python 3.13 dataclasses (and other runtime introspection) require the
    # defining module to exist in sys.modules while class decorators execute.
    # Executing into a detached dict works for simple scripts but fails for
    # @dataclass because cls.__module__ cannot be resolved.
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(public_path), "exec"), namespace)
        if configure is not None:
            configure(namespace)
    except Exception:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
        raise
    return namespace


def expose_implementation(
    target_globals: dict[str, Any],
    public_path: Path,
    implementation_path: Path,
    module_name: str,
    configure: ConfigureHook | None = None,
) -> None:
    """Re-export an implementation so existing import-based tests/callers keep working."""
    namespace = _load_namespace(
        public_path,
        implementation_path,
        module_name=f"{module_name}.__implementation__",
        configure=configure,
    )
    protected = {
        "__name__",
        "__file__",
        "__package__",
        "__spec__",
        "__loader__",
        "__cached__",
        "__builtins__",
    }
    for key, value in namespace.items():
        if key not in protected:
            target_globals[key] = value


def _prepare_argv(argv: list[str]) -> tuple[bool, bool, list[str]]:
    verbose = False
    help_mode = False
    passthrough = False
    cleaned = [argv[0]] if argv else []
    for arg in argv[1:]:
        if arg == "--":
            passthrough = True
            cleaned.append(arg)
            continue
        if not passthrough and arg == "--verbose":
            verbose = True
            continue
        if not passthrough and arg in {"-h", "--help"}:
            help_mode = True
        cleaned.append(arg)
    return verbose, help_mode, cleaned


def _result_exit_code(value: Any, stderr: io.StringIO | None = None) -> int:
    """Match `raise SystemExit(main())` semantics used by the legacy entrypoints."""
    if value is None:
        return 0
    if isinstance(value, int):
        return int(value)
    if stderr is not None:
        print(str(value), file=stderr)
    return 1


def _system_exit_code(exc: SystemExit, stderr: io.StringIO | None = None) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return int(code)
    if stderr is not None:
        print(str(code), file=stderr)
    return 1


def _diagnostics(stdout_text: str, stderr_text: str, limit: int = 30) -> list[str]:
    stdout_lines = [line.rstrip() for line in stdout_text.splitlines()]
    stderr_lines = [line.rstrip() for line in stderr_text.splitlines() if line.strip()]

    selected: list[str] = []
    selected.extend(stderr_lines)

    error_indexes = [
        index for index, line in enumerate(stdout_lines)
        if _ERROR_RE.search(line)
    ]
    for index in error_indexes:
        start = max(0, index - 2)
        end = min(len(stdout_lines), index + 3)
        selected.extend(line for line in stdout_lines[start:end] if line.strip())

    if not selected:
        selected.extend(line for line in stdout_lines[-12:] if line.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for line in selected:
        if line in seen:
            continue
        seen.add(line)
        deduped.append(line)
        if len(deduped) >= limit:
            break
    return deduped


def run_implementation(
    public_path: Path,
    implementation_path: Path,
    configure: ConfigureHook | None = None,
) -> int:
    """Run a rulebook CLI with terse-by-default output and --verbose passthrough."""
    original_argv = list(sys.argv)
    verbose, help_mode, cleaned_argv = _prepare_argv(original_argv)
    sys.argv[:] = cleaned_argv

    try:
        if verbose or help_mode:
            namespace = _load_namespace(
                public_path,
                implementation_path,
                module_name=f"_rulebook_cli_{public_path.stem.replace('-', '_')}",
                configure=configure,
            )
            main = namespace.get("main")
            if not callable(main):
                raise RuntimeError(f"{implementation_path.name} does not define main().")
            try:
                result = main()
                code = _result_exit_code(result)
            except SystemExit as exc:
                code = _system_exit_code(exc)
            if help_mode and code == 0:
                print("\nGlobal option: --verbose  Show the script's full legacy output.")
            return code

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            try:
                namespace = _load_namespace(
                    public_path,
                    implementation_path,
                    module_name=f"_rulebook_cli_{public_path.stem.replace('-', '_')}",
                    configure=configure,
                )
                main = namespace.get("main")
                if not callable(main):
                    raise RuntimeError(f"{implementation_path.name} does not define main().")
                try:
                    result = main()
                    code = _result_exit_code(result, stderr_buffer)
                except SystemExit as exc:
                    code = _system_exit_code(exc, stderr_buffer)
            except Exception:
                code = 1
                traceback.print_exc(file=stderr_buffer)

        if code == 0:
            print(f"{public_path.name}: PASS")
            return 0

        print(f"{public_path.name}: FAIL")
        for line in _diagnostics(stdout_buffer.getvalue(), stderr_buffer.getvalue()):
            print(line)
        return code or 1
    finally:
        sys.argv[:] = original_argv
