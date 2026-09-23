"""Score saved chat conversations with the two session-level third-party evaluators.

  ConversationCompleteness  C1 self-service resolution, live signal: of what the employee
                            asked across the conversation, how much was handled. Used on
                            chat instead of Builtin.GoalSuccessRate, not beside it
  KnowledgeRetention        diagnostic: does the assistant keep what the employee said
                            earlier, or ask for it again

Both are managed DeepEval metrics: no ground truth, no parameters. They judge whether the
conversation looks resolved and consistent, not whether any figure in it is right; a
confidently wrong total can score as complete. Chat is a single agent with one session per
conversation, so the whole-session trap from the receipt pipeline does not apply.

Usage:
    python score_chat.py --run out/chat-<id>
"""

import argparse
import json
from pathlib import Path

EVALUATORS = ["ThirdParty.DeepEval.ConversationCompleteness", "ThirdParty.DeepEval.KnowledgeRetention"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="A run directory written by run_chat.py")
    parser.add_argument("--region", default="us-west-2")
    return parser.parse_args()


def score(client, evaluator_id: str, spans: list[dict]) -> dict:
    try:
        response = client.evaluate(evaluatorId=evaluator_id, evaluationInput={"sessionSpans": spans})
    except Exception as exc:  # noqa: BLE001 — report and carry on through the set
        return {"label": "call failed", "value": None, "explanation": str(exc)[:200]}
    result = (response.get("evaluationResults") or [{}])[0]
    return {
        "label": result.get("label") or result.get("errorCode") or "no result",
        "value": result.get("value"),
        "explanation": result.get("explanation") or result.get("errorMessage") or "",
        "tokens": (result.get("tokenUsage") or {}).get("totalTokens"),
    }


def main() -> None:
    args = parse_args()
    import boto3

    client = boto3.client("bedrock-agentcore", region_name=args.region)
    rows = []
    print(f"{'conversation':20s} {'turns':>5s}  {'completeness':>12s}  {'retention':>9s}")
    for case_dir in sorted(p for p in args.run.iterdir() if (p / "adot.json").exists()):
        spans = json.loads((case_dir / "adot.json").read_text())
        turns = len(json.loads((case_dir / "transcript.json").read_text())["transcript"])
        scores = {evaluator.split(".")[-1]: score(client, evaluator, spans) for evaluator in EVALUATORS}
        rows.append({"id": case_dir.name, "turns": turns, **scores})
        c, k = scores["ConversationCompleteness"], scores["KnowledgeRetention"]
        print(f"{case_dir.name:20s} {turns:5d}  {str(c['value']):>12s}  {str(k['value']):>9s}")

    (args.run / "scored.json").write_text(json.dumps(rows, indent=2, default=str))
    print(f"\nWritten to {args.run / 'scored.json'}")


if __name__ == "__main__":
    main()
