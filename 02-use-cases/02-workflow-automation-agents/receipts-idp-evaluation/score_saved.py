"""Stage 3: re-score saved traces without re-running the agent.

The traces from `run_dataset.py` are on disk, so new evaluators can be added and scored
against receipts that have already been processed. No Textract, no extraction model, no
waiting. Only the judge calls an evaluator makes itself.

What it adds over the run itself:

  B4  routing outcome, four labels, from the code-based evaluator
  B3d process integrity, `Builtin.TrajectoryInOrderMatch` through the Evaluate API
  S1  the reviewer note scored for leaked personal data and for malicious content,
      on escalated receipts only, since that is the only time a note is written

The trajectory check runs twice on purpose:

  process   [submit_expense, submit_validation]         did the independent validator run
                                                        before anything was written
  full      the above plus the write the label expects  the same check, plus routing

Comparing the two shows how easily a process check turns into a routing check by accident.
The first is the sample's design claim. The second is B4 wearing a different hat.

Usage:
    python score_saved.py --run out/dataset-<id>
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TERMINAL_TOOL = {"processed": "save_expense", "needs_review": "human_review"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="A run directory written by run_dataset.py")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures")
    parser.add_argument("--skip-trajectory", action="store_true", help="Score B4 only, no AWS calls")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(HERE / "evaluators"))

    import boto3
    from bedrock_agentcore.evaluation.custom_code_based_evaluators import EvaluatorInput
    from business_outcomes import handler

    labels = {entry["id"]: entry for entry in json.loads((args.fixtures / "labels.json").read_text())}
    results = json.loads((args.run / "results.json").read_text())
    client = None if args.skip_trajectory else boto3.client("bedrock-agentcore", region_name=args.region)

    def judge(evaluator_id: str, spans: list[dict]):
        """Score the human-facing note. TRACE level, so the judge reads the assistant turn."""
        try:
            response = client.evaluate(evaluatorId=evaluator_id, evaluationInput={"sessionSpans": spans})
        except Exception as exc:  # noqa: BLE001 — report and carry on through the set
            return f"call failed: {str(exc)[:60]}", ""
        results = response.get("evaluationResults") or []
        if not results:
            return "no result", ""
        worst = min(results, key=lambda r: r.get("value") if r.get("value") is not None else 1.0)
        return f"{worst.get('label')} ({worst.get('value')})", (worst.get("explanation") or "")[:200]

    def trajectory(spans: list[dict], session_id: str, tools: list[str]):
        response = client.evaluate(
            evaluatorId="Builtin.TrajectoryInOrderMatch",
            evaluationInput={"sessionSpans": spans},
            evaluationReferenceInputs=[
                {"context": {"spanContext": {"sessionId": session_id}}, "expectedTrajectory": {"toolNames": tools}}
            ],
        )
        first = (response.get("evaluationResults") or [{}])[0]
        return first.get("label"), first.get("explanation", "")

    rows = []
    for row in results:
        fixture_id = row["id"]
        label = labels[fixture_id]
        spans = json.loads((args.run / fixture_id / "adot.json").read_text())

        routing = handler.unwrapped(
            EvaluatorInput(
                evaluation_level="SESSION",
                session_spans=spans,
                evaluator_name="ReceiptsRoutingOutcome",
                reference_inputs=[
                    {
                        "context": {"spanContext": {"sessionId": row["session_id"]}},
                        "expectedResponse": {"text": json.dumps(label)},
                    }
                ],
            ),
            None,
        )

        process_label = full_label = "skipped"
        if client:
            process_label, _ = trajectory(spans, row["session_id"], ["submit_expense", "submit_validation"])
            expected_tools = ["submit_expense", "submit_validation", TERMINAL_TOOL[label["expected_outcome"]]]
            full_label, _ = trajectory(spans, row["session_id"], expected_tools)

        pii = security = "not escalated"
        if client and row["actual"] == "needs_review":
            pii, pii_why = judge("ThirdParty.DeepEval.PIILeakage", spans)
            security, security_why = judge("ThirdParty.AutoEval.Security", spans)

        rows.append(
            {
                **row,
                "routing": routing.label,
                "trajectory_process": process_label,
                "trajectory_full": full_label,
                "pii_leakage": pii,
                "autoeval_security": security,
            }
        )
        print(f"  {fixture_id:16s} {routing.label:20s} process={process_label:8s} full={full_label}")
        if client and row["actual"] == "needs_review":
            print(f"    note: PIILeakage {pii} | Security {security}")

    (args.run / "scored.json").write_text(json.dumps(rows, indent=2, default=str))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["routing"]] = counts.get(row["routing"], 0) + 1

    review_correct = counts.get("ReviewCorrect", 0)
    false_alarm = counts.get("FalseAlarm", 0)
    reviewed = review_correct + false_alarm

    print("\nB4 review-queue precision")
    for name in ("AutoPersistCorrect", "ReviewCorrect", "FalseAlarm", "FalseClear", "NoOutcome"):
        if counts.get(name):
            print(f"  {name:20s} {counts[name]}")
    if reviewed:
        print(
            f"  precision            {review_correct / reviewed:.0%}  ({review_correct} of {reviewed} escalations were needed)"
        )
    if counts.get("FalseClear"):
        exposure = sum(r["true_total"] for r in rows if r["routing"] == "FalseClear")
        print(f"  false-clear exposure {exposure:.2f} committed without a check")

    if client:
        print("\nB3d process integrity")
        passed = sum(1 for r in rows if r["trajectory_process"] == "Yes")
        full_passed = sum(1 for r in rows if r["trajectory_full"] == "Yes")
        print(f"  validator ran before the write        {passed}/{len(rows)}")
        print(f"  the same check including routing      {full_passed}/{len(rows)}")

    print(f"\nWritten to {args.run / 'scored.json'}")


if __name__ == "__main__":
    main()
