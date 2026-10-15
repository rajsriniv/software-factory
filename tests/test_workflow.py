import json
import subprocess
import sys
from pathlib import Path

import pytest

from software_factory.workflow import GATES, PHASES, Workflow, digest


def setup(tmp_path: Path, tamper=False, fail_gate=False) -> Workflow:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text("evidence/\n")
    (repo / "evidence").mkdir()
    (repo / "test.txt").write_text("assert value == 1")
    artifact = tmp_path / "artifact"
    artifact.write_bytes(b"immutable build")
    report = repo / "evidence/e2e.xml"
    report.write_text('<testsuite><testcase classname="suite" name="e2e_case"/></testsuite>')
    coverage = {
        "R1": [
            {
                "path": str(report),
                "sha256": digest(report.read_bytes()),
                "test_ids": ["suite::e2e_case"],
            }
        ]
    }

    def spec(name, actor="specialist", extra=None, code=0):
        data = {"passed": True, "summary": name, "blocking_findings": []}
        data.update(extra or {})
        output = f"evidence/{name}.json"
        command = [
            sys.executable,
            "-c",
            f"import os,json; from pathlib import Path; data=json.loads({json.dumps(data)!r}); data['input_sha256']=os.environ['FACTORY_INPUT_SHA256']; Path({output!r}).write_text(json.dumps(data)); raise SystemExit({code})",
        ]
        return {"actor": actor, "output": output, "command": command}

    m = {
        "requirements": ["R1"],
        "steps": {},
        "tasks": [],
        "gate_commands": {g: [sys.executable, "-c", "pass"] for g in GATES},
    }
    for phase in PHASES:
        if phase != "tasks" and not phase.endswith("approval"):
            m["steps"][phase] = spec(phase, actor=phase)
    task = {
        "id": "t1",
        "requirements": ["R1"],
        "depends_on": [],
        "test_files": ["test.txt"],
        "steps": {},
    }
    for name in ("test", "red", "implement", "green", "review"):
        task["steps"][name] = spec(name, actor=name)
    # This harness really fails an assertion until the implementation changes value.py.
    test_command = [
        sys.executable,
        "-c",
        """import json
from pathlib import Path
ok = Path('value.py').exists()
name = 'green' if ok else 'red'
try:
    assert ok, 'value is not implemented'
except AssertionError:
    Path('evidence/red.json').write_text(json.dumps({'summary':'expected assertion', 'failure_kind':'assertion', 'failing_tests':['test_value']}))
    raise SystemExit(1)
Path('evidence/green.json').write_text(json.dumps({'summary':'assertion passed','passed':True,'passing_tests':['test_value']}))
""",
    ]
    task["steps"]["red"]["command"] = test_command
    task["steps"]["green"]["command"] = test_command
    task["steps"]["implement"]["command"][2] = (
        "from pathlib import Path; Path('value.py').write_text('value = 1'); "
        + task["steps"]["implement"]["command"][2]
    )
    if tamper:
        task["steps"]["implement"]["command"][2] = (
            "from pathlib import Path; Path('test.txt').write_text('assert True'); "
            + task["steps"]["implement"]["command"][2]
        )
    if fail_gate:
        m["gate_commands"]["unit"] = [sys.executable, "-c", "raise SystemExit(1)"]
    m["tasks"] = [task]
    m["steps"]["brainstorm"] = spec("brainstorm", extra={"alternatives": ["a", "b"]})
    m["steps"]["plan"] = spec("plan", extra={"tasks": m["tasks"]})
    m["steps"]["e2e"] = spec("e2e", actor="sdet", extra={"coverage": coverage})
    m["steps"]["verification"] = spec(
        "verification",
        actor="verifier",
        extra={
            "coverage": coverage,
            "gates": dict.fromkeys(GATES, True),
            "artifact_path": str(artifact),
            "artifact_sha256": digest(artifact.read_bytes()),
        },
    )
    m["steps"]["deploy"] = spec("deploy", extra={"artifact_sha256": digest(artifact.read_bytes())})
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(m))
    return Workflow(tmp_path / "controller.db", manifest, repo)


def advance_to(w, target):
    while w.status()["next"] != target:
        phase = w.status()["next"]
        approval = (
            f"APPROVE {phase} {w.fingerprint} {w.snapshot()}"
            if phase.endswith("approval")
            else None
        )
        event = w.advance(approval)
        assert event["success"], event


def test_ordered_full_workflow_and_durable_resume(tmp_path):
    w = setup(tmp_path)
    assert w.advance()["success"]
    with pytest.raises(ValueError, match="Human confirmation"):
        w.advance()
    advance_to(w, "complete")
    resumed = Workflow(tmp_path / "controller.db", tmp_path / "manifest.json", w.repository)
    assert resumed.status()["next"] == "complete"
    assert set(resumed.events()[-3]["gate_runs"]) == set(GATES)
    with pytest.raises(ValueError, match="already complete"):
        resumed.advance()


def test_source_change_invalidates_handoff(tmp_path):
    w = setup(tmp_path)
    w.advance()
    (w.repository / "surprise.py").write_text("changed")
    with pytest.raises(ValueError, match="changed outside"):
        w.advance()


def test_protected_tests_cannot_be_rewritten(tmp_path):
    w = setup(tmp_path, tamper=True)
    advance_to(w, "task/t1/implement")
    assert w.advance()["success"] is False
    with pytest.raises(ValueError, match="mutation"):
        w.advance()


def test_executed_failure_overrules_passing_claim(tmp_path):
    w = setup(tmp_path, fail_gate=True)
    advance_to(w, "verification")
    assert w.advance()["success"] is False
    assert w.status()["next"] == "verification"


def test_artifact_change_blocks_deployment_before_command(tmp_path):
    w = setup(tmp_path)
    advance_to(w, "deploy")
    (tmp_path / "artifact").write_text("different")
    with pytest.raises(ValueError, match="artifact changed"):
        w.advance()
    assert not (w.repository / "evidence/deploy.json").exists()


def test_crash_marker_fails_closed(tmp_path):
    w = setup(tmp_path)
    w.db.execute("INSERT INTO inflight VALUES (1, 'deploy')")
    w.db.commit()
    with pytest.raises(ValueError, match="Interrupted"):
        w.advance()


def test_same_actor_review_rejected(tmp_path):
    w = setup(tmp_path)
    w.manifest["tasks"][0]["steps"]["review"]["actor"] = "implement"
    with pytest.raises(ValueError, match="independent"):
        Workflow.validate(w.manifest)


def test_accepted_evidence_cannot_change(tmp_path):
    w = setup(tmp_path)
    w.advance()
    (w.repository / "evidence/refine.json").write_text("{}")
    with pytest.raises(ValueError, match="evidence changed"):
        w.advance()


def test_manifest_change_requires_new_approvals(tmp_path):
    w = setup(tmp_path)
    w.advance()
    manifest = tmp_path / "manifest.json"
    data = json.loads(manifest.read_text())
    data["steps"]["deploy"]["actor"] = "other-deployer"
    manifest.write_text(json.dumps(data))
    resumed = Workflow(tmp_path / "controller.db", manifest, w.repository)
    with pytest.raises(ValueError, match="Manifest or repository changed"):
        resumed.advance()


def test_cli_approval_rejects_pipe(tmp_path):
    w = setup(tmp_path)
    w.advance()
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "software_factory.cli",
            "workflow",
            "approve",
            "--database",
            str(tmp_path / "controller.db"),
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--repository",
            str(w.repository),
        ],
        input="APPROVE anything",
        text=True,
        capture_output=True,
        check=False,
    )
    assert run.returncode != 0
    assert "interactive terminal" in run.stderr
    assert w.status()["next"] == "intake-approval"


def test_concurrent_handoff_cannot_advance(tmp_path):
    import sqlite3

    w = setup(tmp_path)
    other = Workflow(tmp_path / "controller.db", tmp_path / "manifest.json", w.repository)
    w.db.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            other.advance()
    finally:
        w.db.rollback()
    assert w.status()["next"] == "refine"


def test_stale_completion_is_not_current_success(tmp_path):
    w = setup(tmp_path)
    advance_to(w, "complete")
    (w.repository / "value.py").write_text("broken")
    with pytest.raises(ValueError, match="stale"):
        w.status()


def test_fabricated_coverage_and_malformed_alternatives_rejected(tmp_path):
    w = setup(tmp_path)
    with pytest.raises(ValueError, match="list"):
        w.check_evidence("brainstorm", {"passed": True, "summary": "x", "alternatives": "ab"}, 0)
    with pytest.raises(ValueError):
        w.check_evidence("e2e", {"passed": True, "summary": "x", "coverage": {"R1": ["fake"]}}, 0)
