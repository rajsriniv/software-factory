from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


REQUIRED_ROLES = {
    "product", "architect", "security", "planner", "java", "python", "react",
    "quality", "reviewer", "release",
}


def load_factory(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(str(exc)) from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ConfigError("schema_version must be 1")
    allowed = {"schema_version", "factory", "agents", "councils", "profiles", "aws", "governance"}
    unknown = set(raw) - allowed
    if unknown:
        raise ConfigError(f"Unknown top-level fields: {sorted(unknown)}")
    agents = raw.get("agents")
    if not isinstance(agents, dict) or not REQUIRED_ROLES <= set(agents):
        raise ConfigError(f"Missing roles: {sorted(REQUIRED_ROLES - set(agents or {}))}")
    for agent_id, agent in agents.items():
        if not isinstance(agent, dict) or agent.get("tier") not in {"high", "low"}:
            raise ConfigError(f"Agent {agent_id} needs high/low tier")
        if not agent.get("model") or str(agent["model"]).lower() in {"auto", "inherit"}:
            raise ConfigError(f"Agent {agent_id} needs an explicit model")
        if agent.get("host") not in {"claude", "codex", "copilot"}:
            raise ConfigError(f"Agent {agent_id} needs a supported host")
    for role in ("company-brain", "prompt-refiner", "tdd-guide", "sdet"):
        if role in agents and agents[role]["tier"] != "high":
            raise ConfigError(f"{role} requires a high-tier model")
    for council_id, members in raw.get("councils", {}).items():
        if not isinstance(members, list) or len(members) < 3 or len(members) % 2 == 0:
            raise ConfigError(f"Council {council_id} must have an odd membership of at least three")
        if not set(members) <= set(agents):
            raise ConfigError(f"Council {council_id} contains unknown agents")
    return raw
