# Threshold Control Monitor, and Deploy-Time Boundary Tests

**Date:** 2026-09-23

The question was whether a check that the Cedar policy works can have value of its own. It can. The earlier objection to `ReceiptsThresholdBreach`, that it "can only fail if the policy is off", describes exactly the job: noticing that a deterministic control has stopped working in production. The policy can be edited or detached, the engine set to log-only, or a deploy can leave the Gateway without it.

What changes is the category. It measures **control health, not agent quality**, and it is labelled that way.

## A. Live control monitor: `ReceiptsThresholdControl`

In `evaluators/business_outcomes.py`, it reads `receipts.status` and `receipts.total` from the span and returns one of three labels:
- **`breach`:** saved automatically at or above $2,000.
- **`held`:** at or above the limit and not saved. The explanation says whether Cedar blocked it or the validator held it first.
- **`not_engaged`:** below the limit, so the control was not tested.

It needs no labels, so unlike extraction accuracy and routing it can run on live traffic. It is the only live check on the policy. `run_dataset.py` runs it on every receipt and prints a control section.

**Deliberate limit:** it reads the total the agent saved, which is the total the policy saw. A misread $2,400 saved as $240 is invisible to it. That is extraction accuracy's job, not the monitor's.

## Seeing it catch a missing control

`local_gateway.POLICY_ENABLED` and `run_dataset.py --without-policy` switch off the local stand-in for the Cedar policy.

| Run | Validator | Policy | Outcome | Monitor |
|---|---|---|---|---|
| `over_threshold`, policy off | AUTO_PERSIST | off | saved $2,400 | **breach** |
| `over_threshold`, policy on | NEEDS_REVIEW | not reached | held | held, by the validator first |

This was **not a clean pair.** The validator is not deterministic: this time it held the receipt itself, so Cedar was never exercised in the policy-on run. The runs on 09-18 and 09-22 show the other half, with the validator approving $2,400 at confidence 93-97 and Cedar denying it. Together they show all three states. What this run adds is the monitor catching the breach once the policy is gone.

Two attempts failed first with Bedrock `ServiceUnavailableException`. That is transient and unrelated to the change.

## B. Deploy-time boundary tests

`tests/test_e2e_cedar_live.py` gains `test_threshold_boundaries` against the real Gateway:
- `2000`: denied
- `1999`: allowed
- `2000.50`: denied
- `15.90`: allowed
- `1999.99`: allowed

The two totals with cents under the limit settle an open question. The policy's own description says a fractional total makes the decimal-vs-Long comparison error and the forbid fail closed. If that is how the deployed engine behaves, those two tests fail, and **every real receipt with cents is being sent to review instead of saving**. The local gateway compares plain numbers, so no local run can show this.

**Not yet run.** No stack is deployed, and all 8 Cedar tests skip cleanly.

## Where it sits

Tests prove the control before deploy. The monitor watches it after. Neither is presented as measuring the agent.
