import json
import sys
from pathlib import Path

from software_factory.test_receipt import execute


def test_real_pytest_red_green_and_collection_error(tmp_path: Path) -> None:
    for phase, source, expected in (
        ("red", "def test_value():\n    assert 1 == 2\n", 1),
        ("green", "def test_value():\n    assert 1 == 1\n", 0),
        ("error", "import missing_dependency_for_factory_test\n", 2),
    ):
        phase_dir = tmp_path / phase
        phase_dir.mkdir()
        test = phase_dir / "test_example.py"
        test.write_text(source)
        report, output = tmp_path / f"{phase}.xml", tmp_path / f"{phase}.json"
        result = execute(
            [sys.executable, "-m", "pytest", "-q", str(test), f"--junitxml={report}"],
            report,
            output,
        )
        assert result == expected
        evidence = json.loads(output.read_text())
        assert evidence["passed"] == (phase == "green")
        assert evidence["failure_kind"] == ("assertion" if phase == "red" else "execution")
