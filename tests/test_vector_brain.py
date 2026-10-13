from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip('sqlite_vec')
from software_factory.brain import CompanyBrain
from software_factory.vector_brain import VectorBrain


class FixtureEmbedder:
    """Controlled vectors test retrieval mechanics, not a learned model's quality."""
    model = 'fixture-v1'

    def documents(self, texts):
        return [self.question(text) for text in texts]

    def question(self, text):
        if any(term in text.lower() for term in ('credential', 'password', 'secret')):
            return [1.0, 0.0]
        return [0.0, 1.0]


def ingest(brain, source, text, company='a', roles=None):
    return brain.ingest(company, source, text, 'owner',
                        (datetime.now(UTC) + timedelta(days=1)).isoformat(), roles or ['architect'])


def test_semantic_paraphrase_persistence_and_citations(tmp_path):
    path = tmp_path / 'brain.db'
    brain = CompanyBrain(path)
    digest = ingest(brain, 'identity', 'Rotate credentials regularly.')
    vector = VectorBrain(path, FixtureEmbedder())
    vector.index('a')
    assert brain.query('a', 'architect', 'password')['status'] == 'knowledge-gap'
    packet = VectorBrain(path, FixtureEmbedder()).query('a', 'architect', 'password', mode='vector')
    assert packet['sources'][0]['sha256'] == digest
    assert packet['sources'][0]['source'] == 'identity'
    assert packet['sources'][0]['revision'] == 1
    assert packet['sources'][0]['offset'] == 0


def test_filters_before_top_k_and_stale_index(tmp_path):
    path = tmp_path / 'brain.db'
    brain = CompanyBrain(path)
    ingest(brain, 'allowed', 'Rotate credentials.')
    ingest(brain, 'denied', 'Credentials policy', roles=['security'])
    ingest(brain, 'expired', 'Credentials policy')
    ingest(brain, 'foreign', 'Credentials policy', company='b')
    vector = VectorBrain(path, FixtureEmbedder())
    vector.index('a')
    vector.index('b')
    with brain.connect() as db:
        db.execute("UPDATE knowledge SET expires='2000-01-01T00:00:00+00:00' WHERE source='expired'")
    packet = vector.query('a', 'architect', 'password', top_k=1)
    assert [s['source'] for s in packet['sources']] == ['allowed']
    ingest(brain, 'allowed', 'Network segmentation')
    with pytest.raises(ValueError, match='not indexed'):
        vector.query('a', 'architect', 'password')
    vector.index('a')
    assert vector.query('a', 'architect', 'password', mode='vector')['status'] == 'knowledge-gap'


def test_chunked_hybrid_budget_and_model_mismatch(tmp_path):
    path = tmp_path / 'brain.db'
    brain = CompanyBrain(path)
    ingest(brain, 'long', 'Network text. ' * 150 + ' Credentials policy.')
    vector = VectorBrain(path, FixtureEmbedder())
    assert vector.index('a')['indexed_chunks'] > 1
    packet = vector.query('a', 'architect', 'password', max_chars=50, top_k=1, mode='vector')
    assert packet['sources'][0]['offset'] > 0
    assert len(packet['sources'][0]['excerpt']) <= 50
    assert vector.query('a', 'architect', 'Network', mode='hybrid')['sources']
    embedder = FixtureEmbedder()
    embedder.model = 'different'
    with pytest.raises(ValueError, match='match'):
        VectorBrain(path, embedder).query('a', 'architect', 'password')
    with pytest.raises(ValueError, match='changed'):
        VectorBrain(path, embedder).index('a')


def test_missing_index_and_failed_reindex_preserve_previous_data(tmp_path):
    path = tmp_path / 'brain.db'
    brain = CompanyBrain(path)
    ingest(brain, 'identity', 'Credentials policy')
    vector = VectorBrain(path, FixtureEmbedder())
    with pytest.raises(ValueError, match='missing'):
        vector.query('a', 'architect', 'password')
    vector.index('a')

    class Broken(FixtureEmbedder):
        def documents(self, texts):
            return [[float('nan'), 0.0] for _ in texts]

    with pytest.raises(ValueError, match='Invalid embedding'):
        VectorBrain(path, Broken()).index('a')
    assert vector.query('a', 'architect', 'password')['sources']
    with pytest.raises(ValueError):
        vector.query('a', 'architect', 'password', top_k=0)
