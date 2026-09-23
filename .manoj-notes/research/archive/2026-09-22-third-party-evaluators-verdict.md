# Third-Party Evaluators: None Fit Today

**Date:** 2026-09-22

Every managed third-party evaluator was checked against the two rules: judge a model decision against a known answer or a clear reference, and one question per evaluator. The sources were `ListEvaluators` in us-west-2 (13 `ThirdParty.*`: 10 DeepEval, 3 AutoEval), the AWS third-party evaluator docs, and the upstream DeepEval and autoevals definitions.

**The deciding fact:** the managed third-party evaluators take no ground truth, no parameters and no task override. They judge the spans with no reference at all. Every decision here that has a reference is already owned by a built-in or a code-based evaluator.

| Evaluator | Level | Verdict | Reason |
|---|---|---|---|
| DeepEval.Bias | TRACE | No fit | Scores opinions in the output; the note, validator and chat state facts |
| DeepEval.Toxicity | TRACE | No fit | Same method; nothing here can produce toxic output, so it would be a tripwire |
| DeepEval.PIILeakage | TRACE | Failed | Scored in the wrong direction (09-18 verdict note); no notion of a legitimate recipient |
| DeepEval.Summarization | TRACE | No fit | Rejected on the note; on chat it would duplicate Faithfulness |
| DeepEval.TaskCompletion | TRACE | No fit | Infers the task itself, with no reference; one pipeline trace holds three models' tasks; on chat it duplicates Correctness, less well |
| DeepEval.ConversationCompleteness | SESSION | No fit today | Chat is one question per session |
| DeepEval.KnowledgeRetention | SESSION | No fit today | Scores 1.0 by default on single-turn sessions |
| DeepEval.TurnRelevancy | SESSION | No fit | With one turn it is only "on topic", which Correctness covers |
| DeepEval.GoalAccuracy | SESSION | No fit today | Multi-turn metric; the same job as ConversationCompleteness |
| DeepEval.ToolUse | SESSION | Failed | Scored a correct run 0.25, assuming a user who asked for something |
| AutoEval.Security | TRACE | Failed | "Is this string malicious?"; called every normal note malicious |
| AutoEval.Humor | TRACE | No fit | No decision about humour |
| AutoEval.Possible | TRACE | No fit (closest) | Could read chat declining a write, but no write tools exist, and a false "deleted" claim is caught by Correctness and Faithfulness |

The whole-session trap from the ToolParameterAccuracy test would also hit any TRACE judge pointed at the pipeline, because the extractor, validator and note writer share one trace.

## Only if multi-turn chat is built for its own reasons

Not to give these metrics a job. The 09-17 chat note argues for multi-turn chat on business grounds (C1). If it is built:
- **GoalAccuracy or ConversationCompleteness, one of them, not both.** A diagnostic under Correctness, with scripted session goals as the reference.
- **KnowledgeRetention.** Only meaningful if users volunteer facts in earlier turns.

This confirms the 09-18 conclusion: no third-party metric owns a business outcome in this sample.
