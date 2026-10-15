"""Strict, content-addressed evidence checks. Assertions are not execution receipts."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def strings(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(v, str) or not v.strip() for v in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{label} must be a nonempty list of unique strings")
    return value


def artifact(reference: Any, repository: Path) -> Path:
    if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
        raise ValueError("Evidence requires path and sha256")  # noqa: TRY004 - external document validation contract
    path: Path = (repository / str(reference["path"])).resolve()
    if not path.is_relative_to(repository) or not path.is_file():
        raise ValueError("Evidence must reference an existing file inside the repository")
    if path.stat().st_size > 10_000_000:
        raise ValueError("Evidence file exceeds 10MB; split the report")
    if hashlib.sha256(path.read_bytes()).hexdigest() != reference.get("sha256"):
        raise ValueError("Evidence artifact hash mismatch")
    return path


def junit(path: Path) -> tuple[set[str], set[str], int]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError("Invalid JUnit evidence") from exc
    passed: set[str] = set()
    failed: set[str] = set()
    seen: set[str] = set()
    errors = 0
    for case in root.iter("testcase"):
        name = case.get("classname", "") + "::" + case.get("name", "")
        if not case.get("name") or name in seen:
            raise ValueError("JUnit test IDs must be present and unique")
        seen.add(name)
        if case.find("error") is not None:
            errors += 1
        elif case.find("failure") is not None:
            failed.add(name)
        elif case.find("skipped") is None:
            passed.add(name)
    if not seen:
        raise ValueError("JUnit report contains no tests")
    return passed, failed, errors


def coverage(value: Any, requirements: list[str], repository: Path) -> None:
    if not isinstance(value, dict) or set(value) != set(requirements):
        raise ValueError("Coverage must map every requirement to executed tests")
    for refs in value.values():
        if not isinstance(refs, list) or not refs:
            raise ValueError("Coverage references must be a nonempty list")
        for ref in refs:
            path = artifact(ref, repository)
            tests = strings(ref.get("test_ids"), "test_ids")
            passed, failed, errors = junit(path)
            if errors or failed or not set(tests) <= passed:
                raise ValueError(
                    "Coverage references must identify passing tests in a clean report"
                )


def validate_references(value: Any, repository: Path) -> None:
    """Revalidate every content-addressed reference in accepted evidence."""
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            artifact(value, repository)
        for child in value.values():
            validate_references(child, repository)
    elif isinstance(value, list):
        for child in value:
            validate_references(child, repository)


def specification(reference: Any, requirements: list[str], repository: Path) -> None:
    data = json.loads(artifact(reference, repository).read_text())
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        raise ValueError("Specification requires a requirements array")  # noqa: TRY004 - external document validation contract
    ids = []
    for item in data["requirements"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Each requirement needs an ID")  # noqa: TRY004 - external document validation contract
        strings(item.get("acceptance"), "acceptance criteria")
        ids.append(item["id"])
    strings(ids, "requirement IDs")
    if set(ids) != set(requirements):
        raise ValueError("Manifest requirement IDs differ from approved specification")


def acceptance_ids(reference: Any, repository: Path) -> list[str]:
    data = json.loads(artifact(reference, repository).read_text())
    return [
        f"{item['id']}::AC{number}"
        for item in data["requirements"]
        for number, _ in enumerate(item["acceptance"], 1)
    ]
