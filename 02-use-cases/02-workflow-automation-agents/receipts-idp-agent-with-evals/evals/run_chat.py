"""Run the scripted chat conversations through the chat assistant and save their traces.

One process, one local gateway seeded with a user and their expenses. Each conversation is
one session: every turn calls the agent's query path with the same session id, so the
agent carries the earlier turns, exactly as the deployed REPL does with one Runtime
session. Each turn runs under its own root span, so a conversation is one session made of
several traces, which is what the session-level evaluators in score_chat.py read.

It calls `_answer_query` directly, as run_dataset.py calls `_process`, so no signed
identity token is needed locally. The token check is covered by the agent's own tests.

Usage:
    python run_chat.py
    python run_chat.py --only trip_context,held_explained
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent / "app" / "receiptsagent"

DEPLOYED_ONLY_ENV = (
    "AGENTCORE_GATEWAY_RECEIPTSGATEWAY_URL",
    "AGENTCORE_GATEWAY_TOKEN_ENDPOINT",
    "AGENTCORE_GATEWAY_CLIENT_ID",
    "AGENTCORE_GATEWAY_CLIENT_SECRET",
    "APPCONFIG_APPLICATION",
    "APPCONFIG_ENVIRONMENT",
    "APPCONFIG_PROFILE",
    "MEMORY_RECEIPTSAGENTMEMORY_ID",
    "AGENTCORE_MEMORY_ID",
    "RUN_EVENT_BUS",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--model", help="Override AGENT_MODEL_ID")
    parser.add_argument("--only", help="Comma-separated conversation ids, for a partial run")
    parser.add_argument("--conversations", type=Path, default=HERE / "fixtures" / "conversations.json")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = json.loads(args.conversations.read_text())
    user = spec["user"]
    wanted = set(args.only.split(",")) if args.only else None
    conversations = [c for c in spec["conversations"] if wanted is None or c["id"] in wanted]

    sys.path.insert(0, str(HERE))
    import local_gateway

    local_gateway.seed(
        [user],
        [
            {
                **row,
                "userId": user["userId"],
                "expenseId": local_gateway._expense_id(
                    user["userId"], row["merchant"], row["transactionDate"], row["total"]
                ),
            }
            for row in spec["expenses"]
        ],
    )
    gateway_url = local_gateway.start_in_background()

    for name in DEPLOYED_ONLY_ENV:
        os.environ.pop(name, None)
    os.environ["AGENTCORE_GATEWAY_URL"] = gateway_url
    os.environ["AWS_REGION"] = args.region
    os.environ["AWS_DEFAULT_REGION"] = args.region
    if args.model:
        os.environ["AGENT_MODEL_ID"] = args.model

    from bedrock_agentcore.evaluation.span_to_adot_serializer import convert_strands_to_adot
    from opentelemetry import trace
    from opentelemetry.sdk.trace import SpanProcessor
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from strands.telemetry import StrandsTelemetry

    session_id = {"value": ""}

    class SessionIdProcessor(SpanProcessor):
        def on_start(self, span, parent_context=None) -> None:
            span.set_attribute("session.id", session_id["value"])

    exporter = InMemorySpanExporter()
    telemetry = StrandsTelemetry()
    telemetry.tracer_provider.add_span_processor(SessionIdProcessor())
    telemetry.tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    sys.path.insert(0, str(AGENT_DIR))
    import main as receipts_agent

    run_dir = args.out / f"chat-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    tracer = trace.get_tracer("receipts-evals")
    print(f"Run {run_dir.name}, {len(conversations)} conversations, model {os.environ.get('AGENT_MODEL_ID', 'default')}\n")

    for conversation in conversations:
        session_id["value"] = f"chat-{conversation['id']}-{uuid.uuid4().hex[:12]}"
        exporter.clear()
        transcript = []
        print(f"== {conversation['id']}")
        for text in conversation["turns"]:
            with tracer.start_as_current_span("chat.turn"):
                try:
                    result = receipts_agent._answer_query(user["userId"], text, session_id=session_id["value"])
                    answer = result.get("answer", "")
                except Exception as exc:  # noqa: BLE001 — record it and keep going through the set
                    answer = f"[error] {exc}"
            transcript.append({"user": text, "agent": answer})
            print(f"  you>   {text}")
            print(f"  agent> {answer.strip()[:300]}\n")
        telemetry.tracer_provider.force_flush()
        spans = convert_strands_to_adot(list(exporter.get_finished_spans()))

        case_dir = run_dir / conversation["id"]
        case_dir.mkdir(exist_ok=True)
        (case_dir / "adot.json").write_text(json.dumps(spans, indent=2, default=str))
        (case_dir / "transcript.json").write_text(
            json.dumps({"session_id": session_id["value"], "conversation": conversation, "transcript": transcript}, indent=2)
        )

    print(f"Written to {run_dir}")


if __name__ == "__main__":
    main()
