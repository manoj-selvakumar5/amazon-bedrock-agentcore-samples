# Blog Outline: Choosing AgentCore Evaluators

**Date:** 2026-09-23
**Status:** outline for approval; prose comes after the arc is agreed.

## The one-sentence argument

Pick evaluators by working backwards from what the business needs and forwards from how the agent can fail, then trust none of them until you have shown each one can tell good from bad. Most evaluators that look reasonable fail that test.

## Reader

Builders who have an agent on AgentCore and a list of built-in and third-party evaluators, and do not know which to switch on. The receipts sample is the worked example. Every number comes from code in the branch.

## Working title options

- Choosing AgentCore Evaluators: A Worked Example That Rejects Most of Them
- Your Evaluators Are Confident. Are They Right?
- Start From the Business, Test the Judge: Choosing Evaluators for an AgentCore Agent

---

## 1. The hook: a sample that shipped the wrong evaluators

**Claim:** the default instinct, switching on generic judges, produces confident numbers about nothing.

**Evidence:**
- The sample's `agentcore.json` ran `Helpfulness`, `Correctness` and `ToolSelectionAccuracy` online. They were copied verbatim from a sibling sample.
- `Helpfulness` was scoring an S3-triggered pipeline that has no user.
- Later in the story, a judge scores a wrong answer 1.0, which pays this off.

**Source:** 2026-09-18 story-so-far, section 2.

## 2. The worked example

**Claim:** two workloads, deliberately different.

- **Receipt pipeline:** Textract OCR, then an extractor agent, then an independent validator agent. Code saves the expense or sends it to human review, and a Cedar policy blocks any automatic save of $2,000 or more. A note writer explains each hold to the reviewer.
- **Chat assistant:** read-only, answering an employee's questions about their own expenses. Made multi-turn during this work.

**Visual:** one diagram of both paths, marking where each evaluator reads.

## 3. Framework 1: work backwards from the business

**Claim:** a metric that cannot be stated without naming the agent is not a business metric.

- **The swap test:** replace the agent with a person typing receipts in by hand. Does the number still exist?
- **The scoreboard it produces:**
  - B1 straight-through rate
  - B2 dollar-weighted error
  - B3 control breaches, target zero
  - B4 review-queue precision
  - B5 completion
  - C1 self-service resolution
  - C2 answer accuracy
  - C3 data-boundary breaches
- **What it rejects:** `Helpfulness`, `KnowledgeRetention` and confidence calibration all presuppose the mechanism. They are Framework 2 material.

**Source:** 2026-09-16 feasibility, 2026-09-17 chat workload.

## 4. Framework 2: work forwards from the architecture

**Claim:** each design makes particular failures likely. Evaluators aimed at those failures are the diagnostics that explain why a scoreboard number moved.

**How the two compose:**
- Every scoreboard metric needs a diagnostic under it.
- Framework 2 guards Framework 1 against being gamed. Example: the straight-through rate rises if the validator stops disagreeing.
- Production closes the loop, because neither framework lists failures nobody imagined.

## 5. Before any evaluator: make the trace tell the truth

**Claim:** evaluators read the trace and nothing else. If the business action is not in the trace, every evaluator is blind.

**Evidence:**
- The save and review calls were orchestrator code, not agent tools, so they were never traced. A correct receipt looked like a skipped step.
- The fix went into the agent, not the test harness, because deployed traces have the same gap.

**Source:** 2026-09-17 Stage 1 and Stage 2 notes.

## 6. Three rules for a legitimate evaluator

1. **It judges a decision a model makes, against a right answer or a clear reference.** Re-checking a control the code already enforces tells you nothing about the agent. A control monitor is the one labelled exception (section 8).
2. **One question, one evaluator.** No two evaluators doing the same job in different ways.
3. **Contrast-test every judge before trusting it.** Build pairs of cases that differ in one thing, and require the verdict to flip.

Plus the product rule: change the product only in ways a team would build anyway.

## 7. The evaluators that survived: 8, each with its contrast result

| Scoreboard metric | Evaluator | Kind | Contrast | Runs |
|---|---|---|---|---|
| B2 | Extraction accuracy | code | deterministic | labelled |
| B2, diagnostic | ToolParameterAccuracy (invented values) | built-in | 7/7 on the extractor's part of the trace | offline |
| B4 | Routing outcome | code | deterministic | labelled |
| B4, diagnostic | GoalSuccessRate with per-receipt assertions (right reason) | built-in | 14/14 | offline |
| B3 | Threshold control monitor | code | policy switched off: breach caught | live |
| C1 | ConversationCompleteness | third-party | 1.0 to 0.67 | live |
| C1, diagnostic | KnowledgeRetention | third-party | 1.0 to 0.67, but noisy | live |
| C2 | Correctness with expected answers | built-in | 10/10 | labelled |

B1 is reported as a count, not an evaluator. B5 cannot be measured. C3 is enforced in code.

**Source:** 2026-09-22 pruning note and the four contrast notes.

## 8. The ones that did not make it, and why

This is the evidence section, and it carries the argument.

| Evaluator | What happened |
|---|---|
| `GoalSuccessRate` on the $2,000 rule | Passed because a $15.90 receipt never engaged the rule. Green means both "obeyed" and "not applicable" |
| DeepEval `ToolUse` | Scored a correct run 0.25 and called the save "unauthorized" |
| `PIILeakage`, AutoEval `Security` | Called every normal note malicious, and scored the note near real personal data as the cleanest |
| `TrajectoryInOrderMatch` | On a fixed workflow the order cannot go wrong, so 9/9 was guaranteed by construction |
| Redesigns proposed to give it a job | Rejected as forced: the investigating validator, the velocity step |
| All 13 managed third-party evaluators | None fits a single-turn workload. Two fit after multi-turn chat was built for its own reasons |

**The Cedar reversal:** the threshold check was cut as a tripwire, then brought back, because watching that a hard control still holds in production is a legitimate job. The lesson is to name what an evaluator measures, not to ban the category.

## 9. Traps nobody warns you about

This is the most original section.

1. **The whole-session trap.** In one trace holding three models, `ToolParameterAccuracy` checked the extractor's output against the validator's copy of it, and failed 4 of 7 cases. Cut to the extractor's part of the trace, it passed 7 of 7. That contradicts the documented context scope.
2. **Double counting.** One extractor mistake was counted by extraction accuracy **and** blamed on the validator as a false alarm. Judging the validator on what it was shown moved precision from 33% to 83%.
3. **A judge that caught a bug in the evaluation design.** The "reprint" assertion failed because OCR drops free text, so the validator never saw the reprint mark. The label was wrong, not the agent.
4. **Judges that penalise the right behaviour:**
   - `ToolParameterAccuracy` flagged the model's honest low confidence as invented.
   - `ConversationCompleteness` scored a correct refusal as half met.
5. **Judges without ground truth cannot see a wrong answer.** `ConversationCompleteness` scored 1.0 on a wrong answer. `Correctness` with an expected answer caught it.
6. **Noise.** `KnowledgeRetention` gave the same trace 0.67 once and 1.0 twice.

## 10. What the evaluators found in the agent (kept unfixed as evidence)

| Finding | Caught by |
|---|---|
| Invented dates on 3 of 9 receipts, while dollar error read 0.00% | Extraction accuracy (fields) and ToolParameterAccuracy (the model, not the OCR) |
| A duplicate receipt silently overwriting the first, data loss presented as deduplication | Cross-receipt check |
| A split bill held for an unrelated reason: the control held by accident | Reading routing with the reasons |
| Cedar stopping a $2,400 save the validator approved at 97, the sample's central claim | Threshold control and the routing labels |
| Chat's "most recent expense" wrong: the tool promises newest first but sorts by a hash | Correctness |
| Reconciliation enforced only by a prompt, not in code | Code reading, prompted by the metrics |
| Open question: whether totals with cents are blocked by the deployed policy | Boundary tests written, not yet run |

## 11. Offline versus live

**Claim:** say which evaluators can watch production and which cannot, and why.

- **Live today:**
  - threshold monitor
  - ConversationCompleteness
  - KnowledgeRetention
- **Offline only:**
  - the labelled ones
  - ToolParameterAccuracy, because of the trace trap
- **What would unlock more:** recording reviewer decisions (`resolve_review`), and spot-audits of auto-saved receipts. Both are natural product changes.

## 12. Honest limits

- 9 receipts and 11 chat turns: existence proofs, not rates.
- Synthetic receipts, one model, and nothing deployed. Cedar ran as a local stand-in.
- The sample cannot deploy as shipped: its CDK stack source was never committed.

## 13. Takeaways: a checklist for the reader

1. Write the scoreboard before opening the evaluator list.
2. For each architecture failure mode, pick one diagnostic.
3. Make sure the trace contains the business action.
4. Contrast-test every judge, and keep the failures as evidence.
5. Check what the judge actually sees in a multi-agent trace.
6. Name what each evaluator measures: agent quality, or control health.

---

## Decisions already made that shape the post

- Agent failures and product bugs stay unfixed as evidence.
- Trajectory evaluation is parked, and appears only in section 8.
- The four failed judges are kept, opt-in, as evidence.

## Open for you to decide before prose

- Title, and whether the chat half is a full section or a shorter second act.
- Length target. The outline supports about 3,000 to 4,000 words; sections 9 and 10 could be cut into a follow-up post.
- Whether to show code excerpts, for example the contrast-test pattern, or only link to the branch.
