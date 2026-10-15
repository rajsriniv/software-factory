"""Executable end-to-end controller contract tests; no live LLM or AWS claims."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from software_factory import authority
from software_factory.spec_workflow import phases
from software_factory.workflow import GATES, PHASES, Workflow

HOOK = r"""
import hashlib, json, os, subprocess, sys
from pathlib import Path
phase = os.environ['FACTORY_PHASE']
out = Path(os.environ['FACTORY_EVIDENCE_OUTPUT'])
out.parent.mkdir(parents=True, exist_ok=True)
def ref(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
data = {'summary': phase, 'passed': True, 'blocking_findings': [], 'input_sha256': os.environ['FACTORY_INPUT_SHA256']}
doc = out.with_suffix('.md')
doc.write_text('Reviewed test fixture document for ' + phase)
data['document'] = ref(doc)
if phase == 'company-context':
    data['knowledge_gap'] = True
if phase == 'brainstorm':
    data['alternatives'] = ['pure function', 'HTTP service']
if phase == 'architecture-review':
    data['decision'] = {'eligible_voters':['architect','security','challenger'], 'selected':'pure',
      'options':[{'option_id':'pure','summary':'pure function','utilities':{'risk':0.8}}],
      'votes':[{'agent_id':v,'option_id':'pure','approve':True,'rationale':'meets spec','evidence':[str(doc)]} for v in ['architect','security','challenger']]}
if phase == 'test-design':
    data['test_map'] = {'R1::AC1':['tests.test_feature::test_value']}
if phase == 'plan':
    data['tasks'] = [{'id':'one','template':'python','requirements':['R1'], 'depends_on':[],
      'test_files':['tests/test_feature.py'],'write_files':['value.py'], 'acceptance':['value equals 1']}]
if phase.endswith('/test'):
    Path('tests').mkdir(exist_ok=True)
    Path('tests/test_feature.py').write_text("from pathlib import Path\nimport runpy\ndef test_value():\n    assert Path('value.py').exists()\n    assert runpy.run_path('value.py')['value'] == 1\n")
if phase.endswith('/implement'):
    Path('value.py').write_text('value = 1\n')
if phase in ('e2e','verification'):
    report = out.with_suffix('.xml')
    result = subprocess.run([sys.executable,'-m','pytest','tests/test_feature.py','-q','--junitxml='+str(report)],check=False)
    assert result.returncode == 0
    reference = ref(report)
    reference['test_ids'] = ['tests.test_feature::test_value']
    data['coverage'] = {'R1::AC1':[reference]}
if phase == 'verification':
    artifact = out.with_suffix('.bin')
    artifact.write_bytes(Path('value.py').read_bytes())
    data['artifact_path'] = str(artifact.resolve())
    data['artifact_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    data['gates'] = {k:True for k in ['build','unit','integration','dependencies','iac','provenance','rollback','network-security','observability']}
out.write_text(json.dumps(data))
"""


def fixture(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text(".factory-state/\n__pycache__/\n.pytest_cache/\n")
    (repo / "worker.py").write_text(HOOK)
    spec = repo / "spec.json"
    spec.write_text(
        json.dumps({"requirements": [{"id": "R1", "acceptance": ["Return the integer one"]}]})
    )

    def step(phase):
        return {
            "actor": phase,
            "execution": "tool",
            "command": [sys.executable, "worker.py"],
            "output": ".factory-state/evidence/" + phase + ".json",
        }

    m = {
        "schema_version": 2,
        "requirements": ["R1"],
        "specification": {
            "path": "spec.json",
            "sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
        },
        "assurance": "local",
        "delivery": "verify",
        "frontend": False,
        "existing_system": False,
        "council": ["architect", "security", "challenger"],
        "task_templates": {},
        "tasks": [],
        "gate_commands": {},
        "gate_reports": {},
    }
    m["steps"] = {
        p: step(p) for p in phases(m, PHASES) if p != "tasks" and not p.endswith("approval")
    }
    template = {p: step(p) for p in ("test", "red", "implement", "green", "review")}
    for p in ("red", "green"):
        template[p]["command"] = [
            sys.executable,
            "-m",
            "software_factory.test_receipt",
            "--",
            sys.executable,
            "-m",
            "pytest",
            "tests/test_feature.py",
            "-q",
            "--junitxml={junit}",
        ]
    m["task_templates"] = {"python": template}
    for gate in GATES:
        m["gate_reports"][gate] = f".factory-state/evidence/gate-{gate}.json"
        m["gate_commands"][gate] = [
            sys.executable,
            "-c",
            "import json,os; from pathlib import Path; assert Path('value.py').read_text().strip() == 'value = 1'; Path(os.environ['FACTORY_GATE_REPORT']).write_text(json.dumps({'input_sha256':os.environ['FACTORY_INPUT_SHA256'],'checks':[{'id':'fixture-check','passed':True}]}))",
        ]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(m))
    return Workflow(tmp_path / "run.db", manifest, repo), manifest


def run_until(w, target):
    while w.status()["next"] != target:
        phase = w.status()["next"]
        approval = (
            f"APPROVE {phase} {w.fingerprint} {w.snapshot()}"
            if phase.endswith("approval")
            else None
        )
        event = w.advance(approval)
        assert event["success"], event.get("error", event)


def test_spec_to_approved_plan_to_real_tdd_to_verification(tmp_path):
    w, _ = fixture(tmp_path)
    assert not w.planned_tasks()
    run_until(w, "plan-approval")
    assert w.planned_tasks()[0]["id"] == "one"
    with pytest.raises(ValueError, match="Human confirmation"):
        w.advance()
    run_until(w, "complete")
    assert w.status()["delivery"] == "verify"
    assert w.status()["assurance"] == "local"
    assert not any(e["phase"] == "deploy" for e in w.audit_events())
    (w.repository / "value.py").write_text("value = 2")
    with pytest.raises(ValueError, match="stale"):
        w.status()


def test_local_execution_cannot_enable_deployment(tmp_path):
    w, _ = fixture(tmp_path)
    m = {**w.manifest, "delivery": "deploy"}
    with pytest.raises(ValueError, match="isolated"):
        Workflow.validate(m)


def test_signed_receipt_is_bound_to_run_and_input(tmp_path):
    path = tmp_path / "secret"
    path.write_bytes(b"k" * 32)
    path.chmod(0o600)
    expected = {"run_id": "a", "snapshot": "one"}
    receipt = authority.sign(expected, str(path))
    assert authority.verify(receipt, str(path), expected) == expected
    with pytest.raises(ValueError, match="match"):
        authority.verify(receipt, str(path), {"run_id": "b"})
    receipt["body"]["snapshot"] = "two"
    with pytest.raises(ValueError, match="signature"):
        authority.verify(receipt, str(path), {"run_id": "a"})


def test_bounded_repair_preserves_red_and_invalidates_implementation(tmp_path):
    w, _ = fixture(tmp_path)
    hook = w.repository / "worker.py"
    source = hook.read_text().replace(
        "Path('value.py').write_text('value = 1\\n')",
        "marker=Path('.factory-state/attempt'); Path('value.py').write_text('value = 1\\n' if marker.exists() else 'value = 0\\n'); marker.write_text('attempt')",
    )
    hook.write_text(source)
    run_until(w, "task/one/green")
    event = w.advance()
    assert not event["success"]
    red = next(e for e in w.events() if e["phase"] == "task/one/red")
    w.repair(f"REPAIR {w.run_id} task/one/implement {w.snapshot()}")
    assert w.status()["next"] == "task/one/implement"
    assert next(e for e in w.events() if e["phase"] == "task/one/red") == red
    run_until(w, "complete")
    assert sum(e.get("kind") == "repair" for e in w.audit_events()) == 1


def test_changed_nested_evidence_and_missing_criterion_are_rejected(tmp_path):
    w, _ = fixture(tmp_path)
    run_until(w, "complete")
    event = next(e for e in w.events() if e["phase"] == "e2e")
    receipt = event["evidence"]
    with pytest.raises(ValueError, match="Coverage omits planned acceptance tests"):
        w.check_evidence("e2e", {**receipt, "coverage": {}}, 0)
    report = Path(receipt["coverage"]["R1::AC1"][0]["path"])
    report.write_text("<testsuite/>")
    with pytest.raises(ValueError, match="hash mismatch"):
        w.status()


def test_noop_gate_does_not_count_as_verification(tmp_path):
    w, manifest = fixture(tmp_path)
    data = w.manifest
    data["gate_commands"]["unit"] = [sys.executable, "-c", "pass"]
    manifest.write_text(json.dumps(data))
    w = Workflow(tmp_path / "run.db", manifest, w.repository)
    run_until(w, "verification")
    result = w.advance()
    assert not result["success"]
    assert w.status()["next"] == "verification"


def test_implementation_cannot_write_outside_approved_files(tmp_path):
    w, _ = fixture(tmp_path)
    hook = w.repository / "worker.py"
    hook.write_text(
        hook.read_text().replace(
            "Path('value.py').write_text('value = 1\\n')",
            "Path('value.py').write_text('value = 1\\n'); Path('extra.py').write_text('unapproved')",
        )
    )
    run_until(w, "task/one/implement")
    result = w.advance()
    assert not result["success"]
    with pytest.raises(ValueError, match="mutation"):
        w.status()


def test_initializer_builds_reviewable_client_manifests(tmp_path):
    w, _ = fixture(tmp_path)
    checks = tmp_path / "checks.json"
    checks.write_text(
        json.dumps(
            {
                **w.manifest["gate_commands"],
                "e2e": [sys.executable, "-m", "pytest", "--junitxml={junit}"],
            }
        )
    )
    for host in ("claude", "codex", "copilot"):
        output = tmp_path / f"{host}.json"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/init_spec_workflow.py",
                "--repository",
                str(w.repository),
                "--spec",
                str(w.repository / "spec.json"),
                "--checks",
                str(checks),
                "--host",
                host,
                "--high-model",
                "test-high",
                "--low-model",
                "test-low",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(output.read_text())
        Workflow.validate(data)
        assert not data["tasks"]
        assert data["steps"]["architecture"]["model"] == "test-high"
        assert data["task_templates"]["python"]["implement"]["model"] == "test-low"


def test_unprivileged_worker_cannot_read_controller_key(tmp_path):
    import os

    from software_factory.execution import execute

    if os.geteuid() != 0:
        pytest.skip("OS isolation test requires privileged POSIX test runner")
    secret = tmp_path / "approval.key"
    secret.write_bytes(b"not-a-real-secret" * 4)
    secret.chmod(0o600)
    command = [
        sys.executable,
        "-c",
        f"from pathlib import Path\ntry:\n Path({str(secret)!r}).read_bytes()\nexcept PermissionError:\n raise SystemExit(0)\nraise SystemExit(1)",
    ]
    try:
        result = execute(
            command, cwd=Path("/tmp"), timeout=10, env={}, user=65534, group=65534, extra_groups=[]
        )
    except PermissionError:
        pytest.skip("Host denies UID/GID switching; cannot validate OS isolation here")
    assert result.returncode == 0
