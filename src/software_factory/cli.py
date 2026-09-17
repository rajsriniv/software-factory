from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .config import load_factory
from .governance import decide
from .ledger import Ledger
from .models import Decision, Message, Option, Vote


def main() -> None:
    parser = argparse.ArgumentParser(prog="software-factory")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-config")
    validate.add_argument("config", type=Path)
    ledger = sub.add_parser("verify-ledger")
    ledger.add_argument("database", type=Path)
    vote = sub.add_parser("decide")
    vote.add_argument("decision", type=Path)
    vote.add_argument("--ledger", type=Path, required=True)
    send = sub.add_parser("send")
    send.add_argument("--ledger", type=Path, required=True)
    send.add_argument("--sender", required=True)
    send.add_argument("--recipient", required=True)
    send.add_argument("--kind", required=True)
    send.add_argument("--correlation", required=True)
    send.add_argument("--payload", required=True, help="JSON object")
    inbox = sub.add_parser("inbox")
    inbox.add_argument("--ledger", type=Path, required=True)
    inbox.add_argument("--recipient", required=True)
    inbox.add_argument("--after", type=int, default=0)
    args = parser.parse_args()

    if args.command == "validate-config":
        config = load_factory(args.config)
        print(json.dumps({"valid": True, "factory": config["factory"]}))
        return
    if args.command == "verify-ledger":
        valid = Ledger(args.database).verify()
        print(json.dumps({"valid": valid}))
        raise SystemExit(0 if valid else 2)
    if args.command == "send":
        payload = json.loads(args.payload)
        if not isinstance(payload, dict):
            parser.error("--payload must be a JSON object")
        message = Message(
            uuid4().hex, args.correlation, args.sender, args.recipient,
            args.kind, payload, datetime.now(UTC).isoformat(),
        )
        event_hash = Ledger(args.ledger).message(message)
        print(json.dumps({"message_id": message.message_id, "event_hash": event_hash}))
        return
    if args.command == "inbox":
        print(json.dumps(Ledger(args.ledger).inbox(args.recipient, args.after), indent=2))
        return
    raw = json.loads(args.decision.read_text())
    decision = Decision(
        decision_id=raw.get("decision_id", uuid4().hex),
        question=raw["question"],
        eligible_voters=tuple(raw["eligible_voters"]),
        options=tuple(Option(**option) for option in raw["options"]),
        votes=[Vote(**vote) for vote in raw["votes"]],
    )
    result = decide(decision, mandatory_gates_passed=bool(raw["mandatory_gates_passed"]))
    created = datetime.now(UTC).isoformat()
    Ledger(args.ledger).decision(result, created)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
