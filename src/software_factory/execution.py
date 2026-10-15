"""Bounded output capture and process-group cleanup for synchronous workers."""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def execute(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str],
    capture_output: bool = True,
    check: bool = False,
    **identity: Any,
) -> subprocess.CompletedProcess[bytes]:
    # File-backed capture prevents a verbose model from exhausting controller RAM.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True, **identity
        )
        try:
            proc.wait(timeout=timeout)
        finally:
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif proc.poll() is None:
                proc.kill()
            proc.wait()
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(1_000_001), err.read(1_000_001)
        if len(stdout) > 1_000_000 or len(stderr) > 1_000_000:
            raise ValueError("Worker log limit exceeded; reduce verbosity")
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
