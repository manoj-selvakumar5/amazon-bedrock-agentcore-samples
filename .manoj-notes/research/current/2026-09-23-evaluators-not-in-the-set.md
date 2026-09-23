# Evaluators Not in the Set: For Reference Only

**Date:** 2026-09-23

Everything that was tried, considered or removed and is **not** part of the working evaluator set, with the reason for each. Kept for reference. Nothing here belongs in the summary of what was built.

## Scoreboard metrics with no evaluator

Framework 1 produced these two metrics; neither has an evaluator, on purpose.

| Metric | Meaning | Why no evaluator |
|---|---|---|
| B5 Completion rate | Receipts that finish rather than vanish | A receipt that never arrives leaves nothing in any trace to score. It needs a count of uploads to compare against, which the sample does not keep |
| C3 Data-boundary breaches | Anyone seeing data that is not theirs | Already enforced in code: the user id comes from a signed identity token and is fixed inside the chat tool wrappers, so the model cannot request another user's data. An evaluator would only re-check that code |

## Removed

| Evaluator | Why removed |
|---|---|
| `ReceiptsStpOutcome` (straight-through, as an evaluator) | It only counted statuses, with no right answer to compare against, and routing already sees every outcome. Straight-through rate is now a reported count |
| `ReceiptsThresholdBreach`, original form | Removed as a tripwire that re-checked the Cedar rule with Cedar's own input. It later came back in a different role, as the control monitor `ReceiptsThresholdControl` |

## Parked

| Evaluator | Status |
|---|---|
| `Builtin.TrajectoryInOrderMatch` | The receipt pipeline's step order is fixed in plain Python. When the validator is shed or does not report, the code sends the receipt to review, so "saved without the validator" cannot happen. It passed 9/9 by construction. Adding the expected terminal tool turned it into a copy of routing (4/9). It **still runs by default** in `score_saved.py` and `run_evaluators.py` |

Designs considered to give it a real job, and rejected:
- **An investigating validator** with optional policy, merchant and history lookups. Forced: a short policy belongs in the prompt, merchant normalisation should always run in code, and history checks are controls that must always run.
- **A velocity step** the agent must perform. Designed only so the matcher would have something to check; the check belongs in the Lambda.
- **The read-only chat assistant.** Its tools are independent, so order has no job. It would only check "did it look at all".
- **A candidate for later:** an append-only `add_note_to_held_expense` chat tool, letting the employee answer the reviewer. Natural, but it reverses the chat's read-only decision (ADR-0016). It mainly catches "claimed an action it never took", and cannot catch a wrong expense id.

## Opt-in evidence only (failed or measured nothing)

| Evaluator | How it runs | What happened |
|---|---|---|
| `Builtin.GoalSuccessRate` asserting the $2,000 rule | `run_evaluators.py --evaluator` | Passed on a $15.90 receipt because the rule never engaged. The same green means "obeyed" and "not applicable", at 2,428 judge tokens, for a question code answers exactly |
| `ThirdParty.DeepEval.ToolUse` | `run_evaluators.py --evaluator` | Scored a correct run 0.25 and called the save "unauthorized", assuming a user who asked for something. 6,014 judge tokens |
| `ThirdParty.DeepEval.PIILeakage` | `score_saved.py --with-judges` | Scored in the wrong direction: the note near a real card number and address scored cleanest (0.17), an ordinary coffee note 0.33. The card number appeared nowhere in the output |
| `ThirdParty.AutoEval.Security` | `score_saved.py --with-judges` | Called every normal reviewer note malicious, reading the note's own instruction to the reviewer as an injection. Its only "not malicious" verdict was on the receipt near real personal data |

## Considered and ruled out

**Built-in:**

| Evaluator | Reason |
|---|---|
| `Helpfulness`, `ResponseRelevance`, `Coherence`, `Conciseness` | The pipeline has no user. On chat they judge style, not a decision with a right answer |
| `InstructionFollowing` | Checks instructions in the user's input only. The reviewer note's rules live in the system prompt, which the judge does not see (confirmed on a real trace) |
| `Refusal` | On chat a wrong refusal already fails completeness and correctness; the pipeline models never refuse |
| `Harmfulness`, `Stereotyping` | Nothing in this product produces either |
| `ToolSelectionAccuracy` on the pipeline | Each pipeline agent has one tool |
| `SkillSelectionAccuracy`, `SkillInstructionFollowing` | No skills in this sample |
| `TrajectoryExactOrderMatch`, `TrajectoryAnyOrderMatch` | Same fixed-workflow problem as InOrder |
| `Faithfulness` on the reviewer note or chat, `ToolSelectionAccuracy` and `ToolParameterAccuracy` on chat | Valid candidates, not built |

**Third-party: all 13 managed evaluators.** They take no ground truth and no parameters.

| Evaluator | Verdict |
|---|---|
| DeepEval Bias, Toxicity | Nothing here produces opinions or toxic output |
| DeepEval PIILeakage | Failed (above) |
| DeepEval Summarization | Would duplicate `Faithfulness`; the note is a justification, not a summary |
| DeepEval TaskCompletion, TurnRelevancy | Would duplicate goal success and relevance judges |
| DeepEval ToolUse | Failed on the pipeline. On chat it would duplicate tool selection plus tool parameters |
| DeepEval ConversationCompleteness, KnowledgeRetention | No fit on single-turn chat; **adopted** once multi-turn chat was built |
| DeepEval GoalAccuracy | Same job as ConversationCompleteness; one of the two, and that one was chosen |
| AutoEval Security | Failed (above) |
| AutoEval Humor | No decision about humour |
| AutoEval Possible | Scores any non-refusal as "attempted", so an invented answer still passes |

## Considered and not built

- **A live override guard:** how often the validator overrides a confident extractor. The architecture view should guard the business view against being gamed: the straight-through rate rises if the validator simply stops disagreeing, and this count would show it. Planned, not built.
- **More labelled data:** roughly 30-50 receipts and 15-20 conversations, for quotable rates.
- **Shipping the evaluators in the sample's `agentcore.json`**, replacing the copied set. Blocked: the CDK stack source was never committed.
- **Recording reviewer decisions** (a `resolve_review` tool) and spot-auditing auto-saved receipts. Both would give the labelled evaluators real answers on live traffic.
- **A deployment** to run the Cedar boundary tests and settle whether totals with cents are blocked.
- **Correctness on the receipt pipeline:** extraction accuracy and routing already cover it deterministically.
