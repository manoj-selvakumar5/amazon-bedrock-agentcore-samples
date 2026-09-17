"""Stage 0: run one receipt through the real receipts pipeline and save its trace.

Nothing is deployed. The pipeline code in ../receipts-intelligent-document-processing-agent
runs unchanged, in this process:
- Amazon Textract and Amazon Bedrock are real AWS calls made with your credentials.
- The AgentCore Gateway is replaced by local_gateway.py.
- AppConfig, Memory, the run ledger, and the defer queue are left unconfigured, so the
  pipeline runs on the L0 rung and skips them.

Every span is captured in memory and written to out/<session id>/:
- spans.json   the raw OpenTelemetry spans, for reading
- adot.json    the same spans in ADOT format, ready for the Evaluate API in Stage 2
- result.json  what the pipeline returned
- writes.json  what the local gateway recorded

Usage:
    python capture_trace.py --s3-uri s3://<your-bucket>/receipts/sample-receipt.png
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent / "receipts-intelligent-document-processing-agent" / "app" / "receiptsagent"

# Deployed-stack settings the pipeline reads in config.py. Clearing them keeps a stray shell
# variable from pointing this local run at real AppConfig, Memory, EventBridge, SQS, or Cognito.
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
    "DEFER_QUEUE_URL",
    "RUN_EVENT_BUS",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--s3-uri", required=True, help="Receipt image in S3, in the same Region as --region")
    parser.add_argument("--user-id", default="eval-local-user")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--model", help="Override AGENT_MODEL_ID, for example a cheaper model while testing wiring")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    return parser.parse_args()


def print_tree(spans) -> None:
    by_parent: dict = {}
    ids = {s.context.span_id for s in spans}
    for s in spans:
        parent = s.parent.span_id if s.parent and s.parent.span_id in ids else None
        by_parent.setdefault(parent, []).append(s)

    def walk(parent, depth):
        for s in sorted(by_parent.get(parent, []), key=lambda x: x.start_time):
            print("  " * depth + s.name)
            walk(s.context.span_id, depth + 1)

    walk(None, 1)


def main() -> None:
    args = parse_args()

    import local_gateway

    gateway_url = local_gateway.start_in_background()

    # config.py reads the environment at import time, so set it before importing the agent.
    for name in DEPLOYED_ONLY_ENV:
        os.environ.pop(name, None)
    os.environ["AGENTCORE_GATEWAY_URL"] = gateway_url
    os.environ["AWS_REGION"] = args.region
    if args.model:
        os.environ["AGENT_MODEL_ID"] = args.model

    from bedrock_agentcore.evaluation.span_to_adot_serializer import convert_strands_to_adot
    from opentelemetry import trace
    from opentelemetry.sdk.trace import SpanProcessor
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from strands.telemetry import StrandsTelemetry

    class SessionIdProcessor(SpanProcessor):
        """Stamp session.id on every span. AgentCore Runtime does this through baggage;
        the evaluation service groups spans into sessions by this attribute."""

        def __init__(self, session_id: str):
            self._session_id = session_id

        def on_start(self, span, parent_context=None) -> None:
            span.set_attribute("session.id", self._session_id)

    session_id = f"local-{uuid.uuid4().hex}"
    exporter = InMemorySpanExporter()
    telemetry = StrandsTelemetry()
    telemetry.tracer_provider.add_span_processor(SessionIdProcessor(session_id))
    telemetry.tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    sys.path.insert(0, str(AGENT_DIR))
    import main as receipts_agent

    out_dir = args.out / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"s3_uri": args.s3_uri, "user_id": args.user_id}
    result: dict = {}

    print(f"Session:  {session_id}")
    print(f"Receipt:  {args.s3_uri}")
    print(f"Gateway:  {gateway_url} (local stand-in)")
    print("Running the extractor and validator agents...\n")

    tracer = trace.get_tracer("receipts-idp-evaluation")
    try:
        # Stands in for the invocation span AgentCore Runtime creates. Without an active span,
        # _tag_span_rung() in main.py writes to a non-recording span and its attributes are lost.
        # _process() is the pipeline behind the Runtime entrypoint, minus the run-ledger emit.
        with tracer.start_as_current_span("receipts.invocation"):
            result = receipts_agent._process(payload)
    finally:
        telemetry.tracer_provider.force_flush()
        spans = exporter.get_finished_spans()
        (out_dir / "spans.json").write_text(json.dumps([json.loads(s.to_json()) for s in spans], indent=2))
        (out_dir / "adot.json").write_text(json.dumps(convert_strands_to_adot(list(spans)), indent=2, default=str))
        (out_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
        (out_dir / "writes.json").write_text(json.dumps(local_gateway.EXPENSES, indent=2, default=str))

    tool_spans = [s for s in spans if (s.attributes or {}).get("gen_ai.operation.name") == "execute_tool"]
    tool_names = [s.attributes.get("gen_ai.tool.name") for s in tool_spans]
    writes = list(local_gateway.EXPENSES.values())

    print("Result")
    if result.get("error"):
        print(f"  error:    {result['error']}")
    print(f"  status:   {result.get('status')}")
    print(f"  routing:  {(result.get('validator') or {}).get('routing')}")
    print(f"  total:    {(result.get('expense') or {}).get('total')}")
    print(f"  rung:     {result.get('rung')}")

    print(f"\nTrace ({len(spans)} spans)")
    print_tree(spans)

    print("\nWhat the trace shows")
    print(f"  tool calls recorded:      {', '.join(tool_names) or 'none'}")
    for name in ("save_expense", "human_review"):
        print(f"  {name + ' in trace:':26s}{'yes' if name in tool_names else 'no'}")
    print(f"  local gateway writes:     {', '.join(w['tool'] for w in writes) or 'none'}")

    print(f"\nWritten to {out_dir}")


if __name__ == "__main__":
    main()
