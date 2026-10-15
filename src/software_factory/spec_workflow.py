"""Version-two spec contracts and task expansion; no agent-supplied executable code."""

from __future__ import annotations

import copy
import re
from typing import Any

from .evidence import strings


def phases(manifest: dict[str, Any], original: tuple[str, ...]) -> tuple[str, ...]:
    if manifest.get("schema_version") != 2:
        return original
    result = list(original)
    result.insert(0, "company-context")
    if manifest.get("existing_system"):
        result.insert(1, "discovery")
    result.insert(result.index("architecture-review"), "security-architecture")
    result.insert(result.index("architecture-review"), "architecture-challenge")
    if manifest.get("frontend"):
        index = result.index("architecture-review")
        result[index:index] = ["ux-design", "ui-review", "ui-approval"]
    result.insert(result.index("test-design"), "plan-approval")
    result.insert(result.index("release-approval"), "knowledge-proposal")
    if manifest.get("delivery") == "verify":
        result = result[: result.index("release-approval")]
    else:
        result.append("deployment-verification")
    return tuple(result)


def expand_tasks(manifest: dict[str, Any], declarations: Any) -> list[dict[str, Any]]:
    if not isinstance(declarations, list) or not declarations:
        raise ValueError("Planner must produce a nonempty task graph")
    tasks = []
    seen: set[str] = set()
    for task in declarations:
        fields = {
            "id",
            "template",
            "requirements",
            "depends_on",
            "test_files",
            "write_files",
            "acceptance",
        }
        if not isinstance(task, dict) or set(task) != fields:
            raise ValueError("Planner task fields must match the version-two contract")
        name = task["id"]
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name)
            or name in seen
        ):
            raise ValueError("Task IDs must be unique safe identifiers")
        if not isinstance(task["depends_on"], list) or not set(task["depends_on"]) <= seen:
            raise ValueError("Planner tasks must be in dependency order")
        seen.add(name)
        strings(task["requirements"], "task requirements")
        strings(task["acceptance"], "task acceptance criteria")
        for key in ("test_files", "write_files"):
            for path in strings(task[key], key):
                if any(
                    part in {".git", ".gitignore", ".gitmodules", ".factory-state"}
                    for part in path.split("/")
                ):
                    raise ValueError("Tasks cannot modify repository control or evidence paths")
                if path.startswith(("/", ".git/", ".factory-state/")) or ".." in path.split("/"):
                    raise ValueError("Task paths must be relative source paths")
        if set(task["test_files"]) & set(task["write_files"]):
            raise ValueError("Implementation and protected test paths cannot overlap")
        if task["template"] not in manifest["task_templates"]:
            raise ValueError("Planner cannot introduce new executable templates")
        steps = copy.deepcopy(manifest["task_templates"][task["template"]])
        for stage, step in steps.items():
            step["output"] = f".factory-state/evidence/{name}-{stage}.json"
        tasks.append({**task, "steps": steps})
    return tasks


def validate_spec_manifest(m: dict[str, Any]) -> None:
    if m.get("delivery") not in {"verify", "deploy"}:
        raise ValueError("Version two requires delivery=verify or deploy")
    if m.get("assurance") not in {"local", "isolated"}:
        raise ValueError("Version two requires explicit local or isolated assurance")
    if m["delivery"] == "deploy" and m["assurance"] != "isolated":
        raise ValueError("Deployment requires isolated execution and authenticated approval")
    if not isinstance(m.get("specification"), dict):
        raise ValueError("Version two requires a content-addressed specification")  # noqa: TRY004 - external document validation contract
    if not isinstance(m.get("task_templates"), dict) or not m["task_templates"]:
        raise ValueError("Version two requires operator-owned task templates")
    for flag in ("frontend", "existing_system"):
        if type(m.get(flag)) is not bool:
            raise ValueError(f"{flag} must be an explicit boolean applicability decision")
    if type(m.get("max_attempts", 3)) is not int or not 1 <= m.get("max_attempts", 3) <= 5:
        raise ValueError("max_attempts must be from 1 to 5")
    budget = m.get("budget", {})
    if (
        not isinstance(budget, dict)
        or not set(budget) <= {"tokens", "cost_microunits"}
        or any(type(v) is not int or v <= 0 for v in budget.values())
    ):
        raise ValueError("Budget limits must be positive integer tokens/cost_microunits")
    if m["delivery"] == "deploy":
        target = m.get("deployment", {})
        if set(target) != {"account", "region", "environment", "plan"} or any(
            not target.get(k) for k in ("account", "region", "environment", "plan")
        ):
            raise ValueError("Deployment requires account, region, environment and hashed plan")
