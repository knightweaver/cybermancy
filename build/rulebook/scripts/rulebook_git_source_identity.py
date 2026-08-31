from __future__ import annotations

import hashlib
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
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


def materialize_head_archive(root: Path, export_root: Path) -> None:
    """Materialize HEAD with exact Git blob bytes, bypassing worktree filters."""
    export_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="cybermancy-rulebook-git-archive-",
        suffix=".tar",
        dir=export_root.parent,
        delete=False,
    ) as handle:
        archive_path = Path(handle.name)

    try:
        result = _git_bytes(
            root,
            "archive",
            "--format=tar",
            f"--output={archive_path}",
            "HEAD",
        )
        _require_git_result(result, "could not materialize committed Git archive")

        with tarfile.open(archive_path, mode="r:") as archive:
            for member in archive.getmembers():
                member_path = PurePosixPath(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise GitSourceIdentityError(
                        f"unsafe path in committed Git archive: {member.name}"
                    )
            try:
                archive.extractall(export_root, filter="data")
            except TypeError:  # Python < 3.12 compatibility for local tooling.
                archive.extractall(export_root)
    finally:
        archive_path.unlink(missing_ok=True)


def configure_strict_inventory_git_identity(namespace: dict[str, Any]) -> None:
    namespace["_checkout_index"] = materialize_head_archive


def configure_step4_authored_source_identity(namespace: dict[str, Any]) -> None:
    """Make Step 4 authored identity Git-canonical without weakening dirty checks."""
    original_preflight = namespace["repository_preflight"]
    filesystem_sha256 = namespace["sha256_file"]
    publication_views = namespace["publication_views"]
    pub_authored_by_path = namespace["pub_authored_by_path"]
    add_check = namespace["add_check"]

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

        namespace["sha256_file"] = canonical_sha256
        try:
            result = original_preflight(root, pub, asm, config, report)
        finally:
            namespace["sha256_file"] = filesystem_sha256

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
