"""Stage 3: the code-based evaluators that carry the business metrics.

One Lambda backs several registered evaluators. `EvaluatorInput` carries `evaluator_name`,
so the handler branches on it and each metric is registered separately, returning its own
score. Deploying one function rather than one per metric.

    ReceiptsExtractionAccuracy  B2  did the extractor read the receipt right: dollars on the
                                    total, plus date, merchant, currency, subtotal, tax, tip
    ReceiptsRoutingOutcome      B4  was the escalation, or the auto-save, the right call

One evaluator per model decision: the extractor reading the receipt, the validator choosing
save or review. Controls the code enforces, such as the Cedar threshold, are not re-checked
here, and straight-through rate is a count over B4's outcomes rather than an evaluator.

Each reads span attributes the agent stamps on the invocation span, never message content,
so both keep working when prompt and completion capture is switched off.

Duplicates and splits are deliberately not here. That failure exists between receipts, so a
per-session evaluator cannot see it. It lives in the dataset scorer locally.

Test locally with no AWS:

    from business_outcomes import handler
    handler.unwrapped(EvaluatorInput(...), None)
"""

import json
import re
from typing import Any

from bedrock_agentcore.evaluation.custom_code_based_evaluators import (
    EvaluatorInput,
    EvaluatorOutput,
    custom_code_based_evaluator,
)

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


def _merchant_key(name: Any) -> str:
    """Case and punctuation do not make a merchant wrong: "BLUE BOTTLE" is "Blue Bottle"."""
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


def _field_errors(attributes: dict, label: dict) -> list[str]:
    """Non-total fields recorded differently from the label, one line each.

    Only fields present on both sides are compared, so a label without a tip or a span from
    before these attributes existed does not count as an error.
    """
    errors = []

    def both(span_key: str, label_key: str):
        recorded, expected = attributes.get(span_key), label.get(label_key)
        return (recorded, expected) if recorded is not None and expected is not None else None

    if pair := both("receipts.transaction_date", "transaction_date"):
        if str(pair[0]) != str(pair[1]):
            errors.append(f"date {pair[0]} against a true {pair[1]}")
    if pair := both("receipts.merchant", "merchant"):
        if _merchant_key(pair[0]) != _merchant_key(pair[1]):
            errors.append(f"merchant {pair[0]!r} against a true {pair[1]!r}")
    if pair := both("receipts.currency", "currency"):
        if str(pair[0]).upper() != str(pair[1]).upper():
            errors.append(f"currency {pair[0]} against a true {pair[1]}")
    for field in ("subtotal", "tax", "tip"):
        if pair := both(f"receipts.{field}", field):
            try:
                if abs(float(pair[0]) - float(pair[1])) >= 0.005:
                    errors.append(f"{field} {float(pair[0]):.2f} against a true {float(pair[1]):.2f}")
            except (TypeError, ValueError):
                errors.append(f"{field} {pair[0]!r} is not a number")
    return errors


def _extraction_accuracy(attributes: dict, label: dict) -> EvaluatorOutput:
    """B2. Dollars recorded wrong on the total, plus any other field recorded wrong.

    `value` stays the dollar gap on the total, so the dollar-weighted rate is unchanged. The
    other fields are in the label and explanation, because a fabricated date costs no dollars
    and would otherwise read as a perfect extraction.
    """
    recorded = attributes.get("receipts.total")
    true_total = label.get("total")
    if recorded is None or true_total is None:
        return EvaluatorOutput(
            errorCode="MISSING_REQUIRED_FIELD",
            errorMessage="needs receipts.total on the span and a labelled total in expectedResponse",
        )
    gap = abs(float(recorded) - float(true_total))
    field_errors = _field_errors(attributes, label)

    if gap > MATERIALITY:
        verdict = "material_error"
    elif field_errors:
        verdict = "field_error"
    elif gap >= 0.005:
        verdict = "minor_error"
    else:
        verdict = "exact"

    explanation = f"Total recorded {float(recorded):.2f} against a true {float(true_total):.2f}, off by {gap:.2f}."
    if field_errors:
        explanation += " Also wrong: " + "; ".join(field_errors) + "."
    explanation += " Sum the total gaps and divide by the sum of true totals for the dollar-weighted rate"

    return EvaluatorOutput(value=gap, label=verdict, explanation=explanation)


def _routing_outcome(attributes: dict, label: dict) -> EvaluatorOutput:
    """B4. Four named outcomes, because the two failures have different cost shapes.

    A false clear scales with the amount: money committed that should have been checked.
    A false alarm is a roughly fixed cost, an analyst confirming work that was already right.
    Collapsing them into one accuracy number hides which of the two is happening.

    The validator is judged on what it was shown, the extraction, not on the receipt itself.
    When the extraction got any field wrong, review is the right call whatever the label says,
    so escalating it is not a false alarm. Otherwise one extractor mistake would count twice:
    once in B2 against the extractor, and again here against the validator that caught it.
    """
    status = attributes.get("receipts.status")
    expected = label.get("expected_outcome")
    if not status or not expected:
        return EvaluatorOutput(
            errorCode="MISSING_REQUIRED_FIELD",
            errorMessage="needs receipts.status on the span and expected_outcome in expectedResponse",
        )

    extraction_wrong = _field_errors(attributes, label)
    recorded, true_total = attributes.get("receipts.total"), label.get("total")
    if recorded is not None and true_total is not None and abs(float(recorded) - float(true_total)) >= 0.005:
        extraction_wrong.append(f"total {float(recorded):.2f} against a true {float(true_total):.2f}")
    if extraction_wrong:
        expected = "needs_review"
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

    explanation = outcome[1]
    if extraction_wrong:
        explanation += (
            ". Expected review because the extraction it was shown was wrong: " + "; ".join(extraction_wrong)
        )

    return EvaluatorOutput(
        value=1.0 if outcome[0] in ("AutoPersistCorrect", "ReviewCorrect") else 0.0,
        label=outcome[0],
        explanation=explanation,
    )


@custom_code_based_evaluator()
def handler(input: EvaluatorInput, context) -> EvaluatorOutput:
    """Route to the metric this registration asks for."""
    attributes = _receipt_attributes(input.session_spans)
    name = (input.evaluator_name or "").strip()

    # ReceiptsDollarError is the name B2 was first registered under; kept so older runs resolve.
    if name.endswith("ReceiptsExtractionAccuracy") or name.endswith("ReceiptsDollarError"):
        return _extraction_accuracy(attributes, _label(input))
    if name.endswith("ReceiptsRoutingOutcome"):
        return _routing_outcome(attributes, _label(input))

    return EvaluatorOutput(
        errorCode="UNKNOWN_EVALUATOR",
        errorMessage=f"no metric registered under the name {name!r}",
    )
