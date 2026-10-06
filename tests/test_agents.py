import pytest

from software_factory.agents import AgentRunError, command
from software_factory.models import AgentSpec


@pytest.mark.parametrize("host,executable", [("claude", "claude"), ("codex", "codex"), ("copilot", "copilot")])
def test_adapter_preserves_prompt_as_one_argument(host: str, executable: str) -> None:
    spec = AgentSpec("a", "architect", host, "explicit-model", "high", ("read",))
    prompt = "literal $(touch bad); `echo bad`"
    argv = command(spec, prompt)
    assert argv[0] == executable
    assert prompt in argv
    assert "explicit-model" in " ".join(argv)


def test_unknown_host_is_rejected() -> None:
    spec = AgentSpec("a", "architect", "unknown", "model", "high", ())
    with pytest.raises(AgentRunError):
        command(spec, "prompt")
