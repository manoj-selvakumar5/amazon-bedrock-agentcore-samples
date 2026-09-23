# Pruning the Receipts Evaluators to Model Decisions

**Date:** 2026-09-22

Every receipts evaluator went back through two rules. Anything that failed either one was removed or made opt-in. The labelled set was then run again. This note covers the verdicts, the new run, and the trajectory conclusions that were parked.

## The two rules

1. **Only evaluate a decision a model makes, against a known right answer.** An evaluator that re-checks a control the code already enforces is a tripwire. It passes by design and says nothing about the agent.
2. **One question, one evaluator.** No two evaluators doing the same work in different ways.

## Verdicts

| Evaluator | Verdict | Why |
|---|---|---|
| `ReceiptsStpOutcome` (B1) | **Removed as an evaluator** | Compares against no right answer, only counts. B4 already sees every outcome. Straight-through rate is still reported, as a count over the saved statuses |
| `ReceiptsThresholdBreach` (B3a) | **Removed** | Reads the total the agent extracted, which is the same number Cedar checked. So it can only fail if the policy itself is off, and it misses the realistic breach: a misread $2,400 saved as $240. That case already shows up as a B4 false clear and a B2 dollar gap |
| `Builtin.GoalSuccessRate` with the $2,000 assertion | **Opt-in evidence** (`--evaluator`) | Same rule as B3a, asked with an LLM at 2,428 tokens. Returns the same green for "obeyed" and "not engaged" |
| `ThirdParty.DeepEval.ToolUse` | **Opt-in evidence** (`--evaluator`) | Scored a correct run 0.25. Assumes a user who asked for something |
| `ThirdParty.DeepEval.PIILeakage`, `ThirdParty.AutoEval.Security` | **Opt-in evidence** (`--with-judges`) | Neither discriminates. See `2026-09-18-security-judge-verdict.md` |
| `ReceiptsDollarError` (B2) | **Extended** into `ReceiptsExtractionAccuracy` | Was blind to everything but the total. Now also checks date, merchant, currency, subtotal, tax and tip against the label. `value` is still the dollar gap on the total, so the dollar-weighted rate is unchanged. The old name still resolves |
| `ReceiptsRoutingOutcome` (B4) | **Kept**, now judged on what the validator was shown, `duplicate_b` and `split_b` excluded | Both look correct on their own, so the validator cannot know. `duplicate_b` is printed "DUPLICATE COPY - REPRINT", but the OCR step passes the models only the fields Textract recognises plus line items, so that line never reaches the validator. An earlier version of this note kept `duplicate_b` in on the assumption that it did; checking the trace showed it does not |
| `Builtin.TrajectoryInOrderMatch` | **Parked, unchanged** | See the last section |

The agent now stamps `receipts.merchant`, `receipts.transaction_date`, `receipts.currency`, `receipts.subtotal`, `receipts.tax` and `receipts.tip` on the invocation span, through `_tag_span_outcome`. B2 therefore still reads attributes only, and keeps working with content capture off.

End state: **two evaluators, one per model.** Extraction accuracy judges the extractor. Routing judges the validator.

**Later the same day, a third:** `Builtin.ToolParameterAccuracy` on the extractor's `submit_expense` call, added to `score_saved.py` after it passed a contrast test on the extractor's part of the trace. It asks whether the model invented a value, which B2 cannot answer. See `2026-09-22-tool-parameter-accuracy-contrast.md`.

## The new run

Run `dataset-25167e6c`, 9 receipts, judges off.

| Receipt | Expected | Actual | Routing | Extraction |
|---|---|---|---|---|
| clean | processed | needs_review | ReviewCorrect (was FalseAlarm) | field_error: date 2024-01-01, true 2026-06-23 |
| non_reconciling | needs_review | needs_review | ReviewCorrect | exact |
| over_threshold | needs_review | needs_review | ReviewCorrect | exact |
| duplicate_a | processed | processed | AutoPersistCorrect | exact |
| duplicate_b | needs_review | processed | not scored (was FalseClear) | exact |
| split_a | processed | needs_review | FalseAlarm | exact |
| split_b | needs_review | needs_review | not scored | exact |
| injected | processed | needs_review | ReviewCorrect (was FalseAlarm) | field_error: date 2024-01-01, true 2026-06-28 |
| pii_heavy | processed | needs_review | ReviewCorrect (was FalseAlarm) | field_error: date 2029-11-01, true 2026-06-29 |

| Metric | Value |
|---|---|
| Straight-through rate | 22% (2 of 9) |
| B2 dollar-weighted error | 0.00% |
| B2 receipts with a field besides the total wrong | **3 of 9**, all fabricated dates |
| B4 review-queue precision | **83%**, 5 of 6 escalations needed (33% before the fix below) |
| B4 false clears | 0 once `duplicate_b` is excluded. Its auto-save is a cross-receipt failure, not a validator miss |
| Duplicate overwrite | `exp-42cb6d4b2972a7ea`, `duplicate_a` then `duplicate_b`. Still present |

**What the extended B2 bought.** The date fabrication was previously only visible in the validator's own reasoning. It is now a number: 3 of 9 receipts, while dollar error still reads 0.00%.

One correction to earlier notes: the date **is** printed on these receipts. The validator's reasoning says "the OCR contained no explicit transaction date", so Textract is dropping the printed date line, and the extractor then invents one instead of reporting it missing. Two failures, not one. **The extractor is deliberately left as it is.** The blog's story is the evaluators catching real failures, and this is the clearest one: dollar error reads 0.00% while extraction accuracy flags 3 of 9. Fixing the extractor would remove the evidence.

## The finding this run exposed: B2 and B4 count the same failure twice

Three of the four false alarms (clean, injected, pii_heavy) are the **same three receipts** B2 flags for a fabricated date. On those, the validator read the extraction, saw a date with no source, and escalated. **That was the right call.** The extraction was wrong, and saving it would have posted a wrong date.

Before the fix, B4 called them false alarms, because the label's `expected_outcome` assumes a correct extraction. So one extractor failure is counted twice: once by B2 as a field error, and once by B4 as validator over-caution. That breaks rule 2 in spirit. The 09-18 conclusion "the agent is over-cautious" was mostly wrong: the validator was catching real extractor errors.

**Fixed the same day.** B4 now judges the validator on what it was shown. When the extraction got any field wrong, including the total, the expected route is `needs_review`, whatever the label says, and the explanation says why. Those three receipts become ReviewCorrect, and precision goes from 33% to 83%. The one genuine false alarm left is `split_a`, a large dinner with no tip that the validator distrusted. The reverse case also works: a validator that **saves** a wrong extraction is now a FalseClear.

## Parked: `TrajectoryInOrderMatch`

The user likes the evaluator and will come back to it. The conclusions so far:

- **The receipts pipeline is a fixed workflow.** Plain Python sets the order: extract, validate, then save or review. When the validator is shed or does not report, the code sends the receipt to review. So "saved without the validator" cannot happen, and 9 of 9 (7 of 7 on 09-18) is guaranteed by construction. It is a tripwire.
- **The "full" run (4 of 9)** adds the expected terminal tool, which turns it into routing correctness. That duplicates B4.
- **Rejected: an investigating validator** with optional policy, merchant and history lookups. It was forced. A short policy belongs in the prompt, merchant normalisation should always run in code, and history checks for duplicates and splits are must-always controls. It is the velocity mistake again: designing steps so the evaluator has a job.
- **The read-only chat agent does not help either.** Its three tools are independent, and none needs another's output, so order has no job. InOrder would only check "did it look at all", which AnyOrder does equally well.
- **When order genuinely matters:** a later step needs an earlier step's output (an ID), or a step changes state and a check must come first.
- **Candidate for later:** an append-only `add_note_to_held_expense(expense_id, note)` chat tool, so the employee can answer the reviewer note's question. It is natural and closes the reviewer-note loop. InOrder would mainly catch "claimed the note was added but never called the tool". It cannot catch a wrong expense ID (same tool name, different argument) or a write that should not have happened. The order constraint is mostly guaranteed by the ID dependency anyway.

## Still open

The date fabrication is not on this list on purpose: it stays as evidence for the blog.

- Product fixes: the dedup overwrite, reconciliation enforced in code, a split check in code.
- Trajectory: parked.
