import sqlite3
from datetime import UTC, datetime

import pytest

from software_factory.ledger import Ledger
from software_factory.models import Message


def test_hash_chain_and_append_only(tmp_path) -> None:
    path = tmp_path / "events.db"
    ledger = Ledger(path)
    ledger.append("1", "test", "c", {"answer": 42}, datetime.now(UTC).isoformat())
    ledger.append("2", "test", "c", {"answer": 43}, datetime.now(UTC).isoformat())
    assert ledger.verify()
    with sqlite3.connect(path) as db, pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("DELETE FROM events WHERE event_id='1'")


def test_direct_and_broadcast_messages_reach_inbox(tmp_path) -> None:
    ledger = Ledger(tmp_path / "events.db")
    now = datetime.now(UTC).isoformat()
    ledger.message(Message("m1", "c", "architect", "python", "task", {"id": "T1"}, now))
    ledger.message(Message("m2", "c", "security", "*", "finding", {"severity": "major"}, now))
    ledger.message(Message("m3", "c", "planner", "java", "task", {"id": "T2"}, now))
    assert [message["message_id"] for message in ledger.inbox("python")] == ["m1", "m2"]
