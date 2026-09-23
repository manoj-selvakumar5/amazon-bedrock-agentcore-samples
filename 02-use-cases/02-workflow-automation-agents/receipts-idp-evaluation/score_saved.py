"""Stage 3: re-score saved traces without re-running the agent.

The traces from `run_dataset.py` are on disk, so new evaluators can be added and scored
against receipts that have already been processed. No Textract, no extraction model, no
waiting. Only the judge calls an evaluator makes itself.

What it adds over the run itself:

  B4  routing outcome, four labels, from the code-based evaluator. Receipts whose right
      answer depends on another receipt (label `cross_receipt`) are left out, because the
      validator sees one receipt at a time and cannot know
  B2b invented values, `Builtin.ToolParameterAccuracy` on the extractor's submit_expense
      call: did the model put a value into the record that its own input never contained.
      Read beside B2, it splits the blame for a wrong field between the model and the OCR
  B3d process integrity, `Builtin.TrajectoryInOrderMatch` through the Evaluate API
  S1  opt-in with --with-judges: the reviewer note scored by PIILeakage and AutoEval
      Security. Kept as evidence only; neither discriminates on this workload, see
      .manoj-notes/research/2026-09-18-security-judge-verdict.md

The trajectory check runs twice on purpose:

  process   [submit_expense, submit_validation]         did the independent validator run
                                                        before anything was written
  full      the above plus the write the label expects  the same check, plus routing

Comparing the two shows how easily a process check turns into a routing check by accident.
The first is the sample's design claim. The second is B4 wearing a different hat.

ToolParameterAccuracy is sent the extractor's part of the trace only. On the whole session
the judge also sees the validator's and the note writer's inputs, which repeat the
extractor's own values, so an invented value looks sourced. See
.manoj-notes/research/2026-09-22-tool-parameter-accuracy-contrast.md. For the same reason it
cannot run in an online config yet, which scores the whole session.

Usage:
    python score_saved.py --run out/dataset-<id>
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TERMINAL_TOOL = {"processed": "save_expense", "needs_review": "human_review"}


def extractor_only(spans: list[dict]) -> list[dict]:
    """The session up to the end of the extractor agent, which is the first invoke_agent span.

    Keeps the root invocation span so the session still has its receipts.* attributes.
    """
    extractor = next(s for s in spans if s.get("name", "").startswith("invoke_agent"))
    cutoff = extractor["endTimeUnixNano"]
    return [
        s
        for s in spans
        if s.get("name") == "receipts.invocation" or (s.get("startTimeUnixNano", s.get("timeUnixNano")) or 0) <= cutoff
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="A run directory written by run_dataset.py")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures")
    parser.add_argument("--skip-trajectory", action="store_true", help="Skip the trajectory check")
    parser.add_argument(
        "--skip-parameters", action="store_true", help="Skip ToolParameterAccuracy on the extractor (judge tokens)"
    )
    parser.add_argument(
        "--with-judges", action="store_true", help="Also run the third-party security judges (evidence only)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(HERE / "evaluators"))

    import boto3
    from bedrock_agentcore.evaluation.custom_code_based_evaluators import EvaluatorInput
    from business_outcomes import handler

    labels = {entry["id"]: entry for entry in json.loads((args.fixtures / "labels.json").read_text())}
    results = json.loads((args.run / "results.json").read_text())
    needs_aws = not args.skip_trajectory or not args.skip_parameters or args.with_judges
    client = boto3.client("bedrock-agentcore", region_name=args.region) if needs_aws else None

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

    def invented_values(spans: list[dict]):
        """ToolParameterAccuracy on the extractor's submit_expense call, extractor spans only."""
        spans = extractor_only(spans)
        target = next(
            s["spanId"] for s in spans if (s.get("attributes") or {}).get("gen_ai.tool.name") == "submit_expense"
        )
        try:
            response = client.evaluate(
                evaluatorId="Builtin.ToolParameterAccuracy", evaluationInput={"sessionSpans": spans}
            )
        except Exception as exc:  # noqa: BLE001 — report and carry on through the set
            return f"call failed: {str(exc)[:60]}", ""
        for result in response.get("evaluationResults") or []:
            if result.get("context", {}).get("spanContext", {}).get("spanId") == target:
                return result.get("label"), result.get("explanation", "")
        return "no result", ""

    rows = []
    for row in results:
        fixture_id = row["id"]
        label = labels[fixture_id]
        spans = json.loads((args.run / fixture_id / "adot.json").read_text())

        if label.get("cross_receipt"):
            routing_label = "n/a (cross-receipt)"
        else:
            routing_label = handler.unwrapped(
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
            ).label

        process_label = full_label = "skipped"
        if not args.skip_trajectory:
            process_label, _ = trajectory(spans, row["session_id"], ["submit_expense", "submit_validation"])
            expected_tools = ["submit_expense", "submit_validation", TERMINAL_TOOL[label["expected_outcome"]]]
            full_label, _ = trajectory(spans, row["session_id"], expected_tools)

        parameters, parameters_why = "skipped", ""
        if not args.skip_parameters:
            parameters, parameters_why = invented_values(spans)

        pii = security = "not escalated" if args.with_judges else "not run"
        if args.with_judges and row["actual"] == "needs_review":
            pii, pii_why = judge("ThirdParty.DeepEval.PIILeakage", spans)
            security, security_why = judge("ThirdParty.AutoEval.Security", spans)

        rows.append(
            {
                **row,
                "routing": routing_label,
                "tool_parameter_accuracy": parameters,
                "tool_parameter_accuracy_explanation": parameters_why,
                "trajectory_process": process_label,
                "trajectory_full": full_label,
                "pii_leakage": pii,
                "autoeval_security": security,
            }
        )
        print(
            f"  {fixture_id:16s} {routing_label:20s} parameters={parameters:8s} process={process_label:8s} full={full_label}"
        )
        if args.with_judges and row["actual"] == "needs_review":
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
    excluded = [r["id"] for r in rows if r["routing"] == "n/a (cross-receipt)"]
    if excluded:
        print(f"  not scored           {', '.join(excluded)}: the right answer depends on another receipt")

    if not args.skip_parameters:
        # Beside B2, the two verdicts say whose fault a wrong field is.
        wrong = {r["id"] for r in rows if "Also wrong:" in (r.get("extraction_explanation") or "")}
        wrong |= {r["id"] for r in rows if (r.get("dollar_gap") or 0) >= 0.005}
        invented = [r["id"] for r in rows if r["tool_parameter_accuracy"] == "No" and r["id"] in wrong]
        ocr = [r["id"] for r in rows if r["tool_parameter_accuracy"] == "Yes" and r["id"] in wrong]
        false_alarm = [r["id"] for r in rows if r["tool_parameter_accuracy"] == "No" and r["id"] not in wrong]
        print("\nB2b invented values, ToolParameterAccuracy on the extractor")
        print(f"  model invented a wrong field        {len(invented)}  {', '.join(invented)}")
        print(f"  wrong field copied from the OCR     {len(ocr)}  {', '.join(ocr)}")
        print(f"  flagged, extraction actually right  {len(false_alarm)}  {', '.join(false_alarm)}")
        if false_alarm:
            print("  (so far these have been the model's own confidence, which has no source to trace)")

    if not args.skip_trajectory:
        print("\nB3d process integrity")
        passed = sum(1 for r in rows if r["trajectory_process"] == "Yes")
        full_passed = sum(1 for r in rows if r["trajectory_full"] == "Yes")
        print(f"  validator ran before the write        {passed}/{len(rows)}")
        print(f"  the same check including routing      {full_passed}/{len(rows)}")

    print(f"\nWritten to {args.run / 'scored.json'}")


if __name__ == "__main__":
    main()
