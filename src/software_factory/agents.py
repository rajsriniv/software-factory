from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import AgentSpec, Message


class AgentRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunResult:
    agent_id: str
    requested_model: str
    response: dict[str, object]
    stdout: Path
    stderr: Path


def command(spec: AgentSpec, prompt: str) -> list[str]:
    if spec.host == "claude":
        return ["claude", "--model", spec.model, "-p", prompt, "--output-format", "json"]
    if spec.host == "codex":
        return ["codex", "exec", "--model", spec.model, "--json", prompt]
    if spec.host == "copilot":
        return ["copilot", f"--model={spec.model}", "-p", prompt, "--output-format=json"]
    raise AgentRunError(f"Unsupported host: {spec.host}")


def run_agent(
    spec: AgentSpec,
    messages: list[Message],
    instruction: str,
    workdir: Path,
    run_directory: Path,
    timeout_seconds: int = 1800,
) -> RunResult:
    """Run one isolated role process.

    The adapter records the requested model. Runtime-resolved model verification
    belongs to the host telemetry gate and must not trust response text.
    """
    executable = {"claude": "claude", "codex": "codex", "copilot": "copilot"}.get(spec.host)
    if executable is None or shutil.which(executable) is None:
        raise AgentRunError(f"{spec.host} CLI is unavailable")
    if spec.model.lower() in {"auto", "inherit"}:
        raise AgentRunError("Explicit model selection is required")
    run_directory.mkdir(parents=True, exist_ok=False)
    response_path = run_directory / "response.json"
    packet = [
        {"message_id": message.message_id, "sender": message.sender, "kind": message.kind, "payload": message.payload}
        for message in messages
    ]
    prompt = (
        f"You are agent {spec.agent_id} with role {spec.role}. {instruction}\n"
        f"Read this structured inbox: {json.dumps(packet)}\n"
        f"Write one JSON response to {response_path}. Do not claim model identity as evidence."
    )
    stdout, stderr = run_directory / "stdout.log", run_directory / "stderr.log"
    with stdout.open("w") as out, stderr.open("w") as err:
        completed = subprocess.run(
            command(spec, prompt), cwd=workdir, stdout=out, stderr=err,
            timeout=timeout_seconds, check=False,
        )
    if completed.returncode != 0:
        raise AgentRunError(f"Agent failed with exit code {completed.returncode}; see {stderr}")
    if not response_path.is_file():
        raise AgentRunError("Agent did not create response.json")
    try:
        response = json.loads(response_path.read_text())
    except json.JSONDecodeError as exc:
        raise AgentRunError("Agent response is not valid JSON") from exc
    if not isinstance(response, dict):
        raise AgentRunError("Agent response must be a JSON object")
    return RunResult(spec.agent_id, spec.model, response, stdout, stderr)

