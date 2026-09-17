from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .models import Decision, Message


class Ledger:
    """Append-only local communication and decision ledger."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")
            yield db
            db.commit()
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_id TEXT NOT NULL UNIQUE,
                  event_type TEXT NOT NULL,
                  correlation_id TEXT NOT NULL,
                  payload TEXT NOT NULL,
                  previous_hash TEXT,
                  event_hash TEXT NOT NULL UNIQUE,
                  created_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
                """
            )

    def append(self, event_id: str, event_type: str, correlation_id: str, payload: dict[str, object], created_at: str) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._db() as db:
            row = db.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
            previous = row[0] if row else "GENESIS"
            event_hash = hashlib.sha256(f"{previous}|{event_id}|{event_type}|{correlation_id}|{encoded}|{created_at}".encode()).hexdigest()
            db.execute(
                "INSERT INTO events(event_id,event_type,correlation_id,payload,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?)",
                (event_id, event_type, correlation_id, encoded, previous, event_hash, created_at),
            )
        return event_hash

    def message(self, message: Message) -> str:
        return self.append(message.message_id, "message", message.correlation_id, {
            "sender": message.sender, "recipient": message.recipient, "kind": message.kind, "payload": message.payload
        }, message.created_at)

    def inbox(self, recipient: str, after_sequence: int = 0) -> list[dict[str, object]]:
        with self._db() as db:
            rows = db.execute(
                "SELECT sequence,event_id,correlation_id,payload,created_at FROM events "
                "WHERE event_type='message' AND sequence>? ORDER BY sequence",
                (after_sequence,),
            ).fetchall()
        messages: list[dict[str, object]] = []
        for sequence, event_id, correlation_id, payload, created_at in rows:
            decoded = json.loads(payload)
            if decoded["recipient"] in {recipient, "*"}:
                messages.append({
                    "sequence": sequence, "message_id": event_id,
                    "correlation_id": correlation_id, "created_at": created_at, **decoded,
                })
        return messages

    def decision(self, decision: Decision, created_at: str) -> str:
        return self.append(decision.decision_id, "decision", decision.decision_id, decision.as_dict(), created_at)

    def verify(self) -> bool:
        previous = "GENESIS"
        with self._db() as db:
            rows = db.execute("SELECT event_id,event_type,correlation_id,payload,previous_hash,event_hash,created_at FROM events ORDER BY sequence").fetchall()
        for event_id, event_type, correlation_id, payload, stored_previous, stored_hash, created_at in rows:
            expected = hashlib.sha256(f"{previous}|{event_id}|{event_type}|{correlation_id}|{payload}|{created_at}".encode()).hexdigest()
            if stored_previous != previous or stored_hash != expected:
                return False
            previous = stored_hash
        return True
