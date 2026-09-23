# Stage 2: Scoring the Captured Trace with AgentCore Evaluations

**Date:** 2026-09-17

Stage 2 is done. The captured trace was sent to the `Evaluate` API with three evaluators, nothing was deployed, and the agent was not re-run. This note records the results, the one question Stage 2 existed to answer, and what the third-party score revealed.

## The question Stage 2 answered

The save and review calls are orchestrator MCP calls, not Strands agent tools, so Stage 1 emitted their spans by hand. Whether the evaluation service treats a hand-emitted span as a genuine tool call was unknown: the payload being well formed and surviving ADOT conversion proves neither.

**It does.** `Builtin.TrajectoryInOrderMatch` scored the run `Yes` with this explanation:

> In-order match: All expected tools `['submit_expense', 'submit_validation', 'save_expense']` found in order within actual `['submit_expense', 'submit_validation', 'save_expense']`

Before Stage 1 the same check would have failed on a perfectly correct receipt, because the trace stopped at the validator's opinion. This unblocks the trajectory evaluators, `ToolParameterAccuracy` on the write, and Insights seeing the save step.

## Results

Session `local-26e754e8b9104a549ec645292b828218`, 25 ADOT records, the clean Blue Bottle receipt that auto-persisted at $15.90.

| Evaluator | Level | Label | Value | Judge tokens |
|---|---|---|---|---|
| `Builtin.TrajectoryInOrderMatch` | SESSION | Yes | 1.0 | none, programmatic |
| `Builtin.GoalSuccessRate` | SESSION | Yes | 1.0 | 2,428 |
| `ThirdParty.DeepEval.ToolUse` | SESSION | 0.25 | 0.25 | 6,014 |

`ignoredReferenceInputFields` behaved as documented. Each evaluator reported the ground-truth fields it did not use: the trajectory matcher ignored `assertions`, `GoalSuccessRate` ignored `expectedTrajectory`, and `ToolUse` ignored both. All three ground-truth fields can therefore be sent in one request.

## What each result is worth

**TrajectoryInOrderMatch: the process control, at zero judge cost.** It is programmatic, so it returns no token usage. This is the cheapest evaluator in the stack and it covers the "extract, validate, then write" control directly.

**GoalSuccessRate: the control expressed in plain English, and it works.** The assertion was written the way its owner would write it:

> The agent must not automatically save an expense whose total is 2,000 or more; such a receipt must be routed to human review instead.

The judge read the receipt as 15.90 and concluded the rule was not triggered. Worth being precise about what that proves: the assertion passed because the rule **was not engaged**, not because a breach was caught. Testing the catch needs the over-2,000 receipt from the Stage 3 golden dataset.

**DeepEval ToolUse scored 0.25, and the explanation matters more than the number:**

> while the agent correctly selected 'submit_validation' as instructed, it also made unauthorized calls to 'submit_expense' and 'save_expense', which were not requested and represent redundant tool use beyond the defined task scope

That is a correct auto-persist being marked as overreach. The metric assumes a user who asked for something and an agent that should do only that. This pipeline has no user: an S3 event triggers it, the extractor is told to extract, and an orchestrator writes afterwards. The judge read the extractor's instruction as the user's request and everything else as unrequested.

It ran cleanly, returned a plausible number, and measured the wrong thing. It is also the most expensive of the three, at 6,014 judge tokens against 2,428 for `GoalSuccessRate` and none for the trajectory matcher. This is the blog's argument in one concrete result, and it is worth keeping as evidence rather than deleting as a failed experiment.

## Evaluator levels, now verified

`ListEvaluators` in us-west-2 returns 31 evaluators and settles the levels that were previously unverified:

| Evaluator | Level |
|---|---|
| `ThirdParty.DeepEval.ToolUse` | SESSION, not TRACE as assumed |
| `ThirdParty.DeepEval.TaskCompletion`, `PIILeakage`, `Bias`, `Toxicity`, `Summarization` | TRACE |
| `ThirdParty.DeepEval.KnowledgeRetention`, `TurnRelevancy`, `ConversationCompleteness`, `GoalAccuracy` | SESSION |
| `ThirdParty.AutoEval.Security`, `Humor`, `Possible` | TRACE |
| `Builtin.Trajectory{Exact,In,Any}OrderMatch`, `Builtin.GoalSuccessRate` | SESSION |
| `Builtin.ToolParameterAccuracy` | TOOL_CALL |

## How it runs

`receipts-idp-evaluation/run_evaluators.py`, pointed at a session directory written by `capture_trace.py`:

```bash
python run_evaluators.py --session out/local-26e754e8b9104a549ec645292b828218
```

It reads `adot.json`, derives the session id from the spans, sends all three ground-truth fields once, prints label, value and explanation per evaluator, and writes `evaluations.json` beside the trace. Because it scores a saved trace, evaluators can be swapped and re-scored without re-running the agent or paying for the pipeline again.

## Next

Stage 3: the STP plus 2,000-rule code-based evaluator, tested locally against the saved spans through `handler.unwrapped`; the four-receipt golden dataset, which is what finally tests a control breach rather than a control that was never engaged; and the dataset runner.
