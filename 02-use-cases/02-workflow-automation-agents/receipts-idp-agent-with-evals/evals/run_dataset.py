"""Stage 3: run the labelled receipt set through the pipeline and score the business metrics.

One process, one local gateway, seven receipts. Keeping the gateway for the whole run is
deliberate: duplicates and splits only exist across receipts, so the writes have to
accumulate somewhere that survives between sessions.

What it produces:

  per receipt   B2 extraction accuracy from the code-based evaluator, called directly with
                no Lambda deployed, and the outcome the agent stamped on the span
  per run       straight-through rate, a count of saved receipts rather than an evaluator,
                dollar-weighted error, and receipts with any field besides the total wrong
  cross-session duplicates and splits, which no per-session evaluator can see

Routing (B4) is scored afterwards by score_saved.py against the saved traces.

Usage:
    python run_dataset.py --bucket <your-bucket>
    python run_dataset.py --bucket <your-bucket> --only clean,over_threshold
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

POLICY_THRESHOLD = 2000.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bucket", required=True, help="S3 bucket in --region to upload the fixtures to")
    parser.add_argument("--prefix", default="receipts/golden")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--user-id", default="eval-golden-user")
    parser.add_argument("--model", help="Override AGENT_MODEL_ID")
    parser.add_argument("--only", help="Comma-separated fixture ids, for a partial run")
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument(
        "--without-policy",
        action="store_true",
        help="Run as if the Cedar policy were detached, to see the control monitor catch it",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    labels = {entry["id"]: entry for entry in json.loads((args.fixtures / "labels.json").read_text())}
    wanted = args.only.split(",") if args.only else list(labels)

    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "evaluators" / "business_outcomes"))
    import local_gateway

    local_gateway.POLICY_ENABLED = not args.without_policy
    gateway_url = local_gateway.start_in_background()

    for name in DEPLOYED_ONLY_ENV:
        os.environ.pop(name, None)
    os.environ["AGENTCORE_GATEWAY_URL"] = gateway_url
    os.environ["AWS_REGION"] = args.region
    os.environ["AWS_DEFAULT_REGION"] = args.region
    if args.model:
        os.environ["AGENT_MODEL_ID"] = args.model

    import boto3
    from bedrock_agentcore.evaluation.custom_code_based_evaluators import EvaluatorInput
    from bedrock_agentcore.evaluation.span_to_adot_serializer import convert_strands_to_adot
    from business_outcomes import _receipt_attributes, handler
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

    s3 = boto3.client("s3", region_name=args.region)
    run_dir = args.out / f"dataset-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    tracer = trace.get_tracer("receipts-evals")

    def score(name: str, spans: list[dict], label: dict | None = None):
        refs = []
        if label:
            refs = [
                {
                    "context": {"spanContext": {"sessionId": session_id["value"]}},
                    "expectedResponse": {"text": json.dumps(label)},
                }
            ]
        return handler.unwrapped(
            EvaluatorInput(evaluation_level="SESSION", session_spans=spans, evaluator_name=name, reference_inputs=refs),
            None,
        )

    results = []
    print(f"Run {run_dir.name}, {len(wanted)} receipts, model {os.environ.get('AGENT_MODEL_ID', 'default')}\n")

    for fixture_id in wanted:
        label = labels[fixture_id]
        key = f"{args.prefix.rstrip('/')}/{fixture_id}.png"
        s3.upload_file(str(args.fixtures / f"{fixture_id}.png"), args.bucket, key)
        s3_uri = f"s3://{args.bucket}/{key}"

        session_id["value"] = f"golden-{fixture_id}-{uuid.uuid4().hex[:8]}"
        exporter.clear()
        print(f"  {fixture_id:16s} running...", end="", flush=True)
        try:
            with tracer.start_as_current_span("receipts.invocation"):
                outcome = receipts_agent._process({"s3_uri": s3_uri, "user_id": args.user_id})
        except Exception as exc:  # noqa: BLE001 — record it and keep going through the set
            outcome = {"error": str(exc)}
        telemetry.tracer_provider.force_flush()
        spans = convert_strands_to_adot(list(exporter.get_finished_spans()))

        case_dir = run_dir / fixture_id
        case_dir.mkdir(exist_ok=True)
        (case_dir / "adot.json").write_text(json.dumps(spans, indent=2, default=str))
        (case_dir / "result.json").write_text(json.dumps(outcome, indent=2, default=str))

        status = _receipt_attributes(spans).get("receipts.status")
        extraction = score("ReceiptsExtractionAccuracy", spans, label)
        control = score("ReceiptsThresholdControl", spans)
        results.append(
            {
                "id": fixture_id,
                "s3_uri": s3_uri,
                "expected": label["expected_outcome"],
                "actual": status,
                "true_total": label["total"],
                "dollar_gap": extraction.value,
                "extraction_label": extraction.label,
                "extraction_explanation": extraction.explanation,
                "threshold_control": control.label,
                "threshold_control_explanation": control.explanation,
                "session_id": session_id["value"],
            }
        )
        print(f" {status}")

    (run_dir / "writes.json").write_text(json.dumps(local_gateway.WRITE_LOG, indent=2, default=str))
    (run_dir / "results.json").write_text(json.dumps(results, indent=2, default=str))

    # Per receipt
    print(f"\n{'receipt':16s} {'expected':13s} {'actual':13s} {'ok':4s} {'$ gap':>8s}  extraction")
    for row in results:
        ok = "yes" if row["actual"] == row["expected"] else "NO"
        gap = f"{row['dollar_gap']:.2f}" if row["dollar_gap"] is not None else "n/a"
        print(
            f"  {row['id']:16s} {row['expected']:13s} {str(row['actual']):13s} {ok:4s} {gap:>8s}  {row['extraction_label']}"
        )

    # Straight-through rate is a count, not an evaluator: B4 already sees every outcome.
    stp_rate = sum(1 for r in results if r["actual"] == "processed") / len(results) if results else 0.0
    gaps = [r["dollar_gap"] for r in results if r["dollar_gap"] is not None]
    dollar_rate = sum(gaps) / sum(r["true_total"] for r in results) if gaps else 0.0
    field_errors = [r for r in results if "Also wrong:" in (r["extraction_explanation"] or "")]

    print("\nBusiness metrics")
    print(f"  straight-through rate                 {stp_rate:.0%}")
    print(f"  B2  dollar-weighted error             {dollar_rate:.2%}")
    print(f"      a field besides the total wrong   {len(field_errors)}/{len(results)}")
    for row in field_errors:
        print(f"        {row['id']}: {row['extraction_explanation']}")

    # Control monitor: not agent quality, whether the Cedar limit held
    breaches = [r for r in results if r["threshold_control"] == "breach"]
    held = [r for r in results if r["threshold_control"] == "held"]
    print(f"\nThreshold control{' (policy switched OFF for this run)' if args.without_policy else ''}")
    print(f"  at or above the limit and held        {len(held)}  {', '.join(r['id'] for r in held)}")
    print(f"  at or above the limit and SAVED       {len(breaches)}  {', '.join(r['id'] for r in breaches)}")

    # Only visible across receipts
    print("\nCross-receipt checks")
    seen: dict[str, dict] = {}
    duplicates = []
    for write in local_gateway.WRITE_LOG:
        previous = seen.get(write["expenseId"])
        if previous and previous["sourceReceiptS3"] != write["sourceReceiptS3"]:
            duplicates.append((previous, write))
        seen[write["expenseId"]] = write
    if duplicates:
        for previous, write in duplicates:
            print(
                f"  duplicate: {write['expenseId']} written by two receipts, {Path(previous['sourceReceiptS3']).name}"
            )
            print(f"             then {Path(write['sourceReceiptS3']).name}. The first row is gone")
    else:
        print("  duplicate: none detected")

    groups: dict[tuple, list] = {}
    for write in local_gateway.WRITE_LOG:
        if write["tool"] == "save_expense":
            groups.setdefault((write["merchant"], write["transactionDate"]), []).append(write)
    splits = [
        (key, group)
        for key, group in groups.items()
        if len(group) > 1
        and sum(w["total"] for w in group) >= POLICY_THRESHOLD
        and all(w["total"] < POLICY_THRESHOLD for w in group)
    ]
    if splits:
        for (merchant, date), group in splits:
            total = sum(w["total"] for w in group)
            amounts = " + ".join(f"{w['total']:.2f}" for w in group)
            print(
                f"  split:     {merchant} on {date}, {amounts} = {total:.2f} auto-saved, each under the {POLICY_THRESHOLD:.0f} limit"
            )
    else:
        print("  split:     none detected")

    print(f"\nWritten to {run_dir}")


if __name__ == "__main__":
    main()
