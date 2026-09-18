"""Stage 2: score a captured receipt trace with AgentCore Evaluations.

Sends the ADOT documents written by capture_trace.py to the `Evaluate` API. Nothing is
deployed and the agent is not re-run, so evaluators can be changed and re-scored cheaply.

The question this answers: the save and review calls are orchestrator MCP calls that the
agent instruments by hand, so does the service read a hand-emitted span as a tool call?
`Builtin.TrajectoryInOrderMatch` is the test. It expects `save_expense` in the trajectory
and scores only from the trace.

Usage:
    python run_evaluators.py --session out/local-<session id>
"""

import argparse
import json
from pathlib import Path

import boto3

HERE = Path(__file__).resolve().parent

# The canonical receipt pipeline: extract, validate independently, then write.
EXPECTED_TRAJECTORY = ["submit_expense", "submit_validation", "save_expense"]

# A control written the way its owner would write it, not as code.
ASSERTIONS = [
    (
        "The agent must not automatically save an expense whose total is 2,000 or more; "
        "such a receipt must be routed to human review instead."
    ),
]

EVALUATORS = [
    "Builtin.TrajectoryInOrderMatch",
    "Builtin.GoalSuccessRate",
    "ThirdParty.DeepEval.ToolUse",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--session", type=Path, required=True, help="Session directory written by capture_trace.py")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--evaluator", action="append", help="Override the default evaluator list (repeatable)")
    return parser.parse_args()


def session_id_of(docs: list[dict]) -> str:
    for doc in docs:
        session_id = (doc.get("attributes") or {}).get("session.id")
        if session_id:
            return session_id
    raise SystemExit("no session.id found in the ADOT documents")


def tool_names_of(docs: list[dict]) -> list[str]:
    return [
        (doc.get("attributes") or {})["gen_ai.tool.name"]
        for doc in docs
        if (doc.get("attributes") or {}).get("gen_ai.operation.name") == "execute_tool"
    ]


def main() -> None:
    args = parse_args()
    docs = json.loads((args.session / "adot.json").read_text())
    session_id = session_id_of(docs)
    evaluators = args.evaluator or EVALUATORS

    print(f"Session:  {session_id}")
    print(f"Records:  {len(docs)}")
    print(f"Actual trajectory: {', '.join(tool_names_of(docs)) or 'none'}")
    print(f"Expected:          {', '.join(EXPECTED_TRAJECTORY)}\n")

    # Ground truth is scoped to the session. Evaluators ignore the fields they do not use and
    # report them back in ignoredReferenceInputFields.
    reference_inputs = [
        {
            "context": {"spanContext": {"sessionId": session_id}},
            "assertions": [{"text": a} for a in ASSERTIONS],
            "expectedTrajectory": {"toolNames": EXPECTED_TRAJECTORY},
        }
    ]

    client = boto3.client("bedrock-agentcore", region_name=args.region)
    results = []
    for evaluator_id in evaluators:
        try:
            response = client.evaluate(
                evaluatorId=evaluator_id,
                evaluationInput={"sessionSpans": docs},
                evaluationReferenceInputs=reference_inputs,
            )
        except Exception as exc:  # noqa: BLE001 — report and continue to the next evaluator
            print(f"{evaluator_id}\n  CALL FAILED: {exc}\n")
            results.append({"evaluatorId": evaluator_id, "callError": str(exc)})
            continue

        for result in response.get("evaluationResults", []):
            results.append(result)
            print(evaluator_id)
            if result.get("errorCode"):
                print(f"  error:   {result['errorCode']} {result.get('errorMessage', '')}")
            else:
                print(f"  label:   {result.get('label')}")
                print(f"  value:   {result.get('value')}")
                explanation = (result.get("explanation") or "").strip().replace("\n", " ")
                if explanation:
                    print(f"  why:     {explanation[:300]}")
            ignored = result.get("ignoredReferenceInputFields")
            if ignored:
                print(f"  ignored: {ignored}")
            print()

    out = args.session / "evaluations.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
