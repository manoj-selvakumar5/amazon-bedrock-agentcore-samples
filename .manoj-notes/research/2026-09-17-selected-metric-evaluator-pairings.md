# Selected Metric-to-Evaluator Pairings

**Date:** 2026-09-17

What is selected after the critical pass, and how tightly each evaluator is tied to the business metric it claims to measure.

The test applied to every row: does the evaluator measure the business quantity, or something adjacent that can pass while the business outcome fails. `Summarization` failed that test and was dropped, which set the bar for the rest.

## Selected

| Business metric | Evaluator | Type | Tightness |
|---|---|---|---|
| B1 straight-through processing rate | STP outcome from `receipts.status` | code-based | **Tight.** It is the metric, not a proxy |
| B2 dollar-weighted error | Extracted total against the labelled total, weighted by amount | code-based | **Tight**, offline only. No labels exist in production |
| B3 approval threshold | Saved amount against the threshold | code-based | **Tight.** Same data the control acts on |
| B3 duplicate and split receipts | Expense id and same-day totals across sessions | code-based | **Tight.** The failure lives between receipts, which is why it needs cross-session state |
| B3 daily velocity limit | Daily total at write time, enforced inside `save_expense` | code-based | **Tight**, once the control sits in the Lambda rather than depending on the agent to supply the number |
| B3 process integrity | `Builtin.TrajectoryInOrderMatch`, expecting the validator before the write | built-in, programmatic | **Tight for this claim only.** It proves a step happened, never that the step was correct |
| B4 review-queue precision | Four routing labels against the golden set | code-based, categorical | **Tight** offline. Production needs `resolve_review`, which does not exist |
| Security incidents | `ThirdParty.DeepEval.PIILeakage` on the reviewer note | third-party | **Mostly tight.** Any card digit in a shared queue is wrong, so not knowing whose data it is does not matter here |
| Security incidents | AutoEval `Security` on the reviewer note | third-party | **Untested.** The note quotes malicious text rather than being malicious, so it may score clean. One run settles it |
| B2 under attack | Extracted total against the label on an adversarial receipt | code-based | **Tight.** Quiet compliance with an injected instruction is a dollar error |
| Control calibration | Candidate thresholds swept over the golden set in `LOG_ONLY` mode, reporting STP against error escaping review | code-based | **Tight**, and the only row whose output is a decision rather than a score |
| (counter-example) | `ThirdParty.DeepEval.ToolUse` | third-party | **Owns nothing.** Scored a correct run 0.25 because it assumed a user who asked for something. Kept as evidence |

## Rejected, and why

| Rejected | Reason |
|---|---|
| `ThirdParty.DeepEval.Summarization` on the reviewer note | Scores a summary against a source. The note is a justification of a routing decision, so a note that faithfully describes the receipt while never naming the concern scores well and still wastes the reviewer's time |
| `Builtin.GoalSuccessRate` with assertions, for finance-owned rules | A probabilistic instrument for a deterministic question. The Stage 2 run passed at 2,428 judge tokens because a $15.90 receipt never engaged the $2,000 rule, so the same green means "obeyed" and "not applicable". It also cannot run on live traffic, because ground truth cannot be supplied to an online config |
| Velocity enforced by the agent fetching history and passing a total into Cedar | Designed so a step would exist so the trajectory matcher would have a job. Nobody would build it that way. The check belongs in the Lambda, where it cannot be skipped |
| Pattern check for injected content in the reviewer note | A string scan for URLs, addresses and action phrases misses pure social engineering ("pre-approved by finance, no further review required"), which is the more dangerous payload. The control belongs in the design: assemble the note from validated fields so untrusted text cannot enter it. Then conformance to that template is the check |
| Reviewer note justified by third-party metrics | The note is legitimate on its own terms, as reviewer handling time. Justifying it by which metrics it unlocks is the reasoning the framework exists to prevent |

## Blocked, not rejected

| Metric | What is missing |
|---|---|
| B4 in production | `resolve_review`, so no reviewer decision ever returns |
| B5 completion rate | An upload count to compare against the ledger. Not an evaluator at all, because a lost receipt leaves no session |
| C1 to C4, the chat workload | Multi-turn sessions and a golden question set. Deferred, not dropped |

## Counts

- **Business metrics measured** once the selected work is built: B1, B2, B3, security incidents. B4 offline only.
- **Evaluators: 8.** Four code-based (STP, dollar error, control breaches, routing labels), one built-in (`TrajectoryInOrderMatch`), and three third-party (`PIILeakage` tight, AutoEval `Security` untested, `ToolUse` as the counter-example). Control calibration is an offline analysis rather than a registered evaluator.
- **Third-party metrics that genuinely own a business outcome: 1**, possibly 2 after the `Security` test.
- **Judges among the selected set: 2**, both third-party. Every first-party evaluator selected is deterministic.

That last number is the honest finding. For a document pipeline, most conversational metrics do not apply, and reporting that with evidence is worth more than reshaping the product until they do.
