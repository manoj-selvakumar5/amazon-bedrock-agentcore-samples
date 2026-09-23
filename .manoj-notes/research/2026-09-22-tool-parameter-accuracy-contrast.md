# Contrast Test: Builtin.ToolParameterAccuracy on the Extractor

**Date:** 2026-09-22

Does `Builtin.ToolParameterAccuracy` catch the extractor putting a value into `submit_expense` that its own input never contained? Before trusting it, seven cases that differ in one thing each, scored on the `submit_expense` call only. Traces from run `dataset-25167e6c`. Results are in `receipts-idp-evaluation/out/contrast-tpa/`.

## What the evaluator is

It judges each **parameter value** of a tool call: can the value be traced to the context the model had before the call? It does not know the true value. So it asks "did the model invent this?", not "is this right?". That makes it a complement to B2 extraction accuracy, not a replacement.

## The cases

| Case | OCR | Submitted | Should say |
|---|---|---|---|
| A: real `duplicate_a` | `2026-06-26` | `2026-06-26` | Yes |
| B: A, submitted date edited | `2026-06-26` | `2026-03-14` | No |
| F: A, submitted total edited | `13.49` | `14.49` | No |
| E: A, OCR and value both edited | `2026-06-21` | `2026-06-21` | Yes (faithful, though B2 would call it wrong) |
| C: real `clean` | no date | `2024-01-01` | No |
| C2: real `injected` | no date | `2024-01-01` | No |
| D: real `pii_heavy` | no date, card expiry `11/29` | `2029-11-01` | No |

## Result 1: on the full trace, it fails 4 of 7

| | A | B | F | E | C | C2 | D |
|---|---|---|---|---|---|---|---|
| Full session trace | Yes, pass | **Yes, fail** | **Yes, fail** | Yes, pass | No, pass | **Yes, fail** | **Yes, fail** |

The judge's reasoning shows why. It accepts the edited date because it "comes from extractor's structured expense", and the invented dates because they are "present in the extracted expense data". Those are the **validator's input and the reviewer note's input**, both written **after** `submit_expense`, and both repeat the extractor's own values. The judge checks the model's output against a copy of itself.

C passed for the wrong reason: the later reviewer-note input happened to say the date was fabricated.

This contradicts the docs, which describe tool-level context as previous turns plus tool calls made before the one under evaluation. In this sample, three agents (extractor, validator, note writer) run inside one session, and the later agents' inputs reach the judge.

## Result 2: on the extractor's part of the trace only, it passes 7 of 7

Cutting the trace at the end of the extractor agent removes the later context.

| | A | B | F | E | C | C2 | D |
|---|---|---|---|---|---|---|---|
| Extractor-only trace | Yes | No | No | Yes | No | No | No |

Every verdict is right, and every "No" names the right field for the right reason:
- B: "OCR clearly states 2026-06-26, but the agent used 2026-03-14".
- F: "14.49 vs OCR's 13.49".
- D: "11/29 is a card expiration date, not a transaction date".

## What this means

1. **The evaluator discriminates, but only when it is shown the right context.** On the traces this sample produces as they are, it does not. That is a finding worth stating plainly in the blog: a judge that reads the whole session can be fooled by the agent's own output being repeated downstream.
2. **The on-demand `Evaluate` API can be given the extractor's spans only.** An online evaluation config scores the session it receives, so it cannot. Making this work live would mean separating the agents in telemetry, for example giving the extractor its own trace. That is a design decision, not yet made.
3. **B2 and ToolParameterAccuracy split the blame, as intended.** E is the case only B2 catches: the OCR is wrong and the model copied it faithfully.

## Caveat: confidence gets flagged too

On C, C2 and D the judge also called `confidence` fabricated, because 72 or 60 does not appear in the OCR (which reports its own 98-99). Confidence is the model's own judgement, not a value to copy. All three verdicts were right anyway, because the date was genuinely invented. But a correct extraction with an honest low confidence may be scored "No" for confidence alone. Test that before quoting a false-positive rate.

## Not scored

It also returns verdicts for `submit_validation` and `save_expense`. On `save_expense` it said "No", because the orchestrator fills rung, status and the S3 path in code. That call is not a model decision, so its verdict is ignored.
