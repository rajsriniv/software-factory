"""POSIX principal separation and authenticated, revision-bound approval receipts.

Isolated mode requires an operator-provisioned root controller and unprivileged
workers. It deliberately refuses to pretend that ordinary same-user CLIs isolate
one another. Container/network policies remain the operator's responsibility.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
from pathlib import Path
from typing import Any


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def key(path: str) -> bytes:
    file = Path(path)
    info = file.stat()
    if file.is_symlink() or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("Authority key must be controller-owned with mode 0600")
    value = file.read_bytes()
    if len(value) < 32:
        raise ValueError("Authority key must contain at least 32 random bytes")
    return value


def sign(body: dict[str, Any], path: str) -> dict[str, Any]:
    return {
        "body": body,
        "signature": hmac.new(key(path), canonical(body), hashlib.sha256).hexdigest(),
    }


def verify(receipt: Any, path: str, expected: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, dict) or not isinstance(receipt.get("body"), dict):
        raise ValueError("Authenticated receipt required")  # noqa: TRY004 - external document validation contract
    body = receipt["body"]
    signature = receipt.get("signature")
    actual = hmac.new(key(path), canonical(body), hashlib.sha256).hexdigest()
    if not isinstance(signature, str) or not hmac.compare_digest(signature, actual):
        raise ValueError("Receipt signature invalid")
    if any(body.get(k) != v for k, v in expected.items()):
        raise ValueError("Receipt does not match this run, phase or approved input")
    return dict(body)


def preflight(manifest: dict[str, Any], database: Path, repository: Path) -> None:
    if manifest.get("assurance") != "isolated":
        return
    if os.name != "posix" or os.geteuid() != 0:
        raise ValueError(
            "Isolated mode requires a privileged POSIX controller with separate worker UIDs"
        )
    linux_status = Path("/proc/self/status")
    if linux_status.exists():
        effective = next(
            (
                line.split()[1]
                for line in linux_status.read_text().splitlines()
                if line.startswith("CapEff:")
            ),
            None,
        )
        if effective is not None and int(effective, 16) & 0xC0 != 0xC0:
            raise ValueError(
                "Host denies required SETUID/SETGID capabilities; isolated execution unavailable"
            )
    if database.resolve().is_relative_to(repository):
        raise ValueError("Controller database must be outside the worker repository")
    directory = database.parent.stat()
    if directory.st_uid != 0 or stat.S_IMODE(directory.st_mode) != 0o700:
        raise ValueError("Controller state directory must be root-owned mode 0700")
    runtime = manifest.get("runtime", {})
    for field in ("approval_key", "telemetry_key"):
        filename = runtime.get(field, "")
        if Path(filename).resolve().is_relative_to(repository):
            raise ValueError("Authority keys must be outside the worker checkout")
        key(filename)
    principals = runtime.get("principals", {})
    if not isinstance(principals, dict) or not principals:
        raise ValueError("Isolated mode needs explicit OS principal mappings")
    uids = []
    for actor, principal in principals.items():
        if (
            type(principal.get("uid")) is not int
            or principal["uid"] <= 0
            or type(principal.get("gid")) is not int
            or principal["gid"] <= 0
        ):
            raise ValueError(f"Unprivileged UID/GID required for {actor}")
        uids.append(principal["uid"])
    if len(uids) != len(set(uids)):
        raise ValueError("Distinct actors require distinct OS principals")
    if runtime.get("verification_actor") not in principals:
        raise ValueError("Trusted verification principal required")


def worker_options(manifest: dict[str, Any], actor: str) -> dict[str, Any]:
    if manifest.get("assurance") != "isolated":
        return {}
    principal = manifest["runtime"]["principals"].get(actor)
    if not principal:
        raise ValueError(f"No OS principal provisioned for {actor}")
    return {"user": principal["uid"], "group": principal["gid"], "extra_groups": []}


def immutable_tooling(manifest: dict[str, Any]) -> None:
    """Verify the operator's tool bundle before each execution in isolated mode."""
    if manifest.get("assurance") != "isolated":
        return
    bundle = manifest["runtime"].get("trusted_files", [])
    if not isinstance(bundle, list) or not bundle:
        raise ValueError("Isolated execution requires pinned trusted adapter/tool files")
    for reference in bundle:
        path = Path(reference["path"])
        secure_file(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]:
            raise ValueError("Trusted tool bundle changed")


def secure_file(path: Path) -> None:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("Trusted files must be absolute regular files")
    for entry in (path, *path.parents):
        info = entry.stat()
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022:
            raise ValueError(
                "Trusted file and parent directories must be root-owned and not worker-writable"
            )


def validate_command(manifest: dict[str, Any], command: list[str], repository: Path) -> None:
    """Require isolated entry points to be members of the pinned operator bundle."""
    if manifest.get("assurance") != "isolated":
        return
    import shutil

    allowed = {str(Path(item["path"]).resolve()) for item in manifest["runtime"]["trusted_files"]}
    executable = shutil.which(command[0])
    if not executable or str(Path(executable).resolve()) not in allowed:
        raise ValueError("Isolated executable is not in the pinned trusted bundle")
    if "-c" in command:
        raise ValueError("Use a pinned adapter file rather than inline executable code")
    if "-m" in command:
        module = command[command.index("-m") + 1]
        supported = {
            "software_factory.worker",
            "software_factory.test_receipt",
            "software_factory.acceptance_runner",
        }
        if module not in supported:
            raise ValueError("Use a pinned entry-point script for this module in isolated mode")
        path = Path(__file__).parent / (module.rsplit(".", 1)[1] + ".py")
        if str(path.resolve()) not in allowed:
            raise ValueError("Factory adapter module is not pinned")
    if (
        len(command) > 1
        and command[1].endswith(".py")
        and str((repository / command[1]).resolve()) not in allowed
    ):
        raise ValueError("Adapter script is not in the pinned trusted bundle")
