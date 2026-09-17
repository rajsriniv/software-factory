from pathlib import Path

from software_factory.config import load_factory


def test_example_config_is_valid() -> None:
    config = load_factory(Path("config/factory.example.yaml"))
    assert config["governance"]["fallback"] == "zero-sum-maximin"

