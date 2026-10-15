import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from software_factory.config import ConfigError, load_factory


@pytest.mark.parametrize('host', ['claude', 'codex', 'copilot'])
def test_installer_assigns_high_model_and_discovery_reference(tmp_path, host):
    subprocess.run([sys.executable, 'scripts/install_agents.py', '--host', host,
                    '--high-model', 'test-high', '--low-model', 'test-low',
                    '--destination', str(tmp_path)], check=True, capture_output=True)
    files = list((tmp_path/'agents').glob('factory-reverse-engineer.*'))
    assert len(files) == 1
    assert 'test-high' in files[0].read_text()
    assert 'references/reverse-engineering.md' in files[0].read_text()
    assert (tmp_path/'skills/software-factory/references/reverse-engineering.md').exists()


def test_reverse_engineer_cannot_use_low_tier(tmp_path):
    config = yaml.safe_load(Path('config/factory.example.yaml').read_text())
    config['agents']['reverse-engineer']['tier'] = 'low'
    path = tmp_path/'config.yaml'
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ConfigError, match='reverse-engineer requires a high-tier'):
        load_factory(path)
