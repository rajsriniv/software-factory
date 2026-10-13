from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .brain import CompanyBrain
from .config import load_factory
from .governance import decide
from .improvement import ImprovementStore
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
    send.add_argument("--channel", default="factory-general")
    send.add_argument("--sender", required=True)
    send.add_argument("--recipient", required=True)
    send.add_argument("--kind", required=True)
    send.add_argument("--correlation", required=True)
    send.add_argument("--payload", required=True, help="JSON object")
    inbox = sub.add_parser("inbox")
    inbox.add_argument("--ledger", type=Path, required=True)
    inbox.add_argument("--recipient", required=True)
    inbox.add_argument("--channel")
    inbox.add_argument("--after", type=int, default=0)
    ingest = sub.add_parser("brain-ingest")
    query = sub.add_parser("brain-query")
    index = sub.add_parser("brain-index")
    index.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    for command in (ingest, query, index):
        command.add_argument("--database", type=Path, required=True)
        command.add_argument("--company", required=True)
    ingest.add_argument("--source", required=True)
    ingest.add_argument("--file", type=Path, required=True)
    ingest.add_argument("--owner", required=True)
    ingest.add_argument("--expires", required=True)
    ingest.add_argument("--roles", nargs="+", required=True)
    query.add_argument("--mode", choices=("lexical", "vector", "hybrid"), default="lexical")
    query.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--min-similarity", type=float, default=0.35)
    query.add_argument("--role", required=True)
    query.add_argument("--question", required=True)
    query.add_argument("--max-chars", type=int, default=6000)
    improvement = sub.add_parser("improvement")
    improvement.add_argument("action", choices=("propose", "evaluate", "compare", "rank", "select", "inspect", "assessment"))
    improvement.add_argument("--database", type=Path, required=True)
    improvement.add_argument("--input", type=Path, help="JSON operation payload")
    improvement.add_argument("--candidate")
    args = parser.parse_args()
    if args.command == "improvement":
        store = ImprovementStore(args.database)
        data = json.loads(args.input.read_text()) if args.input else {}
        if args.action == "propose":
            print(json.dumps({"candidate": store.propose(data)}))
        elif args.action == "compare":
            store.compare(**data)
            print(json.dumps({"recorded": True}))
        else:
            if not args.candidate:
                parser.error("--candidate is required for this operation")
            if args.action == "assessment":
                print(json.dumps({"assessment_sha256": store.assessment_hash(args.candidate)}))
            elif args.action == "rank":
                print(json.dumps(store.rank(args.candidate), indent=2))
            elif args.action == "inspect":
                print(json.dumps(store.candidate(args.candidate), indent=2))
            elif args.action == "evaluate":
                store.evaluate(args.candidate, data)
                print(json.dumps({"recorded": True}))
            else:
                store.select(args.candidate, data)
                print(json.dumps({"selected": True, "live_agents_changed": False}))
        return
    if args.command == "brain-ingest":
        digest = CompanyBrain(args.database).ingest(
            args.company, args.source, args.file.read_text(), args.owner,
            args.expires, args.roles)
        print(json.dumps({"sha256": digest}))
        return
    if args.command == "brain-index" or (args.command == "brain-query" and args.mode != "lexical"):
        from .vector_brain import VectorBrain
        try:
            brain = VectorBrain(args.database, model=args.model)
            if args.command == "brain-index":
                print(json.dumps(brain.index(args.company), indent=2))
            else:
                print(json.dumps(brain.query(args.company, args.role, args.question,
                    args.max_chars, args.top_k, args.min_similarity, args.mode), indent=2))
        except ImportError:
            parser.error("Install vector support with pip install '.[brain]'")
        except ValueError as exc:
            parser.error(str(exc))
        return
    if args.command == "brain-query":
        print(json.dumps(CompanyBrain(args.database).query(
            args.company, args.role, args.question, args.max_chars), indent=2))
        return

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
            args.kind, payload, datetime.now(UTC).isoformat(), args.channel,
        )
        event_hash = Ledger(args.ledger).message(message)
        print(json.dumps({"message_id": message.message_id, "event_hash": event_hash}))
        return
    if args.command == "inbox":
        print(json.dumps(Ledger(args.ledger).inbox(args.recipient, args.after, args.channel), indent=2))
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
