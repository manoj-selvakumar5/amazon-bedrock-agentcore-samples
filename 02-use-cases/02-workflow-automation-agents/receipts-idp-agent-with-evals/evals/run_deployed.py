"""Run the labelled receipts and the chat conversations through the DEPLOYED stack.

The local runners (run_dataset.py, run_chat.py) exercise the agent code on a laptop with
a stand-in Gateway. This one exercises what is actually deployed, end to end:

  receipts  each fixture is uploaded to the S3 inbox, which triggers the pipeline Runtime
            through EventBridge exactly as a real receipt would. The script waits for the
            run ledger to record the receipt's fate, finds its session in the spans, and
            collects the session's trace from CloudWatch
  chat      each conversation is one chat Runtime session, turn by turn, with a signed
            identity token for the seeded conversation user

Output is written in the same shape the local runners write, so the same scorers apply:

    python score_saved.py --run out/deployed-<id>        routing, right reason, invented values
    python score_chat.py  --run out/deployed-chat-<id>   completeness, retention, correctness

Extraction accuracy and the threshold control are scored here, as run_dataset.py does.
The cross-receipt duplicate check is not: it reads the local gateway's write log.

Usage:
    python run_deployed.py                   # receipts and chat
    python run_deployed.py --only receipts
    python run_deployed.py --only chat
"""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--stack", default="AgentCore-ReceiptsAgent-dev")
    parser.add_argument("--only", choices=["receipts", "chat"], help="Run one workload only")
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--timeout", type=int, default=900, help="Seconds to wait for all receipts to finish")
    return parser.parse_args()


def stack_outputs(cfn, stack: str) -> dict[str, str]:
    outs = cfn.describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", [])
    return {o["OutputKey"]: o["OutputValue"] for o in outs}


def output(outs: dict[str, str], exact: str, prefix: str | None = None) -> str:
    """An output by exact key, or by construct-prefixed key (InfraIdentityKeyId1529ABDE)."""
    if exact in outs:
        return outs[exact]
    for key, value in outs.items():
        if prefix and key.startswith(prefix):
            return value
    raise SystemExit(f"stack output {exact or prefix} not found")


def runtime_log_group(runtime_arn: str) -> str:
    return f"/aws/bedrock-agentcore/runtimes/{runtime_arn.rsplit('/', 1)[-1]}-DEFAULT"


def find_session_id(logs, s3_uri: str, start: datetime, end: datetime) -> str | None:
    """The pipeline session that processed this receipt, from the receipts.s3_uri span attribute."""
    query = (
        "fields attributes.session.id as sid"
        f'\n| filter attributes.receipts.s3_uri = "{s3_uri}"'
        "\n| filter ispresent(attributes.session.id)"
        "\n| limit 1"
    )
    qid = logs.start_query(
        logGroupName="aws/spans",
        startTime=int(start.timestamp()),
        endTime=int(end.timestamp()),
        queryString=query,
    )["queryId"]
    while True:
        res = logs.get_query_results(queryId=qid)
        if res["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
        time.sleep(2)
    for row in res.get("results", []):
        for field in row:
            if field["field"] == "sid":
                return field["value"]
    return None


def run_receipts(args, boto3, outs: dict[str, str], collector_cls) -> Path:
    sys.path.insert(0, str(ROOT / "app" / "receiptsagent"))
    sys.path.insert(0, str(ROOT / "evaluators" / "business_outcomes"))
    from bedrock_agentcore.evaluation.custom_code_based_evaluators import EvaluatorInput
    from business_outcomes import _receipt_attributes, handler
    from parsing import receipt_id

    region = args.region
    s3 = boto3.client("s3", region_name=region)
    logs = boto3.client("logs", region_name=region)
    runs = boto3.resource("dynamodb", region_name=region).Table("ReceiptsAgent-ProcessingRuns")
    bucket = output(outs, "", prefix="InfraInboxBucketName")
    collector = collector_cls(log_group_name=runtime_log_group(output(outs, "RuntimeArn")), region=region)

    labels = {entry["id"]: entry for entry in json.loads((args.fixtures / "labels.json").read_text())}
    run_tag = uuid.uuid4().hex[:8]
    run_dir = args.out / f"deployed-{run_tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    user = f"eval-deployed-{run_tag}"
    started = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Upload in fixture order: duplicate_b and split_b follow their first halves, as locally.
    uploaded = {}
    for fixture_id in labels:
        key = f"receipts/{user}/{fixture_id}.png"
        s3.upload_file(str(args.fixtures / f"{fixture_id}.png"), bucket, key)
        uploaded[fixture_id] = f"s3://{bucket}/{key}"
        print(f"  uploaded {fixture_id}")
        time.sleep(2)

    print(f"\nWaiting for the run ledger (up to {args.timeout}s)...")
    deadline = time.monotonic() + args.timeout
    fates: dict[str, dict] = {}
    while len(fates) < len(uploaded) and time.monotonic() < deadline:
        for fixture_id, uri in uploaded.items():
            if fixture_id not in fates:
                item = runs.get_item(Key={"receiptId": receipt_id(uri)}).get("Item")
                if item:
                    fates[fixture_id] = item
                    print(f"  {fixture_id:16s} {item.get('status')}")
        time.sleep(10)
    missing = sorted(set(uploaded) - set(fates))
    if missing:
        print(f"  no ledger row yet for: {', '.join(missing)}")

    def score(name: str, spans: list[dict], label: dict | None, session_id: str):
        refs = []
        if label:
            refs = [{"context": {"spanContext": {"sessionId": session_id}}, "expectedResponse": {"text": json.dumps(label)}}]
        return handler.unwrapped(
            EvaluatorInput(evaluation_level="SESSION", session_spans=spans, evaluator_name=name, reference_inputs=refs),
            None,
        )

    print("\nCollecting traces from CloudWatch...")
    ended = datetime.now(timezone.utc)
    results = []
    for fixture_id, uri in uploaded.items():
        label = labels[fixture_id]
        session_id = find_session_id(logs, uri, started, ended + timedelta(minutes=5))
        if not session_id:
            print(f"  {fixture_id:16s} no session found in aws/spans")
            continue
        spans = collector.collect(session_id, started, ended)
        case_dir = run_dir / fixture_id
        case_dir.mkdir(exist_ok=True)
        (case_dir / "adot.json").write_text(json.dumps(spans, indent=2, default=str))

        extraction = score("ReceiptsExtractionAccuracy", spans, label, session_id)
        control = score("ReceiptsThresholdControl", spans, None, session_id)
        results.append(
            {
                "id": fixture_id,
                "s3_uri": uri,
                "expected": label["expected_outcome"],
                "actual": _receipt_attributes(spans).get("receipts.status"),
                "ledger_status": (fates.get(fixture_id) or {}).get("status"),
                "true_total": label["total"],
                "dollar_gap": extraction.value,
                "extraction_label": extraction.label,
                "extraction_explanation": extraction.explanation,
                "threshold_control": control.label,
                "threshold_control_explanation": control.explanation,
                "session_id": session_id,
            }
        )
        print(f"  {fixture_id:16s} {len(spans):3d} spans  {results[-1]['actual']}  {extraction.label}  {control.label}")

    (run_dir / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nWritten to {run_dir}. Score with: python score_saved.py --run {run_dir}")
    return run_dir


def run_chat(args, boto3, outs: dict[str, str], collector_cls) -> Path:
    sys.path.insert(0, str(ROOT / "scripts"))
    from ask import ask

    region = args.region
    spec = json.loads((args.fixtures / "conversations.json").read_text())
    user = spec["user"]
    dynamodb = boto3.resource("dynamodb", region_name=region)

    # Seed the conversation user and their expenses, keyed as save_expense keys them.
    sys.path.insert(0, str(HERE))
    from local_gateway import _expense_id

    dynamodb.Table("ReceiptsAgent-Users").put_item(Item=user)
    expenses = dynamodb.Table("ReceiptsAgent-Expenses")
    from decimal import Decimal

    for row in spec["expenses"]:
        item = {k: (Decimal(str(v)) if isinstance(v, float) else v) for k, v in row.items()}
        item["userId"] = user["userId"]
        item["expenseId"] = _expense_id(user["userId"], row["merchant"], row["transactionDate"], row["total"])
        item["total"] = str(row["total"])
        expenses.put_item(Item=item)
    print(f"Seeded {user['userId']} with {len(spec['expenses'])} expenses")

    collector = collector_cls(log_group_name=runtime_log_group(output(outs, "ChatRuntimeArn")), region=region)
    run_dir = args.out / f"deployed-chat-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    for conversation in spec["conversations"]:
        # Runtime session ids must be at least 33 characters.
        session_id = f"chat-{conversation['id']}-{uuid.uuid4().hex}"
        started = datetime.now(timezone.utc) - timedelta(minutes=1)
        transcript = []
        print(f"\n== {conversation['id']}")
        for text in conversation["turns"]:
            answer = ask(text, user["userId"], region, args.stack, session_id=session_id)
            transcript.append({"user": text, "agent": answer})
            print(f"  you>   {text}")
            print(f"  agent> {answer.strip()[:200]}")
        spans = collector.collect(session_id, started, datetime.now(timezone.utc))
        case_dir = run_dir / conversation["id"]
        case_dir.mkdir(exist_ok=True)
        (case_dir / "adot.json").write_text(json.dumps(spans, indent=2, default=str))
        (case_dir / "transcript.json").write_text(
            json.dumps({"session_id": session_id, "conversation": conversation, "transcript": transcript}, indent=2)
        )
        print(f"  {len(spans)} spans collected")

    print(f"\nWritten to {run_dir}. Score with: python score_chat.py --run {run_dir}")
    return run_dir


def main() -> None:
    args = parse_args()
    import boto3
    from bedrock_agentcore.evaluation.agent_span_collector.agent_span_collector import CloudWatchAgentSpanCollector

    outs = stack_outputs(boto3.client("cloudformation", region_name=args.region), args.stack)
    if args.only in (None, "receipts"):
        print("== Receipts through the deployed pipeline\n")
        run_receipts(args, boto3, outs, CloudWatchAgentSpanCollector)
    if args.only in (None, "chat"):
        print("\n== Chat through the deployed chat Runtime\n")
        run_chat(args, boto3, outs, CloudWatchAgentSpanCollector)


if __name__ == "__main__":
    main()
