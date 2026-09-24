# Blog Outline: Choosing AgentCore Evaluators

**Date:** 2026-09-23, updated 2026-09-24 after the sample was deployed to AgentCore.
**Status:** outline for approval; prose comes after the arc is agreed.

## The one-sentence argument

Pick evaluators by working backwards from what the business needs and forwards from how the agent can fail, then trust none of them until you have shown each one can tell good from bad. Most evaluators that look reasonable fail that test.

## Reader

Builders who have an agent on AgentCore and a list of built-in and third-party evaluators, and do not know which to switch on. The receipts sample is the worked example. It is deployed to AgentCore, and every number comes from code in the branch and runs against the deployed stack.

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

- **Receipt pipeline:** Textract OCR, then an extractor agent, then an independent validator agent. The validator acts on its decision by calling one of two tools, `approve_expense` or `send_to_review`. The tools are pinned to the extractor's expense, so the validator chooses the outcome but cannot change what is saved. A Cedar policy at the Gateway blocks any automatic save of $2,000 or more. A note writer explains each hold to the reviewer.
- **Chat assistant:** read-only, answering an employee's questions about their own expenses. Made multi-turn during this work, and given its own Runtime so each live evaluation config scores only its own traffic.

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
- The save and review calls were orchestrator code, not agent tools, so they were never traced. A correct receipt looked like a skipped step. The first fix stamped the outcome on the trace from the agent, not the test harness, because deployed traces have the same gap.
- The second fix moved the action into the agent. The validator now calls `approve_expense` or `send_to_review` itself, so the decision is traced as the validator's own tool call, with the Gateway's save or review call beneath it. Code still guarantees one decision only, review when there is no decision or the system is degraded, and review when Cedar denies.
- **The deployed agent exported no traces at all.** The container started without the OpenTelemetry wrapper, a bug inherited from the upstream sample. Every evaluator, live or offline, was blind to the deployed agent until the Dockerfile was fixed.

**Source:** 2026-09-17 Stage 1 and Stage 2 notes; the sample's ADR-0019; 2026-09-23 deployed-sample note.

## 6. Three rules for a legitimate evaluator

1. **It judges a decision a model makes, against a right answer or a clear reference.** Re-checking a control the code already enforces tells you nothing about the agent. A control monitor is the one labelled exception (section 8).
2. **One question, one evaluator.** No two evaluators doing the same job in different ways.
3. **Contrast-test every judge before trusting it.** Build pairs of cases that differ in one thing, and require the verdict to flip. Test again whenever the agent's trace changes shape.

Plus the product rule: change the product only in ways a team would build anyway.

## 7. The evaluators that survived: 8, each with its contrast result

| Scoreboard metric | Evaluator | Kind | Contrast | Runs |
|---|---|---|---|---|
| B2 | Extraction accuracy | code | deterministic | labelled |
| B2, diagnostic | ToolParameterAccuracy (invented values) | built-in | 7/7 on the extractor's part of the trace | labelled |
| B4 | Routing outcome | code | deterministic | labelled |
| B4, diagnostic | GoalSuccessRate with per-receipt assertions (right reason) | built-in | 14/14; after the validator moved to tools, 8/8 on a local trace and 8/8 on a deployed one | labelled |
| B3 | Threshold control monitor | code | policy switched off: breach caught | live |
| C1 | ConversationCompleteness | third-party | 1.0 to 0.67 | live |
| C1, diagnostic | KnowledgeRetention | third-party | 1.0 to 0.67, but noisy | live |
| C2 | Correctness with expected answers | built-in | 10/10 | labelled |

B1 is reported as a count, not an evaluator. B5 cannot be measured. C3 is enforced in code.

**All three code evaluators are deployed as Lambdas,** and AgentCore itself was shown to give the same answers as the local code: 18 of 18 on the deployed receipt traces, and 13 of 13 in a live test covering every label. The live chat scores match the harness scores exactly.

**Source:** 2026-09-22 pruning note, the four contrast notes, 2026-09-23 evaluation summary.

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
2. **The borrowed-credit trap.** Once the validator acted through its own tools, the note writer ran inside the validator's call. With the validator's concern replaced by "please check this receipt", the right-reason judge scored **No** on the validator's part of the trace and **Yes** on the whole trace, because the note writer's note named the $8 gap. A judge credits whoever in the trace said the right thing. The fix selects each agent's part of the trace by name, and it was re-proven with a contrast test.
3. **Double counting.** One extractor mistake was counted by extraction accuracy **and** blamed on the validator as a false alarm. Judging the validator on what it was shown moved precision from 33% to 83%.
4. **A judge that caught a bug in the evaluation design.** The "reprint" assertion failed because OCR drops free text, so the validator never saw the reprint mark. The label was wrong, not the agent.
5. **Judges that penalise the right behaviour:**
   - `ToolParameterAccuracy` flagged the model's honest low confidence as invented.
   - `ConversationCompleteness` scored a correct refusal as half met.
6. **Judges without ground truth cannot see a wrong answer.** `ConversationCompleteness` scored 1.0 on a wrong answer. `Correctness` with an expected answer caught it.
7. **Noise.** `KnowledgeRetention` gave the same trace 0.67 once and 1.0 twice.
8. **A control that holds for the wrong reason.** On the deployed stack, the $2,400 receipt was blocked and the threshold monitor reported "held". But Cedar was denying every save, whatever the amount, because of a type error (section 10). The monitor was right that the money was held and could not see why. Only boundary tests with small totals showed the rule never ran.
9. **Deployment changes what the evaluator is handed.**
   - The live path calls a code evaluator's Lambda without its name, while the on-demand path passes it. An evaluator that routed on its name returned `UNKNOWN_EVALUATOR` live until each got its own entry point.
   - Spans reach CloudWatch over minutes. Scoring as soon as any spans exist scores a partial trace.
   - Deployed traces put the outcome and the messages in different places than local ones. Trimming and contrast tests had to be checked on both.

## 10. What the evaluators found in the agent (kept unfixed as evidence, except one)

| Finding | Caught by |
|---|---|
| Invented dates on 2 to 3 of 9 receipts per run, while dollar error read 0.00% | Extraction accuracy (fields) and ToolParameterAccuracy (the model, not the OCR) |
| A duplicate receipt silently overwriting the first, data loss presented as deduplication | Cross-receipt check |
| A split bill approved on one run and held for an unrelated reason on another: the validator sees one receipt at a time and cannot see the split | Reading routing with the reasons |
| Cedar stopping a $2,400 save the validator approved, the sample's central claim | Threshold control and the routing labels |
| **The deployed Cedar policy denied every automatic save, of any amount.** Totals like 15.9 reach Cedar as decimals, the rule compared a whole number, and a forbid policy that errors denies. Straight-through rate was zero by construction. **Fixed**, because a product that cannot save anything is not evidence of agent behaviour: saves now carry integer cents | Boundary tests, and routing labels that showed approved receipts landing in review |
| Chat's "most recent expense" wrong: the tool promises newest first but sorts by a hash | Correctness |
| Chat restating a 24 to 27 June trip as 24 to 26. The answers were still right, because no meal fell on the 27th | KnowledgeRetention, live and offline |
| Reconciliation enforced only by a prompt, not in code | Code reading, prompted by the metrics |

## 11. Offline versus live

**Claim:** say which evaluators can watch production and which cannot, and why.

- **Live today, on the deployed stack:**
  - threshold monitor, on every pipeline session
  - ConversationCompleteness and KnowledgeRetention, on every chat session
- **Offline only:**
  - the labelled ones, which need a right answer production does not have
  - ToolParameterAccuracy, because of the whole-session trap: an online config scores the whole session
- **Live results carry noise that is not a failure.** A chat request with a rejected identity token produces an evaluation error ("no spans with supported scope names"), because no agent ran and there was nothing to judge.
- **What would unlock more:** recording reviewer decisions (`resolve_review`), and spot-audits of auto-saved receipts. Both are natural product changes.

## 12. Honest limits

- 9 receipts and 11 scored chat turns: existence proofs, not rates. Routing precision moved from 71% to 67% between two deployed runs of the same receipts, from the validator's run-to-run variation alone.
- Synthetic receipts and one model.
- Traces from before the agents were named cannot be rescored with the current trimming.

## 13. Takeaways: a checklist for the reader

1. Write the scoreboard before opening the evaluator list.
2. For each architecture failure mode, pick one diagnostic.
3. Make sure the trace contains the business action, and that the deployed agent exports it at all.
4. Contrast-test every judge, and keep the failures as evidence.
5. Check what the judge actually sees in a multi-agent trace, and check again when the trace changes shape.
6. Name what each evaluator measures: agent quality, or control health.
7. Verify on the deployed stack, not only locally. The Cedar type error and the missing traces existed only there.

---

## Decisions already made that shape the post

- Agent failures and product bugs stay unfixed as evidence. The one exception is the Cedar type error, fixed because it blocked every save.
- Trajectory evaluation is parked, and appears only in section 8.
- The four failed judges are kept, opt-in, as evidence.
- The validator acts on its decision through pinned tools (the sample's ADR-0019). The post can use this as the example of an agent that decides and acts while code keeps every guarantee.

## Open for you to decide before prose

- Title, and whether the chat half is a full section or a shorter second act.
- Length target. The outline supports about 3,000 to 4,000 words; sections 9 and 10 could be cut into a follow-up post.
- Whether to show code excerpts, for example the contrast-test pattern, or only link to the branch.
- Whether deployment gets its own section, or stays spread across sections 5, 9 and 10 as it is here.
