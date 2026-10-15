from datetime import UTC, datetime, timedelta

import pytest

from software_factory.knowledge_updates import KnowledgeUpdates


def document(content='Approved architecture'):
    return {'company': 'a', 'source': 'project/architecture', 'content': content,
            'owner': 'team', 'expires': (datetime.now(UTC)+timedelta(days=1)).isoformat(),
            'roles': ['architect'], 'task_id': 'task-1', 'repository_revision': 'commit-1',
            'author': 'company-brain', 'evidence': ['reviewed-architecture.md#sha256']}


def approve(store, proposal):
    store.review(proposal, 'reviewer', 'review-receipt', True)
    store.approve(proposal, 'human', 'human-response', proposal)


def test_no_publish_until_independent_review_and_exact_approval(tmp_path):
    store = KnowledgeUpdates(tmp_path/'brain.db')
    proposal = store.propose(document())
    assert store.brain.query('a', 'architect', 'architecture')['status'] == 'knowledge-gap'
    with pytest.raises(ValueError, match='human-approved'):
        store.publish(proposal, lambda company: None)
    with pytest.raises(ValueError, match='review'):
        store.approve(proposal, 'human', 'receipt', proposal)
    with pytest.raises(ValueError, match='Independent'):
        store.review(proposal, 'company-brain', 'receipt', True)
    store.review(proposal, 'reviewer', 'receipt', True)
    with pytest.raises(ValueError, match='Exact'):
        store.approve(proposal, 'human', 'receipt', 'wrong-hash')
    store.approve(proposal, 'human', 'receipt', proposal)
    calls = []
    assert store.publish(proposal, calls.append)['state'] == 'published'
    assert calls == ['a']
    assert store.publish(proposal, calls.append)['published_revision'] == 1
    assert calls == ['a']
    assert store.brain.query('a', 'architect', 'architecture')['sources'][0]['revision'] == 1
    assert store.events('task-1')[-1]['kind'] == 'knowledge-published'
    assert store.events('other') == []


def test_index_failure_is_retryable_without_duplicate_import(tmp_path):
    store = KnowledgeUpdates(tmp_path/'brain.db')
    proposal = store.propose(document())
    approve(store, proposal)

    def fail(company):
        raise RuntimeError('missing model')

    with pytest.raises(ValueError, match='Retry publish'):
        store.publish(proposal, fail)
    assert store.inspect(proposal)['state'] == 'index-pending'
    assert store.publish(proposal, lambda company: None)['published_revision'] == 1
    with store.brain.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0] == 1


def test_stale_source_and_rejection_do_not_publish(tmp_path):
    store = KnowledgeUpdates(tmp_path/'brain.db')
    proposal = store.propose(document())
    approve(store, proposal)
    data = document('Newer source')
    store.brain.ingest(data['company'], data['source'], data['content'], data['owner'],
                       data['expires'], data['roles'])
    with pytest.raises(ValueError, match='Source changed'):
        store.publish(proposal, lambda company: None)
    other = store.propose(document('Alternative'))
    store.reject(other, 'human', 'Not approved')
    with pytest.raises(ValueError, match='human-approved'):
        store.publish(other, lambda company: None)


def test_failed_review_cannot_be_approved_and_changed_text_is_new_proposal(tmp_path):
    store = KnowledgeUpdates(tmp_path/'brain.db')
    proposal = store.propose(document())
    store.review(proposal, 'reviewer', 'unsupported facts', False)
    with pytest.raises(ValueError, match='review'):
        store.approve(proposal, 'human', 'receipt', proposal)
    new = store.propose(document('Corrected architecture'))
    assert new != proposal and store.inspect(new)['state'] == 'proposed'


def test_publish_refreshes_real_sqlite_vector_index(tmp_path):
    pytest.importorskip('sqlite_vec')
    from software_factory.vector_brain import VectorBrain

    class Embedder:
        model = 'fixture-v1'

        def documents(self, texts):
            return [[1.0, 0.0] for _ in texts]

        def question(self, text):
            return [1.0, 0.0]

    path = tmp_path/'brain.db'
    store = KnowledgeUpdates(path)
    proposal = store.propose(document())
    approve(store, proposal)
    vector = VectorBrain(path, Embedder())
    store.publish(proposal, vector.index)
    assert vector.query('a', 'architect', 'design')['sources'][0]['revision'] == 1
    assert vector.query('a', 'python', 'design')['status'] == 'knowledge-gap'


def test_cli_rejects_noninteractive_approval(tmp_path):
    import subprocess
    import sys

    path = tmp_path/'brain.db'
    store = KnowledgeUpdates(path)
    proposal = store.propose(document())
    store.review(proposal, 'reviewer', 'receipt', True)
    result = subprocess.run([sys.executable, '-m', 'software_factory.cli', 'brain-updates',
                             'approve', '--database', str(path), '--proposal', proposal,
                             '--actor', 'human', '--evidence', 'receipt'],
                            check=False, input='APPROVE '+proposal, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'interactive terminal' in result.stderr
    assert store.inspect(proposal)['state'] == 'reviewed'
