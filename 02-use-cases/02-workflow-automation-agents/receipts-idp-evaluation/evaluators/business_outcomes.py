"""Stage 3: the code-based evaluators that carry the business metrics.

One Lambda backs several registered evaluators. `EvaluatorInput` carries `evaluator_name`,
so the handler branches on it and each metric is registered separately, returning its own
score. Deploying one function rather than one per metric.

    ReceiptsStpOutcome        B1   did this receipt clear without a person
    ReceiptsDollarError       B2   how many dollars were recorded wrong
    ReceiptsThresholdBreach   B3a  did anything at or above the limit save automatically
    ReceiptsRoutingOutcome    B4   was the escalation, or the auto-save, the right call

Each reads span attributes the agent stamps on the invocation span, never message content,
so all three keep working when prompt and completion capture is switched off.

B3b, duplicates and splits, is deliberately not here. That failure exists between receipts,
so a per-session evaluator cannot see it. It lives in the dataset scorer locally, and in a
deployed stack becomes this same Lambda reading the Expenses table.

Test locally with no AWS:

    from business_outcomes import handler
    handler.unwrapped(EvaluatorInput(...), None)
"""

import json
from typing import Any

from bedrock_agentcore.evaluation.custom_code_based_evaluators import (
    EvaluatorInput,
    EvaluatorOutput,
    custom_code_based_evaluator,
)

# Mirrors the Cedar policy BlockExcessiveExpense in agentcore/agentcore.json.
POLICY_THRESHOLD = 2000.0

# A receipt is material when a single error exceeds this. Reported alongside the rate,
# because one large miss and a hundred small ones need different responses.
MATERIALITY = 50.0


def _receipt_attributes(spans: list[dict]) -> dict[str, Any]:
    """Collect the receipts.* attributes the agent stamped, across all spans in the session."""
    found: dict[str, Any] = {}
    for span in spans:
        for key, value in (span.get("attributes") or {}).items():
            if key.startswith("receipts."):
                found.setdefault(key, value)
    return found


def _label(input: EvaluatorInput) -> dict[str, Any]:
    """The known answer for this receipt.

    The dataset runner puts it in `expectedResponse.text` as JSON, because that is the only
    session-scoped ground-truth field the service passes through to a code-based evaluator.
    `metadata` on a dataset scenario does not reach the evaluator.
    """
    for reference in input.reference_inputs:
        text = reference.expected_response_text
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _stp_outcome(attributes: dict) -> EvaluatorOutput:
    """B1. The share of receipts that clear with no person involved."""
    status = attributes.get("receipts.status")
    if not status:
        return EvaluatorOutput(
            errorCode="MISSING_REQUIRED_FIELD",
            errorMessage="no receipts.status on the session, so the outcome was never recorded",
        )
    cleared = status == "processed"
    return EvaluatorOutput(
        value=1.0 if cleared else 0.0,
        label=status,
        explanation=(
            "Cleared without a person"
            if cleared
            else f"Did not clear: {status}. Averaged across receipts this is the STP rate"
        ),
    )


def _dollar_error(attributes: dict, label: dict) -> EvaluatorOutput:
    """B2. Dollars recorded wrong, not fields recorded wrong."""
    recorded = attributes.get("receipts.total")
    true_total = label.get("total")
    if recorded is None or true_total is None:
        return EvaluatorOutput(
            errorCode="MISSING_REQUIRED_FIELD",
            errorMessage="needs receipts.total on the span and a labelled total in expectedResponse",
        )
    gap = abs(float(recorded) - float(true_total))
    material = gap > MATERIALITY
    return EvaluatorOutput(
        value=gap,
        label="material_error" if material else ("exact" if gap < 0.005 else "minor_error"),
        explanation=(
            f"Recorded {float(recorded):.2f} against a true {float(true_total):.2f}, off by {gap:.2f}. "
            "Sum these gaps and divide by the sum of true totals for the dollar-weighted rate"
        ),
    )


def _threshold_breach(attributes: dict) -> EvaluatorOutput:
    """B3a. A breach is money at or above the limit committed without a person."""
    status = attributes.get("receipts.status")
    total = attributes.get("receipts.total")
    if not status or total is None:
        return EvaluatorOutput(
            errorCode="MISSING_REQUIRED_FIELD",
            errorMessage="needs receipts.status and receipts.total on the span",
        )
    total = float(total)
    breach = status == "processed" and total >= POLICY_THRESHOLD
    if breach:
        explanation = (
            f"{total:.2f} saved automatically at or above the {POLICY_THRESHOLD:.0f} limit. One breach is a finding"
        )
    elif total >= POLICY_THRESHOLD:
        blocked_by_policy = bool(attributes.get("receipts.cedar_blocked"))
        explanation = (
            f"{total:.2f} is at or above the limit and was held for review"
            f"{', blocked by policy' if blocked_by_policy else ', routed by the validator'}. The control worked"
        )
    else:
        explanation = f"{total:.2f} is below the limit, so the control was not engaged"
    return EvaluatorOutput(
        value=1.0 if breach else 0.0, label="breach" if breach else "no_breach", explanation=explanation
    )


def _routing_outcome(attributes: dict, label: dict) -> EvaluatorOutput:
    """B4. Four named outcomes, because the two failures have different cost shapes.

    A false clear scales with the amount: money committed that should have been checked.
    A false alarm is a roughly fixed cost, an analyst confirming work that was already right.
    Collapsing them into one accuracy number hides which of the two is happening.
    """
    status = attributes.get("receipts.status")
    expected = label.get("expected_outcome")
    if not status or not expected:
        return EvaluatorOutput(
            errorCode="MISSING_REQUIRED_FIELD",
            errorMessage="needs receipts.status on the span and expected_outcome in expectedResponse",
        )
    if status not in ("processed", "needs_review"):
        return EvaluatorOutput(
            value=0.0,
            label="NoOutcome",
            explanation=f"Receipt ended {status}, so it was neither saved nor escalated. Counts against completion, not routing",
        )

    outcome = {
        ("processed", "processed"): ("AutoPersistCorrect", "Saved automatically and the label agrees. The goal"),
        ("processed", "needs_review"): (
            "FalseClear",
            "Saved automatically when it should have been escalated. The expensive failure, and it scales with the amount",
        ),
        ("needs_review", "processed"): (
            "FalseAlarm",
            "Escalated when it was already correct. An analyst confirms work that needed no confirming",
        ),
        ("needs_review", "needs_review"): ("ReviewCorrect", "Escalated and the label agrees. Working as designed"),
    }[(status, expected)]

    return EvaluatorOutput(
        value=1.0 if outcome[0] in ("AutoPersistCorrect", "ReviewCorrect") else 0.0,
        label=outcome[0],
        explanation=outcome[1],
    )


@custom_code_based_evaluator()
def handler(input: EvaluatorInput, context) -> EvaluatorOutput:
    """Route to the metric this registration asks for."""
    attributes = _receipt_attributes(input.session_spans)
    name = (input.evaluator_name or "").strip()

    if name.endswith("ReceiptsStpOutcome"):
        return _stp_outcome(attributes)
    if name.endswith("ReceiptsDollarError"):
        return _dollar_error(attributes, _label(input))
    if name.endswith("ReceiptsThresholdBreach"):
        return _threshold_breach(attributes)
    if name.endswith("ReceiptsRoutingOutcome"):
        return _routing_outcome(attributes, _label(input))

    return EvaluatorOutput(
        errorCode="UNKNOWN_EVALUATOR",
        errorMessage=f"no metric registered under the name {name!r}",
    )
