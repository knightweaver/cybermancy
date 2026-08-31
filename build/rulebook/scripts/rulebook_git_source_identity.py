from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class GitSourceIdentityError(RuntimeError):
    pass


def _git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").strip()


def _require_git_result(result: subprocess.CompletedProcess, action: str) -> None:
    if result.returncode != 0:
        detail = _decode(result.stderr or result.stdout)
        raise GitSourceIdentityError(f"{action}: {detail}")


def is_git_repository(root: Path) -> bool:
    result = _git_bytes(root, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and _decode(result.stdout).casefold() == "true"


def git_blob_bytes(root: Path, relative: str, ref: str = "HEAD") -> bytes:
    result = _git_bytes(root, "cat-file", "blob", f"{ref}:{relative}")
    _require_git_result(result, f"could not read Git blob {ref}:{relative}")
    return result.stdout or b""


def git_blob_sha256(root: Path, relative: str, ref: str = "HEAD") -> str:
    return hashlib.sha256(git_blob_bytes(root, relative, ref)).hexdigest()


def git_path_tracked(root: Path, relative: str) -> bool:
    result = _git_bytes(root, "ls-files", "--error-unmatch", "--", relative)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    _require_git_result(result, f"could not determine whether Git tracks {relative}")
    return False


def _git_differs(root: Path, *args: str) -> bool:
    result = _git_bytes(root, *args)
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    _require_git_result(result, "could not compare authored source with Git HEAD")
    return False


def git_path_drift(root: Path, relative: str) -> dict[str, Any]:
    index_differs = _git_differs(
        root,
        "diff",
        "--cached",
        "--quiet",
        "HEAD",
        "--",
        relative,
    )
    worktree_differs = _git_differs(
        root,
        "diff",
        "--quiet",
        "--",
        relative,
    )
    return {
        "path": relative,
        "indexDiffersFromHead": index_differs,
        "worktreeDiffersFromIndex": worktree_differs,
        "dirty": index_differs or worktree_differs,
    }


def _head_tree(root: Path) -> dict[str, dict[str, str]]:
    result = _git_bytes(root, "ls-tree", "-r", "-z", "--full-tree", "HEAD")
    _require_git_result(result, "could not enumerate Git HEAD tree")
    entries: dict[str, dict[str, str]] = {}
    for raw in (result.stdout or b"").split(b"\0"):
        if not raw:
            continue
        try:
            metadata, path_bytes = raw.split(b"\t", 1)
            mode_b, type_b, oid_b = metadata.split(b" ", 2)
        except ValueError as exc:
            raise GitSourceIdentityError("malformed Git ls-tree record") from exc
        relative = os.fsdecode(path_bytes)
        entries[relative] = {
            "mode": mode_b.decode("ascii"),
            "type": type_b.decode("ascii"),
            "oid": oid_b.decode("ascii"),
        }
    return entries


def materialize_head_blobs(
    root: Path,
    export_root: Path,
    candidate_relpaths: list[str],
) -> None:
    """Write exact HEAD blob bytes for strict-inventory candidates."""
    export_root.mkdir(parents=True, exist_ok=True)
    tree = _head_tree(root)
    requested: list[tuple[str, str, str]] = []
    for relative in candidate_relpaths:
        entry = tree.get(relative)
        if entry is None:
            raise GitSourceIdentityError(f"tracked path is absent from HEAD tree: {relative}")
        if entry["type"] != "blob":
            raise GitSourceIdentityError(
                f"unsupported Git object type for strict inventory: {relative}: {entry['type']}"
            )
        if entry["mode"] == "120000":
            raise GitSourceIdentityError(
                f"symbolic-link candidate is not supported by strict inventory materialization: {relative}"
            )
        requested.append((relative, entry["mode"], entry["oid"]))

    process = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        for relative, mode, oid in requested:
            process.stdin.write((oid + "\n").encode("ascii"))
            process.stdin.flush()
            header = process.stdout.readline().rstrip(b"\n")
            fields = header.split(b" ")
            if len(fields) != 3:
                raise GitSourceIdentityError(
                    f"unexpected git cat-file response for {relative}: {_decode(header)}"
                )
            actual_oid, obj_type, size_b = fields
            if actual_oid.decode("ascii") != oid or obj_type != b"blob":
                raise GitSourceIdentityError(
                    f"unexpected Git object for {relative}: {_decode(header)}"
                )
            try:
                size = int(size_b)
            except ValueError as exc:
                raise GitSourceIdentityError(
                    f"invalid Git blob size for {relative}: {_decode(size_b)}"
                ) from exc
            data = process.stdout.read(size)
            delimiter = process.stdout.read(1)
            if len(data) != size or delimiter != b"\n":
                raise GitSourceIdentityError(f"truncated Git blob stream for {relative}")
            path = export_root / Path(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            if mode == "100755":
                path.chmod(path.stat().st_mode | stat.S_IXUSR)
    finally:
        process.stdin.close()
        return_code = process.wait()
        stderr = (process.stderr.read() if process.stderr is not None else b"")
        if return_code != 0:
            raise GitSourceIdentityError(
                "git cat-file batch failed: " + _decode(stderr)
            )


def configure_strict_inventory_git_identity(namespace: dict[str, Any]) -> None:
    StrictInventoryError = namespace["StrictInventoryError"]

    def build_from_committed_head(
        root: Path,
        head: str,
        candidate_relpaths: list[str],
    ) -> dict[str, Any]:
        legacy = namespace["_legacy_namespace"]()
        excluded_dirs = set(legacy["DEFAULT_EXCLUDED_DIRS"])
        if any(
            namespace["_legacy_excluded"](relative, excluded_dirs)
            for relative in candidate_relpaths
        ):
            raise StrictInventoryError("internal error: excluded path reached strict candidate set")

        with tempfile.TemporaryDirectory(prefix="cybermancy-rulebook-inventory-") as td:
            export_root = Path(td) / root.name
            try:
                materialize_head_blobs(root, export_root, candidate_relpaths)
            except GitSourceIdentityError as exc:
                raise StrictInventoryError(str(exc)) from exc

            candidate_paths: list[Path] = []
            missing_export: list[str] = []
            for relative in candidate_relpaths:
                path = export_root / Path(relative)
                if not path.exists() and not path.is_symlink():
                    missing_export.append(relative)
                else:
                    candidate_paths.append(path)
            if missing_export:
                raise StrictInventoryError(
                    "tracked paths were not materialized from Git HEAD: "
                    + "; ".join(missing_export[:12])
                )

            legacy["walk_repo"] = lambda _root: iter(candidate_paths)
            inventory = legacy["build_inventory"](export_root)

        inventory.setdefault("repository", {})["root_name"] = root.name
        inventory["repository"]["git_commit"] = head
        return inventory

    namespace["_build_from_committed_index"] = build_from_committed_head


def configure_step4_authored_source_identity(namespace: dict[str, Any]) -> None:
    """Make Step 4 authored identity Git-canonical without weakening dirty checks."""
    original_preflight = namespace["repository_preflight"]
    pipeline_globals = original_preflight.__globals__
    filesystem_sha256 = pipeline_globals["sha256_file"]
    publication_views = pipeline_globals["publication_views"]
    pub_authored_by_path = pipeline_globals["pub_authored_by_path"]
    add_check = pipeline_globals["add_check"]

    def repository_preflight(repo_root, pub, asm, config, report):
        root = Path(repo_root)
        canonical_hashes: dict[Path, str] = {}
        dirty_records: list[dict[str, Any]] = []

        if is_git_repository(root):
            _pub_commit, authored_records, _family_records = publication_views(pub, config)
            for record in pub_authored_by_path(authored_records).values():
                relative = record.get("path")
                if not isinstance(relative, str) or not relative:
                    continue
                source = root / relative
                if not source.is_file() or not git_path_tracked(root, relative):
                    continue
                drift = git_path_drift(root, relative)
                if drift["dirty"]:
                    dirty_records.append(drift)
                    continue
                canonical_hashes[source.resolve()] = git_blob_sha256(root, relative, "HEAD")

        def canonical_sha256(path: Path) -> str:
            resolved = Path(path).resolve()
            if resolved in canonical_hashes:
                return canonical_hashes[resolved]
            return filesystem_sha256(path)

        pipeline_globals["sha256_file"] = canonical_sha256
        try:
            result = original_preflight(root, pub, asm, config, report)
        finally:
            pipeline_globals["sha256_file"] = filesystem_sha256

        if dirty_records:
            dirty_code = "AUTHORED_SOURCE_GIT_STATE"
            add_check(
                report,
                dirty_code,
                "ERROR",
                "Included authored canonical sources have staged or unstaged Git changes.",
                dirty_records,
            )
            aggregate = next(
                (
                    item
                    for item in reversed(report.get("checks", []))
                    if item.get("code") == "SOURCE_CORPUS_INTEGRITY"
                ),
                None,
            )
            if aggregate is None:
                add_check(
                    report,
                    "SOURCE_CORPUS_INTEGRITY",
                    "ERROR",
                    "Canonical source corpus has drifted from the frozen publication snapshot.",
                    {"blockingChecks": [dirty_code]},
                )
            else:
                details = dict(aggregate.get("details") or {})
                blocking = list(details.get("blockingChecks") or [])
                if dirty_code not in blocking:
                    blocking.append(dirty_code)
                details["blockingChecks"] = blocking
                aggregate.update(
                    status="ERROR",
                    message="Canonical source corpus has drifted from the frozen publication snapshot.",
                    details=details,
                )
            report["status"] = "FAIL"

        return result

    namespace["repository_preflight"] = repository_preflight
