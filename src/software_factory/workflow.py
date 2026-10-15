"""Ordered, resumable execution. Run as a trusted controller, not inside a worker."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import authority
from . import evidence as proof
from .execution import execute
from .governance import decide
from .models import Decision, Option, Vote
from .spec_workflow import expand_tasks, phases, validate_spec_manifest

PHASES = (
    "refine",
    "intake-approval",
    "brainstorm",
    "architecture",
    "architecture-review",
    "architecture-approval",
    "plan",
    "test-design",
    "tasks",
    "e2e",
    "security",
    "verification",
    "release-approval",
    "deploy",
)
GATES = (
    "build",
    "unit",
    "integration",
    "dependencies",
    "iac",
    "provenance",
    "rollback",
    "network-security",
    "observability",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Workflow:
    """One manifest, one repository, one serial event stream per database.

    Manifest commands are trusted operator configuration. No shell interpolation.
    Failed operations never advance; command logs remain in the event stream.
    """

    def __init__(self, database: Path, manifest: Path, repository: Path) -> None:
        self.database = database.resolve()
        self.repository = repository.resolve()
        self.manifest = json.loads(manifest.read_text())
        try:
            self.validate(self.manifest)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Malformed workflow manifest") from exc
        self.fingerprint = digest(encode(self.manifest).encode())
        database.parent.mkdir(parents=True, exist_ok=True)
        authority.preflight(self.manifest, database, self.repository)
        self.db = sqlite3.connect(database, timeout=1)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'immutable'); END"
        )
        self.db.execute(
            "CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'immutable'); END"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS inflight (id INTEGER PRIMARY KEY CHECK(id=1), phase TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS run_identity (id INTEGER PRIMARY KEY CHECK(id=1), nonce TEXT NOT NULL)"
        )
        self.db.execute("INSERT OR IGNORE INTO run_identity VALUES (1, ?)", (uuid4().hex,))
        self.run_id = str(
            self.db.execute("SELECT nonce FROM run_identity WHERE id=1").fetchone()[0]
        )
        self.db.commit()

    @staticmethod
    def validate(m: dict[str, Any]) -> None:
        if m.get("schema_version", 1) not in {1, 2}:
            raise ValueError("Unsupported workflow schema version")
        if m.get("assurance") == "isolated" and m.get("schema_version") != 2:
            raise ValueError("Isolated execution requires schema_version 2")
        if m.get("schema_version") == 2:
            validate_spec_manifest(m)
            if set(m.get("gate_reports", {})) != set(GATES):
                raise ValueError("Each verification gate requires an actual report")
            council = proof.strings(m.get("council"), "council")
            if len(council) < 3 or len(council) % 2 == 0:
                raise ValueError("Council requires an odd number of at least three members")
            if not m.get("tasks"):
                placeholders = [
                    {
                        "id": f"template-{i}",
                        "template": name,
                        "requirements": m["requirements"],
                        "depends_on": [],
                        "test_files": [f"tests/template-{i}.py"],
                        "write_files": [f"src/template-{i}.py"],
                        "acceptance": ["Template validation only"],
                    }
                    for i, name in enumerate(m["task_templates"])
                ]
                m = {**m, "tasks": expand_tasks(m, placeholders)}
        required = {p for p in phases(m, PHASES) if p != "tasks" and not p.endswith("approval")}
        if (
            not isinstance(m.get("requirements"), list)
            or not m["requirements"]
            or any(not isinstance(r, str) or not r.strip() for r in m["requirements"])
            or len(set(m["requirements"])) != len(m["requirements"])
        ):
            raise ValueError("Unique nonempty requirement IDs required")
        if set(m.get("steps", {})) != required:
            raise ValueError(f"steps must contain exactly {sorted(required)}")
        if set(m.get("gate_commands", {})) != set(GATES):
            raise ValueError("Executable commands required for every mandatory verification gate")
        for command in m["gate_commands"].values():
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(v, str) or not v for v in command)
            ):
                raise ValueError("Gate commands must be argument arrays")
        tasks = m.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            raise ValueError("At least one bounded task required")
        ids: set[str] = set()
        covered: set[str] = set()
        for task in tasks:
            if (
                not isinstance(task.get("id"), str)
                or not task["id"]
                or "/" in task["id"]
                or task["id"] in ids
            ):
                raise ValueError("Unique task IDs required")
            if not set(task.get("depends_on", [])) <= ids:
                raise ValueError("Tasks must follow dependency order")
            ids.add(task["id"])
            criteria = task.get("requirements", [])
            if not criteria or not set(criteria) <= set(m["requirements"]):
                raise ValueError("Task requirement coverage missing or invalid")
            covered.update(criteria)
            if set(task.get("steps", {})) != {"test", "red", "implement", "green", "review"}:
                raise ValueError("Each task needs test, red, implement, green, review")
            if not task.get("test_files") or any(
                not isinstance(p, str) for p in task["test_files"]
            ):
                raise ValueError("Every task requires explicit protected test_files")
            steps = task["steps"]
            if steps["red"]["command"] != steps["green"]["command"]:
                raise ValueError("Red and green must execute the same test command")
            if steps["review"]["actor"] in {steps["implement"]["actor"], steps["test"]["actor"]}:
                raise ValueError("Task reviewer must be independent")
        if covered != set(m["requirements"]):
            raise ValueError("Every requirement must map to a task")
        steps = m["steps"]
        if steps["architecture"]["actor"] == steps["architecture-review"]["actor"]:
            raise ValueError("Architecture reviewer must be independent")
        if m.get("schema_version") == 2:
            if steps["security-architecture"]["actor"] == steps["architecture"]["actor"] or steps[
                "architecture-challenge"
            ]["actor"] in {steps["architecture"]["actor"], steps["security-architecture"]["actor"]}:
                raise ValueError("Architect, security architect and challenger must be independent")
            if (
                "deployment-verification" in steps
                and steps["deployment-verification"]["actor"] == steps["deploy"]["actor"]
            ):
                raise ValueError("Deployment must be independently verified")
        if m.get("schema_version") == 2:
            if steps["e2e"].get("execution") != "tool" or any(
                t["steps"][p].get("execution") != "tool" for t in tasks for p in ("red", "green")
            ):
                raise ValueError("TDD and E2E results must come from deterministic tool steps")
            for phase, step in steps.items():
                if step.get("execution") == "agent" and step.get("tier") != "high":
                    raise ValueError(f"{phase} requires a high-tier agent")
            for task in tasks:
                for phase, step in task["steps"].items():
                    if (
                        step.get("execution") == "agent"
                        and phase != "implement"
                        and step.get("tier") != "high"
                    ):
                        raise ValueError("Test design and review require high-tier agents")
        authors = {t["steps"][k]["actor"] for t in tasks for k in ("test", "implement")}
        if steps["verification"]["actor"] in authors | {steps["e2e"]["actor"]}:
            raise ValueError("Final verifier must be independent of implementation and SDET")
        outputs: set[str] = set()
        for spec in list(steps.values()) + [s for t in tasks for s in t["steps"].values()]:
            if m.get("schema_version") == 2:
                if spec.get("execution") not in {"agent", "tool"}:
                    raise ValueError("Each step must declare agent or tool execution")
                if spec["execution"] == "agent" and (
                    not isinstance(spec.get("model"), str)
                    or spec["model"].lower() in {"", "auto", "inherit"}
                    or spec.get("tier") not in {"high", "low"}
                ):
                    raise ValueError("Agent steps need explicit model and tier")
            if not isinstance(spec.get("actor"), str) or not spec["actor"].strip():
                raise ValueError("Explicit actor required")
            cmd = spec.get("command")
            if (
                not isinstance(cmd, list)
                or not cmd
                or any(not isinstance(v, str) or not v for v in cmd)
            ):
                raise ValueError("Explicit command argument array required")
            if not isinstance(spec.get("output"), str) or not spec["output"]:
                raise ValueError("JSON evidence output path required")
            if spec["output"] in outputs:
                raise ValueError("Evidence output paths must be unique")
            outputs.add(spec["output"])
            if (
                not isinstance(spec.get("timeout", 1800), int)
                or not 1 <= spec.get("timeout", 1800) <= 7200
            ):
                raise ValueError("Timeout must be an integer from 1 to 7200 seconds")

    def doctor(self) -> dict[str, Any]:
        self.status()
        commands = [s["command"] for s in self.manifest["steps"].values()]
        commands += [
            s["command"]
            for template in self.manifest.get("task_templates", {}).values()
            for s in template.values()
        ]
        commands += list(self.manifest["gate_commands"].values())
        errors = []
        for command in commands:
            executable = command[0]
            if not shutil.which(executable):
                errors.append(f"Executable unavailable: {executable}")
            if (
                len(command) > 1
                and command[1].endswith(".py")
                and not (self.repository / command[1]).is_file()
            ):
                errors.append(f"Project adapter missing: {command[1]}")
            if "software_factory.worker" in command and "--host" in command:
                host = command[command.index("--host") + 1]
                if not shutil.which(host):
                    errors.append(f"Native client unavailable: {host}")
        return {
            "ready": not errors,
            "errors": sorted(set(errors)),
            "assurance": self.manifest.get("assurance", "legacy-local"),
            "live_client_authentication_verified": False,
            "note": "Checks local configuration and executables; it does not establish provider authentication or cloud permissions.",
        }

    def planned_tasks(self) -> list[dict[str, Any]]:
        if self.manifest.get("schema_version") != 2:
            return list(self.manifest["tasks"])
        plans = [e for e in self.events() if e.get("success") and e["phase"] == "plan"]
        return expand_tasks(self.manifest, plans[-1]["evidence"]["tasks"]) if plans else []

    def schedule(self) -> list[tuple[str, dict[str, Any] | None]]:
        result = []
        for phase in phases(self.manifest, PHASES):
            if phase == "tasks":
                for task in self.planned_tasks():
                    for step in ("test", "red", "implement", "green", "review"):
                        result.append((f"task/{task['id']}/{step}", task["steps"][step]))
            else:
                result.append((phase, self.manifest["steps"].get(phase)))
        return result

    def audit_events(self) -> list[dict[str, Any]]:
        return [
            json.loads(row[0]) for row in self.db.execute("SELECT body FROM events ORDER BY id")
        ]

    def events(self) -> list[dict[str, Any]]:
        active: list[dict[str, Any]] = []
        for event in self.audit_events():
            if event.get("kind") == "repair":
                index = next(i for i, e in enumerate(active) if e["phase"] == event["rewind_to"])
                active = active[:index] + [event]
            else:
                active.append(event)
        return active

    def repair(self, confirmation: str) -> dict[str, Any]:
        """Human-requested bounded repair, retaining red evidence and invalidating downstream work."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.status()
            phase = state["next"]
            if not phase.startswith("task/") or not phase.endswith(("/green", "/review")):
                raise ValueError("Repair is allowed only after a failed task green/review step")
            if not self.events() or self.events()[-1].get("success") is not False:
                raise ValueError("Repair requires a recorded failed attempt")
            target = phase.rsplit("/", 1)[0] + "/implement"
            expected = f"REPAIR {self.run_id} {target} {self.snapshot()}"
            if confirmation != expected:
                raise ValueError(f"Human repair confirmation required: {expected}")
            if sum(e.get("rewind_to") == target for e in self.audit_events()) >= self.manifest.get(
                "max_attempts", 3
            ):
                raise ValueError("Repair budget exhausted; human replanning required")
            record = {
                "kind": "repair",
                "phase": "repair",
                "rewind_to": target,
                "snapshot": self.snapshot(),
                "manifest": self.fingerprint,
                "repository": str(self.repository),
                "success": False,
                "run_id": self.run_id,
                "confirmation": confirmation,
                "channel": "factory-handoffs",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.db.execute("INSERT INTO events(body) VALUES (?)", (encode(record),))
            self.db.commit()
            return record
        except BaseException:
            self.db.rollback()
            raise

    def snapshot(self, exclude: tuple[str, ...] = ()) -> str:
        # Includes tracked and untracked source; excludes only Git-ignored files.
        result = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=self.repository,
            capture_output=True,
            check=True,
        )
        entries = []
        for name in sorted(set(result.stdout.decode().split("\0")) - {""}):
            if name in exclude:
                continue
            path = self.repository / name
            if path.is_dir():
                raise ValueError(
                    "Submodule/directory inputs require an explicit materialized checkout"
                )
            if path.is_symlink():
                raise ValueError("Symlink inputs require an explicit isolated checkout")
            entries.append((name, digest(path.read_bytes()) if path.is_file() else "missing"))
        return digest(encode(entries).encode())

    def status(self) -> dict[str, Any]:
        if digest(encode(self.manifest).encode()) != self.fingerprint:
            raise ValueError("In-memory manifest changed; start a new workflow")
        if self.db.execute("SELECT 1 FROM inflight").fetchone():
            raise ValueError(
                "Interrupted or running command: inspect side effects and start a new workflow"
            )
        if self.manifest.get("schema_version") == 2:
            proof.specification(
                self.manifest["specification"], self.manifest["requirements"], self.repository
            )
            for reference in self.manifest.get("regression_tests", []):
                proof.artifact(reference, self.repository)
            if self.manifest.get("delivery") == "deploy":
                proof.artifact(self.manifest["deployment"]["plan"], self.repository)
        events = self.events()
        if any(
            e["manifest"] != self.fingerprint or e["repository"] != str(self.repository)
            for e in events
        ):
            raise ValueError(
                "Manifest or repository changed; start a new workflow and obtain fresh approvals"
            )
        if any(e.get("tainted") for e in events):
            raise ValueError(
                "Read-only or protected-test mutation invalidated this workflow; restart"
            )
        if events and events[-1]["snapshot"] != self.snapshot():
            raise ValueError("Repository changed outside controller; current verification is stale")
        completed = [e for e in events if e["success"]]
        for index, event in enumerate(completed):
            if event["phase"] != self.schedule()[index][0]:
                raise ValueError("Event sequence does not match the workflow")
            proof.validate_references(event.get("evidence", {}), self.repository)
            proof.validate_references(event.get("gate_runs", {}), self.repository)
            if event["phase"] == "verification":
                artifact_file = Path(event["evidence"]["artifact_path"])
                if (
                    not artifact_file.is_file()
                    or digest(artifact_file.read_bytes()) != event["evidence"]["artifact_sha256"]
                ):
                    raise ValueError("Verified artifact changed; verification is stale")
            if event.get("output"):
                path = Path(event["output"])
                if not path.is_file() or digest(path.read_bytes()) != event["evidence_sha256"]:
                    raise ValueError("Previously accepted evidence changed; start a new workflow")
        schedule = self.schedule()
        return {
            "next": schedule[len(completed)][0] if len(completed) < len(schedule) else "complete",
            "completed": len(completed),
            "manifest": self.fingerprint,
            "run_id": self.run_id,
            "assurance": self.manifest.get("assurance", "legacy-local"),
            "delivery": self.manifest.get("delivery", "legacy"),
            "usage": self.usage(),
        }

    def usage(self) -> dict[str, Any]:
        receipts = [e["runtime"] for e in self.audit_events() if "runtime" in e]
        return {
            "verified_receipts": len(receipts),
            "tokens": sum(r["input_tokens"] + r["output_tokens"] for r in receipts),
            "cost_microunits": sum(r["cost_microunits"] for r in receipts),
            "unverified_steps": sum(
                e.get("execution") == "agent" and "runtime" not in e for e in self.audit_events()
            ),
        }

    def approval_body(self, phase: str, snapshot: str) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": phase,
            "manifest": self.fingerprint,
            "snapshot": snapshot,
            "history": digest(encode(self.audit_events()).encode()),
            "deployment": self.manifest.get("deployment"),
            "principal_uid": os.geteuid(),
        }

    def sign_approval(self) -> dict[str, Any]:
        # CLI exposes signing only after interactive confirmation; workers cannot access the key.
        return authority.sign(
            self.approval_body(self.status()["next"], self.snapshot()),
            self.manifest["runtime"]["approval_key"],
        )

    def advance(self, approval: Any = None) -> dict[str, Any]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            authority.preflight(self.manifest, self.database, self.repository)
            authority.immutable_tooling(self.manifest)
            status = self.status()
            if status["next"] == "complete":
                raise ValueError("Workflow already complete")
            name, spec = self.schedule()[status["completed"]]
            budget = self.manifest.get("budget", {})
            usage = self.usage()
            if any(
                usage[k] >= limit
                for k, limit in budget.items()
                if k in {"tokens", "cost_microunits"}
            ):
                raise ValueError("Runtime budget exhausted; human budget revision required")
            attempts = [e for e in self.events() if e["phase"] == name]
            if len(attempts) >= self.manifest.get("max_attempts", 3):
                raise ValueError("Attempt budget exhausted; review and replan")
            before = self.snapshot()
            protected_source = None
            if name.startswith("task/") and name.endswith("/test"):
                test_task = next(t for t in self.planned_tasks() if name == f"task/{t['id']}/test")
                protected_source = self.snapshot(tuple(test_task["test_files"]))
            write_scope = None
            if (
                self.manifest.get("schema_version") == 2
                and name.startswith("task/")
                and name.endswith("/implement")
            ):
                scoped_task = next(
                    t for t in self.planned_tasks() if name == f"task/{t['id']}/implement"
                )
                write_scope = self.snapshot(tuple(scoped_task["write_files"]))
            previous = self.events()
            if previous and previous[-1]["snapshot"] != before:
                raise ValueError(
                    "Repository changed outside controller; start a new workflow for fresh evidence"
                )
            event: dict[str, Any] = {
                "phase": name,
                "manifest": self.fingerprint,
                "repository": str(self.repository),
                "before": before,
                "channel": "factory-handoffs",
                "success": False,
                "run_id": self.run_id,
                "attempt_id": uuid4().hex,
                "created_at": datetime.now(UTC).isoformat(),
            }
            if approval is not None and spec is not None:
                raise ValueError("Approval is only accepted at a human gate")
            if spec is None:
                expected = f"APPROVE {name} {self.fingerprint} {before}"
                if self.manifest.get("assurance") == "isolated":
                    authority.verify(
                        approval,
                        self.manifest["runtime"]["approval_key"],
                        self.approval_body(name, before),
                    )
                elif approval != expected:
                    raise ValueError(f"Human confirmation required: {expected}")
                event.update(success=True, approval=approval)
            else:
                output = (self.repository / spec["output"]).resolve()
                if not output.is_relative_to(self.repository):
                    raise ValueError("Evidence output must be inside the repository")
                if output.exists():
                    historical = [e for e in self.audit_events() if e["phase"] == name]
                    accepted = any(
                        e.get("success") and e.get("output") == str(output) for e in self.events()
                    )
                    if not historical or accepted:
                        raise ValueError("Evidence output must be a fresh path")
                    output.rename(output.with_name(output.name + ".attempt-" + uuid4().hex))
                    junit_report = output.with_suffix(".xml")
                    if junit_report.exists():
                        junit_report.rename(
                            junit_report.with_name(junit_report.name + ".attempt-" + uuid4().hex)
                        )
                ignored = subprocess.run(
                    ["git", "check-ignore", "--quiet", "--", spec["output"]],
                    cwd=self.repository,
                    check=False,
                )
                if ignored.returncode != 0:
                    raise ValueError(
                        "Evidence paths must be Git-ignored to keep source snapshots stable"
                    )
                environment = {
                    key: os.environ[key]
                    for key in ("PATH", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT")
                    if key in os.environ
                }
                environment["FACTORY_RUN_ID"] = self.run_id
                environment["FACTORY_ATTEMPT_ID"] = event["attempt_id"]
                environment["FACTORY_INPUT_SHA256"] = before
                environment["FACTORY_MANIFEST_SHA256"] = self.fingerprint
                environment["FACTORY_EXPECTED_MODEL"] = spec.get("model", "")
                environment["FACTORY_PHASE"] = name
                environment["FACTORY_REQUIREMENTS"] = encode(self.manifest["requirements"])
                if self.manifest.get("schema_version") == 2:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    context_path = output.parent / ("context-" + uuid4().hex + ".json")
                    context_path.write_text(
                        encode(
                            {
                                "phase": name,
                                "specification": self.manifest["specification"],
                                "requirements": self.manifest["requirements"],
                                "task_templates": self.manifest["task_templates"]
                                if name == "plan"
                                else {},
                                "task": next(
                                    (
                                        t
                                        for t in self.planned_tasks()
                                        if name.startswith(f"task/{t['id']}/")
                                    ),
                                    None,
                                ),
                                "prior_outputs": [
                                    {
                                        "phase": e["phase"],
                                        "output": e.get("output"),
                                        "sha256": e.get("evidence_sha256"),
                                    }
                                    for e in previous
                                    if e.get("success")
                                ],
                                "deployment": self.manifest.get("deployment"),
                            }
                        )
                    )
                    environment["FACTORY_CONTEXT"] = str(context_path)
                    if (
                        self.manifest.get("assurance") == "local"
                        and spec.get("execution") == "agent"
                    ):
                        # Native clients need their current user's login/config; local mode is explicitly nonisolated.
                        environment["HOME"] = str(Path.home())
                if name.startswith("task/"):
                    environment["FACTORY_TASK"] = encode(
                        next(t for t in self.planned_tasks() if name.startswith(f"task/{t['id']}/"))
                    )
                environment["FACTORY_EVIDENCE_OUTPUT"] = str(output)
                if name == "deploy":
                    verified = next(
                        e for e in previous if e["phase"] == "verification" and e["success"]
                    )
                    artifact_path = Path(verified["evidence"]["artifact_path"])
                    if (
                        digest(artifact_path.read_bytes())
                        != verified["evidence"]["artifact_sha256"]
                    ):
                        raise ValueError("Approved deployment artifact changed")
                    if self.manifest.get("assurance") == "isolated":
                        authority.secure_file(artifact_path)
                    environment["FACTORY_DEPLOYMENT_TARGET"] = encode(
                        self.manifest.get("deployment", {})
                    )
                    environment["FACTORY_APPROVED_ARTIFACT_PATH"] = str(artifact_path)
                    environment["FACTORY_APPROVED_ARTIFACT_SHA256"] = verified["evidence"][
                        "artifact_sha256"
                    ]
                self.db.execute("INSERT INTO inflight VALUES (1, ?)", (name,))
                self.db.commit()
                self.db.execute("BEGIN IMMEDIATE")
                try:
                    if name == "verification":
                        event["gate_runs"] = {}
                        for gate, command in self.manifest["gate_commands"].items():
                            gate_env = dict(environment)
                            gate_report = None
                            if self.manifest.get("schema_version") == 2:
                                gate_report = (
                                    self.repository / self.manifest["gate_reports"][gate]
                                ).resolve()
                                if not gate_report.is_relative_to(self.repository):
                                    raise ValueError(
                                        "Verification report must be inside the repository"
                                    )
                                if gate_report.exists():
                                    if not attempts:
                                        raise ValueError(
                                            "Verification gate needs a fresh local report path"
                                        )
                                    gate_report.rename(
                                        gate_report.with_name(
                                            gate_report.name + ".attempt-" + uuid4().hex
                                        )
                                    )
                                gate_report.parent.mkdir(parents=True, exist_ok=True)
                                gate_env["FACTORY_GATE_REPORT"] = str(gate_report)
                            authority.validate_command(self.manifest, command, self.repository)
                            check = execute(
                                command,
                                cwd=self.repository,
                                capture_output=True,
                                timeout=spec.get("timeout", 1800),
                                check=False,
                                env=gate_env,
                                **authority.worker_options(
                                    self.manifest,
                                    self.manifest.get("runtime", {}).get(
                                        "verification_actor", spec["actor"]
                                    ),
                                ),
                            )
                            event["gate_runs"][gate] = {
                                "exit_code": check.returncode,
                                "stdout": check.stdout.decode(errors="replace"),
                                "stderr": check.stderr.decode(errors="replace"),
                            }
                            if check.returncode != 0:
                                raise ValueError(f"Executed verification gate failed: {gate}")
                            if gate_report is not None:
                                gate_data = json.loads(gate_report.read_text())
                                checks = (
                                    gate_data.get("checks") if isinstance(gate_data, dict) else None
                                )
                                if (
                                    not isinstance(checks, list)
                                    or not checks
                                    or any(
                                        not isinstance(c, dict)
                                        or not c.get("id")
                                        or c.get("passed") is not True
                                        for c in checks
                                    )
                                ):
                                    raise ValueError(
                                        f"Gate {gate} has no successful executed checks"
                                    )
                                if gate_data.get("input_sha256") != before:
                                    raise ValueError("Gate report does not bind current inputs")
                                event["gate_runs"][gate]["report"] = {
                                    "path": str(gate_report),
                                    "sha256": digest(gate_report.read_bytes()),
                                }
                    authority.validate_command(self.manifest, spec["command"], self.repository)
                    started = time.monotonic()
                    run = execute(
                        spec["command"],
                        cwd=self.repository,
                        capture_output=True,
                        timeout=spec.get("timeout", 1800),
                        check=False,
                        env=environment,
                        **authority.worker_options(self.manifest, spec["actor"]),
                    )
                    event.update(
                        actor=spec["actor"],
                        execution=spec.get("execution", "legacy"),
                        elapsed_seconds=time.monotonic() - started,
                        command=spec["command"],
                        exit_code=run.returncode,
                        stdout=run.stdout.decode(errors="replace"),
                        stderr=run.stderr.decode(errors="replace"),
                    )
                    evidence = json.loads(output.read_text()) if output.is_file() else {}
                    self.check_evidence(name, evidence, run.returncode)
                    if self.manifest.get("assurance") == "isolated" and spec.get("model"):
                        body = authority.verify(
                            evidence.get("runtime_receipt"),
                            self.manifest["runtime"]["telemetry_key"],
                            {
                                "run_id": self.run_id,
                                "phase": name,
                                "input_sha256": before,
                                "actor": spec["actor"],
                                "resolved_model": spec["model"],
                                "attempt_id": event["attempt_id"],
                            },
                        )
                        for metric in ("input_tokens", "output_tokens", "cost_microunits"):
                            if type(body.get(metric)) is not int or body[metric] < 0:
                                raise ValueError(
                                    "Signed nonnegative runtime usage metrics required"
                                )
                        event["runtime"] = body
                    if (
                        name.endswith("review") or name in {"e2e", "security", "verification"}
                    ) and evidence.get("input_sha256") != before:
                        raise ValueError("Review or test evidence must bind FACTORY_INPUT_SHA256")
                    event.update(
                        success=True,
                        output=str(output),
                        evidence=evidence,
                        evidence_sha256=digest(output.read_bytes()),
                    )
                except (
                    ValueError,
                    OSError,
                    TypeError,
                    KeyError,
                    AttributeError,
                    subprocess.TimeoutExpired,
                ) as exc:
                    event["error"] = str(exc)
                    if (
                        name == "deploy"
                        or isinstance(exc, subprocess.TimeoutExpired)
                        or (
                            self.manifest.get("assurance") == "isolated"
                            and spec.get("model")
                            and "runtime" not in event
                        )
                    ):
                        event["tainted"] = True
            if name.startswith("task/"):
                task = next(t for t in self.planned_tasks() if name.startswith(f"task/{t['id']}/"))
                hashes = {}
                for filename in task["test_files"]:
                    path = (self.repository / filename).resolve()
                    if not path.is_relative_to(self.repository) or not path.is_file():
                        event.update(success=False, error="Protected test file missing")
                        break
                    hashes[filename] = digest(path.read_bytes())
                event["tests"] = hashes
                if not name.endswith(("/test", "/red")):
                    red = next(
                        e
                        for e in reversed(previous)
                        if e["phase"] == name.rsplit("/", 1)[0] + "/red" and e["success"]
                    )
                    if hashes != red["tests"]:
                        event.update(
                            success=False,
                            tainted=True,
                            error="Implementation changed protected tests",
                        )
            if protected_source is not None and protected_source != self.snapshot(
                tuple(test_task["test_files"])
            ):
                event.update(
                    success=False,
                    tainted=True,
                    error="Test-writing step changed implementation source",
                )
            if self.manifest.get("schema_version") == 2:
                try:
                    proof.specification(
                        self.manifest["specification"],
                        self.manifest["requirements"],
                        self.repository,
                    )
                except ValueError:
                    event.update(
                        success=False, tainted=True, error="Approved specification changed"
                    )
            for reference in self.manifest.get("regression_tests", []):
                try:
                    proof.artifact(reference, self.repository)
                except ValueError:
                    event.update(
                        success=False, tainted=True, error="Baseline regression tests changed"
                    )
            for prior in previous:
                if prior.get("success") and prior["phase"].endswith("/red"):
                    for filename, expected in prior.get("tests", {}).items():
                        path = self.repository / filename
                        if not path.is_file() or digest(path.read_bytes()) != expected:
                            event.update(
                                success=False,
                                tainted=True,
                                error="Previously accepted regression tests changed",
                            )
            if (
                self.manifest.get("schema_version") == 2
                and name.startswith("task/")
                and name.endswith("/implement")
            ):
                allowed = tuple(task["write_files"])
                if write_scope != self.snapshot(allowed):
                    event.update(
                        success=False,
                        tainted=True,
                        error="Implementation exceeded approved write scope",
                    )
            event["snapshot"] = self.snapshot()
            # Approval, review and execution-only phases may not mutate source.
            readonly = (
                spec is None
                or (
                    self.manifest.get("schema_version") == 2
                    and not name.endswith(("/test", "/implement"))
                )
                or name in {"e2e", "security", "verification", "deploy", "architecture-review"}
                or name.endswith(("/red", "/green", "/review"))
            )
            if readonly and before != event["snapshot"]:
                event.update(
                    success=False, tainted=True, error="Read-only phase changed repository inputs"
                )
            self.db.execute("INSERT INTO events(body) VALUES (?)", (encode(event),))
            self.db.execute("DELETE FROM inflight")
            self.db.commit()
            return event
        except BaseException:
            self.db.rollback()
            raise

    def check_spec_evidence(self, name: str, evidence: dict[str, Any]) -> None:
        if name == "company-context" and evidence.get("knowledge_gap") is not True:
            refs = evidence.get("sources")
            if not isinstance(refs, list) or not refs:
                raise ValueError(
                    "Company context requires source references or an explicit knowledge gap"
                )
            for reference in refs:
                proof.artifact(reference, self.repository)
        if name in {
            "refine",
            "architecture",
            "security-architecture",
            "architecture-challenge",
            "test-design",
            "discovery",
            "ux-design",
            "ui-review",
            "knowledge-proposal",
        }:
            proof.artifact(evidence.get("document"), self.repository)
        if (
            name in {"security-architecture", "architecture-challenge", "ui-review"}
            and evidence.get("blocking_findings") != []
        ):
            raise ValueError("Unresolved specialist findings block the handoff")
        if name == "test-design":
            mapping = evidence.get("test_map")
            criteria = proof.acceptance_ids(self.manifest["specification"], self.repository)
            if not isinstance(mapping, dict) or set(mapping) != set(criteria):
                raise ValueError("SDET must map every acceptance criterion to planned test IDs")
            for ids in mapping.values():
                proof.strings(ids, "planned test IDs")
        if name == "architecture-review":
            raw = evidence.get("decision")
            if not isinstance(raw, dict):
                raise ValueError(
                    "Architecture handoff requires an independently assessed council decision"
                )
            members = self.manifest.get("council", [])
            if raw.get("eligible_voters") != members:
                raise ValueError("Council members must match the approved manifest")
            if self.manifest.get("assurance") == "isolated":
                receipts = evidence.get("ballot_receipts", {})
                for vote in raw.get("votes", []):
                    authority.verify(
                        receipts.get(vote["agent_id"]),
                        self.manifest["runtime"]["telemetry_key"],
                        {
                            "run_id": self.run_id,
                            "actor": vote["agent_id"],
                            "vote": vote,
                            "input_sha256": self.snapshot(),
                            "phase": "architecture-review",
                        },
                    )
            decision = Decision(
                "architecture",
                "Approve architecture",
                tuple(members),
                tuple(Option(**o) for o in raw.get("options", [])),
                [Vote(**v) for v in raw.get("votes", [])],
            )
            result = decide(decision, True)
            if result.status != "decided" or result.outcome != raw.get("selected"):
                raise ValueError("Council has not approved the selected architecture")
            proof.artifact(evidence.get("document"), self.repository)
        if name.endswith(("/red", "/green")):
            report = proof.artifact(evidence.get("test_report"), self.repository)
            passing, failing, errors = proof.junit(report)
            if errors:
                raise ValueError("TDD cannot use test execution errors as evidence")
            claimed = evidence.get(
                "failing_tests" if name.endswith("/red") else "passing_tests", []
            )
            actual = failing if name.endswith("/red") else passing
            if set(claimed) != actual or (name.endswith("/green") and failing):
                raise ValueError("TDD claims do not match the actual test report")
            if name.endswith("/red"):
                design = next(
                    e["evidence"]["test_map"]
                    for e in self.events()
                    if e["phase"] == "test-design" and e["success"]
                )
                task = next(t for t in self.planned_tasks() if name.startswith(f"task/{t['id']}/"))
                expected = {
                    test
                    for criterion, tests in design.items()
                    if criterion.split("::AC", 1)[0] in task["requirements"]
                    for test in tests
                }
                if not failing or not failing <= expected:
                    raise ValueError(
                        "Red must fail planned acceptance tests, not unrelated baseline tests"
                    )
        if name in {"e2e", "verification"}:
            design = next(
                e["evidence"]["test_map"]
                for e in self.events()
                if e["phase"] == "test-design" and e["success"]
            )
            for criterion, tests in design.items():
                references = evidence.get("coverage", {}).get(criterion, [])
                if not isinstance(references, list) or any(
                    not isinstance(r, dict) for r in references
                ):
                    raise ValueError("Coverage must reference planned acceptance tests")
                observed = {test for r in references for test in r.get("test_ids", [])}
                if not set(tests) <= observed:
                    raise ValueError("Coverage omits planned acceptance tests")
        if name == "deployment-verification":
            previous = next(
                e for e in self.events() if e["phase"] == "verification" and e["success"]
            )
            if evidence.get("observed_artifact_sha256") != previous["evidence"]["artifact_sha256"]:
                raise ValueError("Observed deployed artifact differs from the approved artifact")
            if (
                evidence.get("target") != self.manifest["deployment"]
                or evidence.get("healthy") is not True
            ):
                raise ValueError("Independent target and health verification required")
            proof.artifact(evidence.get("document"), self.repository)

    def check_evidence(self, name: str, evidence: dict[str, Any], code: int) -> None:
        if (
            not isinstance(evidence, dict)
            or not isinstance(evidence.get("summary"), str)
            or not evidence["summary"].strip()
        ):
            raise ValueError("Structured evidence with summary required")
        if name.endswith("/red"):
            proof.strings(evidence.get("failing_tests"), "failing_tests")
            if (
                code != 1
                or evidence.get("failure_kind") != "assertion"
                or not evidence.get("failing_tests")
            ):
                raise ValueError("Red requires assertion failures with test IDs and exit code 1")
        elif code != 0 or evidence.get("passed") is not True:
            raise ValueError("Command and evidence must both pass")
        if self.manifest.get("schema_version") == 2:
            self.check_spec_evidence(name, evidence)
        if (
            name == "brainstorm"
            and len(proof.strings(evidence.get("alternatives"), "alternatives")) < 2
        ):
            raise ValueError("Brainstorm must compare at least two alternatives")
        if name == "plan":
            if self.manifest.get("schema_version") == 2:
                tasks = expand_tasks(self.manifest, evidence.get("tasks"))
                self.validate({**self.manifest, "tasks": tasks})
            elif evidence.get("tasks") != self.manifest["tasks"]:
                raise ValueError("Plan must bind the exact configured task breakdown")
        if name.endswith("/green"):
            proof.strings(evidence.get("passing_tests"), "passing_tests")
            red = next(
                e
                for e in reversed(self.events())
                if e["phase"] == name.removesuffix("green") + "red" and e["success"]
            )
            if not set(red["evidence"]["failing_tests"]) <= set(evidence.get("passing_tests", [])):
                raise ValueError("Previously failing test IDs must now pass")
        if (name.endswith("review") or name in {"security", "verification"}) and evidence.get(
            "blocking_findings"
        ) != []:
            raise ValueError("Explicit empty blocking findings required")
        if name in {"e2e", "verification"}:
            proof.coverage(
                evidence.get("coverage"),
                proof.acceptance_ids(self.manifest["specification"], self.repository)
                if self.manifest.get("schema_version") == 2
                else self.manifest["requirements"],
                self.repository,
            )
        if name == "verification" and any(
            evidence.get("gates", {}).get(g) is not True for g in GATES
        ):
            raise ValueError("All mandatory verification gates must pass")
        if name in {"verification", "deploy"}:
            artifact = evidence.get("artifact_sha256", "")
            if len(artifact) != 64 or any(c not in "0123456789abcdef" for c in artifact):
                raise ValueError("Immutable artifact SHA256 required")
            if name == "verification":
                path = Path(evidence.get("artifact_path", ""))
                if (
                    not path.is_absolute()
                    or not path.is_file()
                    or digest(path.read_bytes()) != artifact
                ):
                    raise ValueError("Verification must bind an existing immutable artifact file")
            if name == "deploy":
                verified = next(
                    e for e in self.events() if e["phase"] == "verification" and e["success"]
                )
                if artifact != verified["evidence"]["artifact_sha256"]:
                    raise ValueError("Deployment artifact differs from verified artifact")
