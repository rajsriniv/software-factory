from datetime import UTC, datetime, timedelta

import pytest

from software_factory.brain import CompanyBrain


def test_persistence_revision_scope_and_budget(tmp_path):
    path = tmp_path / 'brain.db'
    brain = CompanyBrain(path)
    expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    brain.ingest('a', 'platform', 'Iceberg old', 'owner', expiry, ['architect'])
    digest = brain.ingest('a', 'platform', 'Iceberg current AWS', 'owner', expiry, ['architect'])
    packet = CompanyBrain(path).query('a', 'architect', 'Iceberg', 10)
    assert packet['sources'][0]['revision'] == 2
    assert packet['sources'][0]['sha256'] == digest
    assert len(packet['sources'][0]['excerpt']) == 10
    assert packet['sources'][0]['truncated']
    assert brain.query('a', 'python', 'Iceberg')['status'] == 'knowledge-gap'
    assert brain.query('b', 'architect', 'Iceberg')['status'] == 'knowledge-gap'
    assert brain.query('a', 'architect', 'unrelated')['status'] == 'knowledge-gap'


def test_expired_latest_does_not_fall_back(tmp_path):
    brain = CompanyBrain(tmp_path / 'brain.db')
    expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    brain.ingest('a', 'policy', 'AWS policy', 'owner', expiry, ['architect'])
    with brain.connect() as db:
        db.execute('UPDATE knowledge SET expires=?',
                   ((datetime.now(UTC) - timedelta(days=1)).isoformat(),))
    assert brain.query('a', 'architect', 'AWS')['status'] == 'knowledge-gap'
    with pytest.raises(ValueError):
        brain.ingest('a', 'policy', 'AWS', 'owner', '2020-01-01', ['architect'])
    with pytest.raises(ValueError):
        brain.query('a', 'architect', 'AWS', 0)
