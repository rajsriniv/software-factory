"""Offline, governed selection of prompt/workflow overlays; never edits live agents."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class ImprovementStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS candidates (
                  id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluations (
                  candidate TEXT, phase TEXT, body TEXT,
                  PRIMARY KEY(candidate,phase));
                CREATE TABLE IF NOT EXISTS comparisons (
                  pair TEXT PRIMARY KEY, body TEXT);
                CREATE TABLE IF NOT EXISTS selections (
                  sequence INTEGER PRIMARY KEY, body TEXT);
            ''')
            for table in ('candidates', 'evaluations', 'comparisons', 'selections'):
                for operation in ('UPDATE', 'DELETE'):
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} "
                               f"BEFORE {operation} ON {table} BEGIN "
                               "SELECT RAISE(ABORT, 'archive is append-only'); END;")

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def candidate(self, candidate_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute('SELECT body FROM candidates WHERE id=?', (candidate_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown candidate')
        result: dict[str, Any] = json.loads(row[0])
        if result['content_sha256'] != digest(result['content']):
            raise ValueError('Candidate integrity failure')
        return result

    def propose(self, data: dict[str, Any]) -> str:
        required = {'kind', 'target', 'content', 'author', 'rationale', 'parent',
                    'baseline_revision', 'policy_sha256', 'evaluation_plan_sha256'}
        if set(data) != required:
            raise ValueError('Candidate fields must exactly match the proposal contract')
        if data['kind'] not in {'prompt', 'workflow'}:
            raise ValueError('Only prompt/workflow overlays are supported')
        if any(not isinstance(data[k], str) or not data[k].strip() for k in required - {'parent'}):
            raise ValueError('Nonempty proposal fields required')
        if not isinstance(data['parent'], str):
            raise TypeError('Parent must be an ID or empty string for baseline')
        for key in ('policy_sha256', 'evaluation_plan_sha256'):
            if len(data[key]) != 64 or any(c not in '0123456789abcdef' for c in data[key]):
                raise ValueError('Expected exact policy and evaluation plan SHA256')
        if len(data['content']) > 20000:
            raise ValueError('Overlay exceeds 20000 characters')
        if data['parent']:
            parent = self.candidate(data['parent'])
            for key in ('kind', 'target', 'baseline_revision', 'policy_sha256', 'evaluation_plan_sha256'):
                if parent[key] != data[key]:
                    raise ValueError('Child must retain parent evaluation scope')
        body = dict(data, content_sha256=digest(data['content']))
        candidate_id = digest(json.dumps(body, sort_keys=True))
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?)',
                       (candidate_id, json.dumps(body, sort_keys=True)))
        return candidate_id

    def evaluate(self, candidate_id: str, data: dict[str, Any]) -> None:
        candidate = self.candidate(candidate_id)
        required = {'phase', 'candidate_sha256', 'evaluation_plan_sha256', 'policy_sha256',
                    'passed', 'total', 'cost_usd', 'tokens', 'seconds', 'evidence',
                    'evaluator', 'model', 'blocking_findings', 'policy_preserved'}
        if set(data) != required or data['phase'] not in {'smoke', 'benchmark', 'review'}:
            raise ValueError('Invalid evaluation contract')
        for key in ('evaluation_plan_sha256', 'policy_sha256'):
            if data[key] != candidate[key]:
                raise ValueError('Stale or incompatible evaluation scope')
        if data['candidate_sha256'] != candidate['content_sha256']:
            raise ValueError('Stale candidate evidence')
        for key in ('passed', 'total', 'tokens'):
            if type(data[key]) is not int or data[key] < 0:
                raise ValueError('Counts must be nonnegative integers')
        if data['total'] == 0 or data['passed'] > data['total']:
            raise ValueError('Meaningful evaluation counts required')
        for key in ('cost_usd', 'seconds'):
            if type(data[key]) not in (int, float) or not math.isfinite(data[key]) or data[key] < 0:
                raise ValueError('Finite nonnegative cost/time required')
        if (not isinstance(data['evidence'], list) or not data['evidence']
                or any(not isinstance(e, str) or not e.strip() for e in data['evidence'])):
            raise ValueError('Evidence references required')
        if (not isinstance(data['blocking_findings'], list)
                or type(data['policy_preserved']) is not bool):
            raise ValueError('Explicit policy and blocker assessment required')
        if any(not isinstance(data[k], str) or not data[k].strip() for k in ('evaluator', 'model')):
            raise ValueError('Evaluator and resolved model receipt required')
        if data['phase'] == 'review' and data['evaluator'] == candidate['author']:
            raise ValueError('Author cannot independently review own candidate')
        with self.connect() as db:
            db.execute('INSERT INTO evaluations VALUES (?,?,?)',
                       (candidate_id, data['phase'], json.dumps(data, sort_keys=True)))

    def evaluation(self, candidate_id: str, phase: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute('SELECT body FROM evaluations WHERE candidate=? AND phase=?',
                             (candidate_id, phase)).fetchone()
        if row is None:
            raise ValueError(f'Missing {phase} evidence')
        result: dict[str, Any] = json.loads(row[0])
        return result

    def eligible(self, candidate_id: str) -> bool:
        try:
            result = self.evaluation(candidate_id, 'smoke')
        except ValueError:
            return False
        return (result['passed'] == result['total'] and result['policy_preserved']
                and not result['blocking_findings'])

    def compare(self, left: str, right: str, winner: str, judge: str,
                model: str, rationale: str, evidence: str) -> None:
        if left == right or winner not in {left, right, 'tie'}:
            raise ValueError('Invalid comparison')
        a, b = self.candidate(left), self.candidate(right)
        if not all(self.eligible(c) for c in (left, right)):
            raise ValueError('Both candidates must pass smoke/policy checks')
        for key in ('kind', 'target', 'baseline_revision', 'policy_sha256', 'evaluation_plan_sha256'):
            if a[key] != b[key]:
                raise ValueError('Cannot compare incompatible scopes')
        if judge in {a['author'], b['author']} or not all((judge, model, rationale, evidence)):
            raise ValueError('Independent judge, model and rationale/evidence required')
        body = {'left': left, 'right': right, 'winner': winner, 'judge': judge,
                    'model': model, 'rationale': rationale, 'evidence': evidence}
        pair = digest('|'.join(sorted((left, right))))
        with self.connect() as db:
            db.execute('INSERT INTO comparisons VALUES (?,?)', (pair, json.dumps(body)))

    def rank(self, scope: str) -> list[dict[str, Any]]:
        anchor = self.candidate(scope)
        with self.connect() as db:
            ids = [row[0] for row in db.execute('SELECT id FROM candidates ORDER BY id')]
            comparisons = [json.loads(row[0]) for row in db.execute('SELECT body FROM comparisons')]
        keys = ('kind', 'target', 'baseline_revision', 'policy_sha256', 'evaluation_plan_sha256')
        ids = [c for c in ids if all(self.candidate(c)[k] == anchor[k] for k in keys)
               and self.eligible(c)]
        strengths = dict.fromkeys(ids, 1.0)
        wins = dict.fromkeys(ids, 1.0)  # symmetric pseudo-comparisons against fixed strength 1
        pairs = [p for p in comparisons if p['left'] in strengths and p['right'] in strengths]
        for p in pairs:
            if p['winner'] == 'tie':
                wins[p['left']] += 0.5
                wins[p['right']] += 0.5
            else:
                wins[p['winner']] += 1
        for _ in range(200):
            denominators = {c: 2 / (strengths[c] + 1) for c in ids}
            for p in pairs:
                value = 1 / (strengths[p['left']] + strengths[p['right']])
                denominators[p['left']] += value
                denominators[p['right']] += value
            strengths = {c: wins[c] / denominators[c] for c in ids}
        return [{'candidate': c, 'strength': strengths[c],
                     'comparisons': sum(c in (p['left'], p['right']) for p in pairs),
                     'purpose': 'evaluation-priority-only'}
                for c in sorted(ids, key=lambda c: (-strengths[c], c))]

    def assessment_hash(self, candidate_id: str) -> str:
        candidate = self.candidate(candidate_id)
        body = {phase: self.evaluation(candidate_id, phase)
                for phase in ('smoke', 'benchmark', 'review')}
        body['baseline'] = self.evaluation(candidate['parent'], 'benchmark')
        return digest(json.dumps(body, sort_keys=True))

    def select(self, candidate_id: str, approval: dict[str, Any]) -> None:
        candidate = self.candidate(candidate_id)
        parent_id = candidate['parent']
        if not parent_id or not self.eligible(candidate_id):
            raise ValueError('Promotion requires evaluated parent and successful smoke checks')
        result = self.evaluation(candidate_id, 'benchmark')
        parent = self.evaluation(parent_id, 'benchmark')
        review = self.evaluation(candidate_id, 'review')
        if (result['blocking_findings'] or not result['policy_preserved']
                or review['blocking_findings'] or not review['policy_preserved']
                or review['passed'] != review['total']):
            raise ValueError('Independent review or policy gate failed')
        new_rate, old_rate = result['passed'] / result['total'], parent['passed'] / parent['total']
        if (result['total'] != parent['total'] or new_rate < old_rate
                or not (new_rate > old_rate or result['cost_usd'] < parent['cost_usd'])):
            raise ValueError('No measured success/cost improvement over comparable baseline')
        expected = {'candidate', 'candidate_sha256', 'policy_sha256', 'evaluation_plan_sha256',
                    'reviewer', 'evidence', 'decision', 'assessment_sha256'}
        if (set(approval) != expected or approval['decision'] != 'approve'
                or approval['candidate'] != candidate_id
                or approval['candidate_sha256'] != candidate['content_sha256']
                or approval['assessment_sha256'] != self.assessment_hash(candidate_id)
                or any(approval[k] != candidate[k] for k in ('policy_sha256', 'evaluation_plan_sha256'))
                or any(not isinstance(approval[k], str) or not approval[k].strip()
                       for k in ('reviewer', 'evidence'))
                or approval['reviewer'] == candidate['author']):
            raise ValueError('Exact human approval evidence required')
        with self.connect() as db:
            db.execute('INSERT INTO selections(body) VALUES (?)', (json.dumps(approval),))
        # Selection is a proposal for adoption. No live files or agent settings are changed.
