# Receipts IDP Evaluation Revamp: The Whole Story So Far

**Date:** 2026-09-18

Written to be read cold. It covers why the work started, the two frameworks that shaped it, what was built, what the real runs found, and what is still open.

## 1. The goal

Use the receipts IDP sample as the worked example for a blog on choosing AgentCore evaluators, with code that actually runs behind every claim.

## 2. Where the sample started

`agentcore/agentcore.json` ships four evaluators and nothing else.

| Item | State |
|---|---|
| `ReceiptsExtractionQualityEvaluator` | SESSION LLM judge, 1 to 5, blending extraction, reconciliation, category, routing and confidence into one score |
| Online config | `Builtin.Helpfulness`, `Builtin.Correctness`, `Builtin.ToolSelectionAccuracy`, sampling 100 |
| Golden dataset | none |
| Regression gate | none |
| Threshold, alarm or CI consumption of scores | none |

Two things stood out immediately. The same three built-ins appear verbatim in the sibling claims sample, so the set was copied rather than chosen. And the extraction pipeline has no conversation at all: an S3 event triggers it, so `Helpfulness` scores a machine-to-machine payload against an absent user.

## 3. The two frameworks

**Framework 1 works backwards from the business.** Three questions: why does this agent exist, what would you measure regardless of the implementation, and how do those translate into evaluators at the right level.

The middle question does the work, applied as a swap test: **state the metric without naming the agent, its model or its tools.** If you cannot, it is not a business metric. Operationally, imagine replacing the agent with a rules engine, an offshore data-entry team, or a person typing receipts in by hand, and ask whether the number still exists.

**Framework 2 works forwards from the architecture.** Identify the failure modes this particular design makes likely, then pick evaluators that catch those.

**How they compose**, which was my synthesis rather than received wisdom:

- Backwards sets the scoreboard. Forwards supplies the explanation. Every scoreboard metric needs at least one diagnostic that can explain a movement in it.
- Forwards guards backwards against the architecture gaming it. Straight-through processing improves if the validator stops disagreeing, and the dual-agent design makes exactly that likely, so validator disagreement becomes a guard on the headline number.
- Production closes the loop. Neither framework enumerates failures nobody imagined, which is what failure clustering is for.

## 4. Framework 1 applied

**Extraction**, seven metrics survived the swap test.

| | Metric | What it owns |
|---|---|---|
| B1 | Straight-through processing rate | Whether any manual work was actually replaced |
| B2 | Dollar-weighted extraction error | How many dollars posted wrong, not how many fields |
| B3 | Control breach count | The rules an auditor tests. Target zero |
| B4 | Review-queue precision | Whether the escape hatch is worth staffing |
| B5 | Completion rate | Receipts that vanish leave no bad output to catch |
| B6 | Cost per receipt | Whether it beats the clerk it replaced |
| B7 | Degraded-volume share | How much data came from a fallback model |

**Chat**, run later and separately, because the chat path had only ever been given one line.

| | Metric |
|---|---|
| C1 | Self-service resolution rate |
| C2 | Answer accuracy |
| C3 | Data-boundary breaches |
| C4 | Cost per question |

Things the filter rejected, and why they still matter: `Helpfulness`, `KnowledgeRetention`, `TurnRelevancy` and confidence calibration all presuppose the mechanism. They are Framework 2 diagnostics, not scoreboard metrics.

## 5. The discovery that blocked everything

Evaluators read the trace. The receipts trace ended at the validator's opinion.

`save_expense` and `human_review` are orchestrator MCP calls made after both agents finish, not Strands agent tools, so nothing traced them. A correct auto-save looked like a skipped step. Any evaluator asking "was this receipt handled correctly" was blind, whatever it was called.

That reordered the work: the code had to change before the evaluators could mean anything.

## 6. What was built

| Stage | What | Outcome |
|---|---|---|
| 0 | Local harness plus a FastMCP stand-in for the Gateway, so the real pipeline runs on a laptop with no deployment | Captured the first trace and confirmed the save was missing |
| 1 | Tool spans for the save and review calls, and the outcome stamped on the invocation span | 14 spans, root status OK, the write finally visible |
| 1b | Review fixes: `receipts.s3_uri`, outcome tagging on every terminal path, a lint nit | Deferred and failed receipts no longer drop out of the denominator |
| 1c | A real bug found while verifying: the Textract client had no region, so it used the profile default and could not read a bucket in another Region | Fixed through the config seam |
| 2 | Scored the saved trace through the `Evaluate` API | Proved the service reads a hand-emitted span as a tool call |
| 3 | Seven labelled receipts, four code-based evaluators, a cross-receipt check, and a reviewer note with two safety judges | Five business metrics producing numbers |

## 7. The labelled receipt set

Built around the failures, not the happy path.

| Fixture | What it tests |
|---|---|
| `clean` | The control case. Anything but an auto-save is a false alarm |
| `non_reconciling` | Subtotal plus tax plus tip does not equal the total |
| `over_threshold` | 2,400.00, which must never save automatically |
| `duplicate_a` and `duplicate_b` | One purchase submitted twice |
| `split_a` and `split_b` | One 2,400.00 dinner split across two checks, 1,250 and 1,150 |

The last two pairs are deliberately correct in isolation. The failure exists only across receipts, which is the point.

## 8. What the runs produced

| Receipt | Expected | Actual | Routing outcome |
|---|---|---|---|
| clean | processed | needs_review | FalseAlarm |
| non_reconciling | needs_review | needs_review | ReviewCorrect |
| over_threshold | needs_review | needs_review | ReviewCorrect |
| duplicate_a | processed | processed | AutoPersistCorrect |
| duplicate_b | needs_review | processed | **FalseClear** |
| split_a | processed | needs_review | FalseAlarm |
| split_b | needs_review | needs_review | ReviewCorrect |

| Metric | Value |
|---|---|
| B1 straight-through processing | 29% |
| B2 dollar-weighted error | 0.00% |
| B3a threshold breaches | 0 |
| B4 review-queue precision | 60%, three of five escalations were needed |
| B4 false-clear exposure | 13.49 committed without a check |
| B3d process integrity | 7 of 7, the validator ran before every write |

## 9. What the runs found

1. **A duplicate auto-saved at confidence 97 and destroyed the earlier record.** The sample's dedup is a content hash plus `put_item`, so the second write overwrites the first. That is data loss presented as deduplication, and only a cross-receipt check can see it.
2. **The policy stopped a 2,400 charge the model wanted to commit.** The validator said auto-persist at confidence 97 and the deterministic control denied it. The sample's central design claim, demonstrated rather than asserted.
3. **Dollar error read 0.00% while the agent fabricated a date.** Textract returned no date for the rendered receipt, and the model invented `2024-01-01` rather than reporting absence. The metric is tight for dollars and blind to dates, and the thing that caught it was the validator, a workflow component, not an evaluator.
4. **The split evasion did not happen, but not because the control worked.** Both halves were escalated because the validator distrusted a large dinner with no tip. The 2,000 rule never engaged. The control held for an unintended reason.
5. **The agent is over-cautious.** Two of five escalations were unnecessary, which is the cost side of a safety record that looks perfect.

## 10. What the evaluators themselves showed

| Evaluator | Type | Result |
|---|---|---|
| `Builtin.TrajectoryInOrderMatch` | built-in, programmatic | 7 of 7 on its own claim, at zero judge cost |
| Code-based B1, B2, B3a, B4 | code-based | Carried every business number above |
| Cross-receipt duplicate and split check | analysis, not a registered evaluator | Found the overwrite |
| `Builtin.GoalSuccessRate` with assertions | built-in judge | Passed at 2,428 tokens because a 15.90 receipt never engaged the 2,000 rule |
| `ThirdParty.DeepEval.ToolUse` | third-party judge | 0.25 on a correct run, calling the write "unauthorized" |
| `ThirdParty.DeepEval.PIILeakage` | third-party judge | 0.33, flagging the note's required content as a privacy violation |
| `ThirdParty.AutoEval.Security` | third-party judge | "Malicious" on both clean notes, calling the note's own instruction to the reviewer a prompt injection |

The pattern: **the deterministic evaluators did the work, and the judges returned plausible numbers about something else.** No third-party metric has yet been shown to own a business outcome here, and three have been shown not to.

## 11. What was rejected, and why

| Rejected | Reason |
|---|---|
| `Summarization` on the reviewer note | Scores a summary against a source. The note is a justification of a routing decision, so it can score well while never naming the concern |
| `GoalSuccessRate` as a measurement | A probabilistic instrument for a deterministic question, and it returns the same green for "obeyed" and "not applicable" |
| Velocity enforced by the agent passing a total into the policy | Designed so a step would exist so the trajectory matcher would have a job. The check belongs in the Lambda where it cannot be skipped |
| A pattern scan for injected content in the note | Misses pure social engineering, which is the more dangerous payload. The control belongs in the design: build the note from validated fields |
| Cost per receipt, in its partial form | Excludes reviewer time, which dominates the escalated path, so the number invites the conclusion that automation is cheap |

Two of those were cases of forcing the product to fit a metric. Worth keeping visible, because the pull toward metric-chasing showed up even while writing the argument against it.

## 12. Current state

| | |
|---|---|
| Business metrics producing numbers | 5: B1, B2, B3, B4 offline, plus process integrity |
| Evaluators run against real traces | 8 |
| High-priority items implemented | 6 of 6 |
| Blocked on product gaps | B4 in production needs `resolve_review`, B5 needs an upload count, the chat metrics need multi-turn sessions |
| Open experiment | The two fixtures that settle whether the security judges discriminate |

## 13. Honest caveats

- Seven synthetic receipts, one run, one model. An existence proof, not a measurement.
- The fabricated date depends on Textract returning no date for a rendered receipt. The behaviour is real, the trigger is fixture-specific.
- Cedar was a local stand-in, not the deployed policy engine. It reproduced the deny path faithfully; the real one is untested.
- **Nothing is deployed.** The sample cannot deploy as shipped: `agentcore/cdk/lib/` was never committed, upstream included, because the repo's root `.gitignore` has a blanket `lib/` rule and this sample was never given the exception its sibling has.

## 14. Where it lives

Branch `receipts-idp-eval-revamp`, folder `02-use-cases/02-workflow-automation-agents/receipts-idp-evaluation`.

| File | Purpose |
|---|---|
| `capture_trace.py` | Run one receipt, save the trace |
| `local_gateway.py` | Stand-in for the Gateway, including the policy block |
| `make_fixtures.py`, `fixtures/` | The labelled receipt set |
| `run_dataset.py` | All seven receipts, scored end to end |
| `score_saved.py` | Re-score saved traces without re-running the agent |
| `evaluators/business_outcomes.py` | B1, B2, B3a and B4 in one Lambda |

Reasoning behind each decision is in the other notes in this folder, including the metric-to-evaluator pairings with priorities, the chat-workload metrics, and the feature-adoption survey.
