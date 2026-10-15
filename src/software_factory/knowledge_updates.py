"""Reviewable, human-approved knowledge handoffs with transactional publication."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .brain import CompanyBrain


def fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class KnowledgeUpdates:
    def __init__(self, database: Path):
        self.brain = CompanyBrain(database)
        with self.brain.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS knowledge_updates (
                    id TEXT PRIMARY KEY, body TEXT, state TEXT, review TEXT, approval TEXT,
                    published_revision INTEGER, index_error TEXT);
                CREATE TABLE IF NOT EXISTS knowledge_update_events (
                    sequence INTEGER PRIMARY KEY, proposal TEXT, kind TEXT, body TEXT,
                    created_at TEXT);
                CREATE TRIGGER IF NOT EXISTS knowledge_events_no_update
                BEFORE UPDATE ON knowledge_update_events BEGIN
                    SELECT RAISE(ABORT, 'events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS knowledge_events_no_delete
                BEFORE DELETE ON knowledge_update_events BEGIN
                    SELECT RAISE(ABORT, 'events are append-only'); END;
            ''')

    @staticmethod
    def validate(data: dict[str, Any]) -> None:
        fields = {'company', 'source', 'content', 'owner', 'expires', 'roles',
                  'task_id', 'repository_revision', 'author', 'evidence'}
        if set(data) != fields:
            raise ValueError('Proposal must contain exactly the documented fields')
        for key in fields - {'roles', 'evidence'}:
            if not isinstance(data[key], str) or not data[key].strip():
                raise ValueError('Nonempty document and provenance fields required')
        if (not isinstance(data['roles'], list) or not data['roles']
                or any(not isinstance(r, str) or not re.fullmatch(r'[a-z][a-z0-9-]*', r)
                       for r in data['roles'])):
            raise ValueError('Explicit recipient roles required')
        if (not isinstance(data['evidence'], list) or not data['evidence']
                or any(not isinstance(e, str) or not e.strip() for e in data['evidence'])):
            raise ValueError('Source evidence references required')
        expiry = datetime.fromisoformat(data['expires'])
        if expiry.tzinfo is None or expiry <= datetime.now(UTC):
            raise ValueError('Expiry must be future and timezone-aware')

    @staticmethod
    def event(db: Any, proposal: str, kind: str, body: dict[str, Any]) -> None:
        db.execute('INSERT INTO knowledge_update_events(proposal,kind,body,created_at) VALUES (?,?,?,?)',
                   (proposal, kind, json.dumps(body, sort_keys=True), datetime.now(UTC).isoformat()))

    def propose(self, data: dict[str, Any]) -> str:
        self.validate(data)
        body = dict(data)
        body['roles'] = sorted(set(data['roles']))
        with self.brain.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            body['base_revision'] = db.execute(
                'SELECT COALESCE(MAX(revision),0) FROM knowledge WHERE company=? AND source=?',
                (body['company'], body['source']),
            ).fetchone()[0]
            proposal = fingerprint(body)
            db.execute('INSERT INTO knowledge_updates(id,body,state) VALUES (?,?,?)',
                       (proposal, json.dumps(body, sort_keys=True), 'proposed'))
            self.event(db, proposal, 'knowledge-proposal', body)
        return proposal

    def inspect(self, proposal: str) -> dict[str, Any]:
        with self.brain.connect() as db:
            row = db.execute('SELECT body,state,review,approval,published_revision,index_error '
                             'FROM knowledge_updates WHERE id=?', (proposal,)).fetchone()
            if row is None:
                raise ValueError('Unknown proposal')
            body = json.loads(row[0])
            if fingerprint(body) != proposal:
                raise ValueError('Proposal integrity mismatch')
            previous = db.execute('SELECT content FROM knowledge WHERE company=? AND source=? '
                                  'AND revision=?', (body['company'], body['source'],
                                                     body['base_revision'])).fetchone()
        return {'proposal': proposal, 'document': body, 'previous_content': previous[0] if previous else '',
                'state': row[1], 'review': json.loads(row[2]) if row[2] else None,
                'approval': json.loads(row[3]) if row[3] else None,
                'published_revision': row[4], 'index_error': row[5]}

    def review(self, proposal: str, reviewer: str, evidence: str, passed: bool) -> None:
        item = self.inspect(proposal)
        if not reviewer.strip() or not evidence.strip() or reviewer == item['document']['author']:
            raise ValueError('Independent reviewer and evidence required')
        if type(passed) is not bool:
            raise ValueError('Review result must be boolean')
        review = {'reviewer': reviewer, 'evidence': evidence, 'passed': passed}
        with self.brain.connect() as db:
            result = db.execute('UPDATE knowledge_updates SET state=?,review=? WHERE id=? AND state=?',
                                ('reviewed' if passed else 'review-failed', json.dumps(review),
                                 proposal, 'proposed'))
            if result.rowcount != 1:
                raise ValueError('Review requires a new proposed document')
            self.event(db, proposal, 'knowledge-review', review)

    def approve(self, proposal: str, human: str, evidence: str, approved_hash: str) -> None:
        item = self.inspect(proposal)
        if (approved_hash != proposal or not human.strip() or not evidence.strip()
                or human == item['document']['author']):
            raise ValueError('Exact human approval and evidence required')
        approval = {'human': human, 'evidence': evidence, 'approved_hash': approved_hash,
                    'approved_at': datetime.now(UTC).isoformat()}
        with self.brain.connect() as db:
            result = db.execute('UPDATE knowledge_updates SET state=?,approval=? '
                                'WHERE id=? AND state=?',
                                ('approved', json.dumps(approval), proposal, 'reviewed'))
            if result.rowcount != 1:
                raise ValueError('Approval requires successful independent review')
            self.event(db, proposal, 'knowledge-approval', approval)

    def reject(self, proposal: str, actor: str, reason: str) -> None:
        if not actor.strip() or not reason.strip():
            raise ValueError('Rejection actor and reason required')
        with self.brain.connect() as db:
            result = db.execute("UPDATE knowledge_updates SET state='rejected' WHERE id=? "
                                "AND state IN ('proposed','reviewed','review-failed','approved')", (proposal,))
            if result.rowcount != 1:
                raise ValueError('Cannot reject unknown or already published proposal')
            self.event(db, proposal, 'knowledge-rejection', {'actor': actor, 'reason': reason})

    def publish(self, proposal: str, indexer: Callable[[str], Any]) -> dict[str, Any]:
        with self.brain.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body,state FROM knowledge_updates WHERE id=?', (proposal,)).fetchone()
            if not row or row[1] not in {'approved', 'index-pending', 'published'}:
                raise ValueError('Publication requires exact human-approved proposal')
            body = json.loads(row[0])
            if fingerprint(body) != proposal:
                raise ValueError('Proposal integrity mismatch')
            if row[1] == 'published':
                return self.inspect(proposal)
            if row[1] == 'approved':
                self.validate({k: v for k, v in body.items() if k != 'base_revision'})
                current = db.execute('SELECT COALESCE(MAX(revision),0) FROM knowledge '
                                     'WHERE company=? AND source=?',
                                     (body['company'], body['source'])).fetchone()[0]
                if current != body['base_revision']:
                    raise ValueError('Source changed since proposal; create and approve a new proposal')
                revision = current + 1
                sha = hashlib.sha256(body['content'].encode()).hexdigest()
                expiry = datetime.fromisoformat(body['expires']).astimezone(UTC).isoformat()
                db.execute('INSERT INTO knowledge VALUES (?,?,?,?,?,?,?,?)',
                           (body['company'], body['source'], revision, sha, body['content'],
                            body['owner'], expiry, ','.join(body['roles'])))
                db.execute("UPDATE knowledge_updates SET state='index-pending',published_revision=? WHERE id=?",
                           (revision, proposal))
                self.event(db, proposal, 'knowledge-imported', {'revision': revision, 'sha256': sha})
        try:
            indexer(body['company'])
        except Exception as exc:
            with self.brain.connect() as db:
                db.execute('UPDATE knowledge_updates SET index_error=? WHERE id=?', (type(exc).__name__, proposal))
                self.event(db, proposal, 'knowledge-index-failed', {'error_type': type(exc).__name__})
            raise ValueError('Approved document imported; indexing failed. Retry publish without reimporting.') from exc
        with self.brain.connect() as db:
            db.execute("UPDATE knowledge_updates SET state='published',index_error=NULL WHERE id=?", (proposal,))
            self.event(db, proposal, 'knowledge-published', {'index_refreshed': True})
        return self.inspect(proposal)

    def events(self, task_id: str | None = None) -> list[dict[str, Any]]:
        with self.brain.connect() as db:
            rows = db.execute('SELECT e.sequence,e.proposal,e.kind,e.body,e.created_at '
                              'FROM knowledge_update_events e JOIN knowledge_updates u ON u.id=e.proposal '
                              'WHERE ? IS NULL OR json_extract(u.body,\'$.task_id\')=? ORDER BY e.sequence',
                              (task_id, task_id)).fetchall()
        return [{'sequence': r[0], 'proposal': r[1], 'kind': r[2], 'payload': json.loads(r[3]),
                 'created_at': r[4], 'channel': 'factory-knowledge'} for r in rows]
