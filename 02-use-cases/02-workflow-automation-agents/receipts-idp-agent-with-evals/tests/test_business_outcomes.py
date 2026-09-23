"""Unit tests for the code-based evaluators (no AWS).

The same handler is deployed as the evaluator Lambda. The online path passes only the
evaluator id, the on-demand path passes the name, and both must route to the same metric."""

import os
import sys

import pytest
from bedrock_agentcore.evaluation.custom_code_based_evaluators import EvaluatorInput

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evaluators", "business_outcomes"))
from business_outcomes import handler  # noqa: E402

pytestmark = pytest.mark.unit

SAVED_OVER_LIMIT = [{"attributes": {"receipts.status": "processed", "receipts.total": 2400.0}}]


def _run(**ids):
    return handler.unwrapped(
        EvaluatorInput(evaluation_level="SESSION", session_spans=SAVED_OVER_LIMIT, reference_inputs=[], **ids), None
    )


def test_online_path_routes_on_the_evaluator_id():
    out = _run(evaluator_id="ReceiptsAgent_ReceiptsThresholdControl-cxrwrs9ZLp")
    assert out.label == "breach"


def test_on_demand_path_routes_on_the_evaluator_name():
    out = _run(evaluator_name="ReceiptsAgent_ReceiptsThresholdControl")
    assert out.label == "breach"


def test_unknown_evaluator_is_reported_not_guessed():
    out = _run(evaluator_id="SomethingElse-abcdefghij")
    assert out.errorCode == "UNKNOWN_EVALUATOR"


def test_deployed_entry_points_need_no_name_or_id():
    from business_outcomes import threshold_control_handler

    out = threshold_control_handler.unwrapped(
        EvaluatorInput(evaluation_level="SESSION", session_spans=SAVED_OVER_LIMIT, reference_inputs=[]), None
    )
    assert out.label == "breach"
