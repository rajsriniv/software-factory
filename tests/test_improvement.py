import sqlite3

import pytest

from software_factory.improvement import ImprovementStore


def proposal(content, parent='', author='proposer'):
    return {'kind': 'prompt', 'target': 'factory-python', 'content': content, 'author': author,
                'rationale': 'Observed test failures', 'parent': parent, 'baseline_revision': 'commit-a',
                'policy_sha256': 'a' * 64, 'evaluation_plan_sha256': 'b' * 64}


def report(store, candidate, phase='smoke', passed=4, total=4, cost=1.0, evaluator='quality'):
    c = store.candidate(candidate)
    return {'phase': phase, 'candidate_sha256': c['content_sha256'],
                'evaluation_plan_sha256': c['evaluation_plan_sha256'], 'policy_sha256': c['policy_sha256'],
                'passed': passed, 'total': total, 'cost_usd': cost, 'tokens': 100, 'seconds': 2.0,
                'evidence': ['immutable-report-sha256'], 'evaluator': evaluator, 'model': 'verified-model-id',
                'blocking_findings': [], 'policy_preserved': True}


def approval(store, candidate):
    c = store.candidate(candidate)
    return {'candidate': candidate, 'candidate_sha256': c['content_sha256'],
                'policy_sha256': c['policy_sha256'], 'evaluation_plan_sha256': c['evaluation_plan_sha256'],
                'reviewer': 'human', 'evidence': 'signed-user-response', 'decision': 'approve',
                'assessment_sha256': store.assessment_hash(candidate)}


def test_scope_integrity_and_duplicate_evidence(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    root = store.propose(proposal('Baseline'))
    assert ImprovementStore(store.path).candidate(root)['content'] == 'Baseline'
    invalid = proposal('Change', root)
    invalid['policy_sha256'] = 'c' * 64
    with pytest.raises(ValueError, match='scope'):
        store.propose(invalid)
    data = report(store, root)
    data['candidate_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='Stale'):
        store.evaluate(root, data)
    store.evaluate(root, report(store, root))
    with pytest.raises(sqlite3.IntegrityError):
        store.evaluate(root, report(store, root))


def test_ranking_is_independent_and_smoke_gated(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    a = store.propose(proposal('Baseline'))
    b = store.propose(proposal('Run tests after editing', a))
    with pytest.raises(ValueError, match='smoke'):
        store.compare(a, b, b, 'judge', 'model', 'reason', 'receipt')
    for c in (a, b):
        store.evaluate(c, report(store, c))
    with pytest.raises(ValueError, match='Independent'):
        store.compare(a, b, b, 'proposer', 'model', 'reason', 'receipt')
    store.compare(a, b, b, 'judge', 'model', 'meaningful test loop', 'receipt')
    assert store.rank(a)[0]['candidate'] == b
    assert store.rank(a)[0]['purpose'] == 'evaluation-priority-only'
    with pytest.raises(ValueError, match='benchmark'):
        store.select(b, {})


def test_selection_requires_independent_review_and_exact_human_approval(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    a = store.propose(proposal('Baseline'))
    b = store.propose(proposal('Clearer verification', a))
    store.evaluate(b, report(store, b))
    store.evaluate(a, report(store, a, 'benchmark', 3))
    store.evaluate(b, report(store, b, 'benchmark', 4))
    with pytest.raises(ValueError, match='own'):
        store.evaluate(b, report(store, b, 'review', evaluator='proposer'))
    store.evaluate(b, report(store, b, 'review'))
    bad = approval(store, b)
    bad['candidate_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='approval'):
        store.select(b, bad)
    store.select(b, approval(store, b))
    assert store.candidate(a)['content'] == 'Baseline'


def test_no_regression_even_if_cheaper(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    a = store.propose(proposal('Baseline'))
    b = store.propose(proposal('Cheaper but wrong', a))
    store.evaluate(b, report(store, b))
    store.evaluate(a, report(store, a, 'benchmark', 4))
    store.evaluate(b, report(store, b, 'benchmark', 3, cost=0.1))
    store.evaluate(b, report(store, b, 'review'))
    with pytest.raises(ValueError, match='improvement'):
        store.select(b, approval(store, b))


def test_blocking_policy_findings_cannot_be_ranked(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    a = store.propose(proposal('Bypass approval'))
    data = report(store, a)
    data['policy_preserved'] = False
    store.evaluate(a, data)
    assert store.rank(a) == []


def test_archive_records_cannot_be_rewritten(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    candidate = store.propose(proposal('Baseline'))
    with store.connect() as db, pytest.raises(sqlite3.IntegrityError, match='append-only'):
        db.execute('DELETE FROM candidates WHERE id=?', (candidate,))


def test_nonfinite_measurements_are_rejected(tmp_path):
    store = ImprovementStore(tmp_path / 'search.db')
    candidate = store.propose(proposal('Baseline'))
    data = report(store, candidate)
    data['cost_usd'] = float('nan')
    with pytest.raises(ValueError, match='Finite'):
        store.evaluate(candidate, data)
