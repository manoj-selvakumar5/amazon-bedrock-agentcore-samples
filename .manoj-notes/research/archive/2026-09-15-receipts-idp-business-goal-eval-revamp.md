# Receipts IDP on AgentCore: Business-Goal-Oriented Evaluation Revamp

**Date:** 2026-09-15
**Context:** Research
**Subject:** `02-use-cases/02-workflow-automation-agents/receipts-intelligent-document-processing-agent`

## Summary

The sample declares AgentCore Evaluations but measures none of the business outcomes an
expense-automation owner actually cares about. Its evaluator set was inherited verbatim from the
sibling `event-driven-claims-agent` sample, and one of its three online metrics is scored against a
workload that has no user in it. This note captures the translation from business outcomes to
evaluators, the full AgentCore Evaluations feature surface (verified against the CLI, the SDK, the
boto3 service models, and the developer guide), and a concrete revamp.

---

## 1. The anti-pattern this sample illustrates

The common failure in agent evaluation is starting from the metric catalogue and picking the
names that sound right, rather than starting from what success means for the agent. The result
runs, produces numbers, and yields close to zero actionable insight.

Evidence that this is what happened here:

- `agentcore.json` online eval config selects `Builtin.Helpfulness`, `Builtin.Correctness`,
  `Builtin.ToolSelectionAccuracy`. The sibling claims sample selects the identical three, with the
  identical 1 to 5 rating scale and near-identical label wording. The set was copied, not chosen.
- The extraction pipeline has no conversation. Its front door is an S3 event: EventBridge fires the
  trigger Lambda, which invokes the Runtime with `{s3_uri, user_id}`. There is no user turn.
  `Builtin.Helpfulness` is scoring a machine-to-machine payload against an absent user.
- The custom judge `ReceiptsExtractionQualityEvaluator` blends five unrelated criteria (extraction
  accuracy, reconciliation, category plausibility, routing, confidence honesty) into one 1 to 5
  Likert. A run that extracts perfectly but routes wrongly and a run that routes correctly off a
  garbled total both land on "3 - Average".
- Nothing consumes the scores. No threshold, no alarm, no CI gate, no script reads them.

A nuance worth preserving rather than flattening: the same Runtime **also** serves a genuine
conversational path (`_answer_query` in `main.py`, reached through `chat.py` and `ask.py`), where a
real user asks about their own spend. `Builtin.Helpfulness` is reasonable **there**. The precise
failure is not "wrong metric" but "nobody asked which workload this metric is for". One un-scoped
config is applied across two workloads with nothing in common.

## 2. What the sample has today

| Item | Where | Note |
|---|---|---|
| `ReceiptsExtractionQualityEvaluator` | `agentcore/agentcore.json` | SESSION LLM judge, 1 to 5 numerical, five blended criteria |
| `ReceiptsEvaluation` online config | `agentcore/agentcore.json` | `Builtin.Helpfulness`, `Builtin.Correctness`, `Builtin.ToolSelectionAccuracy`, sampling 100 |
| Golden dataset | none | one unlabelled fixture PNG |
| Offline or batch harness | none | |
| Regression gate | none | strongest pipeline assertion is `assert expense.get("merchant")` |
| Threshold, alarm, or CI consumption | none | |

Substrate that already exists but is unused for evaluation:

- `ProcessingRuns` DynamoDB table holds per-receipt `status`, `needsReview`, `cedarBlocked`,
  `extractorConfidence`, `parseRate`, `validatorRouting`, `validatorConcerns`, `rung`, `model`,
  `total`, with a `status-index` GSI. A labelled outcome table that nothing aggregates.
- `_reconciles()` in `tools/structured_output.py` and `parse_success_rate()` in
  `tools/table_parser.py` are computed every run and never thresholded.
- `tests/fixtures/sample-receipt.png` is fully determined ground truth
  (Blue Bottle Coffee, 2026-06-23, 12.75 + 1.15 + 2.00 = 15.90) with no label file beside it.

## 3. The translation exercise

Three steps, applied in order, before any metric name is considered.

1. Define what a successful interaction looks like from a business perspective.
2. Decompose that outcome into observable agent behaviours that proxy for it.
3. Map each behaviour to an evaluator at the right level. TRACE and TOOL_CALL cover per-turn and
   per-tool-call behaviour; SESSION covers outcomes that only exist across the whole interaction.

For this sample, step one produces two definitions, because the Runtime serves two workloads:

- **Extraction.** The employee is reimbursed the right amount, in the right period, against the
  right cost centre, with no human touching it, and the company does not pay twice or pay
  something it should not.
- **Query.** The employee gets a true answer about their own spend, and only their own.

## 4. The business outcomes

| ID | Outcome | What it means and why finance cares | Measurement |
|---|---|---|---|
| B1 | Straight-through processing rate | The whole business case is replacing manual expense coding. At 40 percent STP the agent costs more than it saves once reviewer time is counted. At 85 percent it pays for itself. | `processed / all receipts` |
| B2 | Dollar-weighted extraction error | Finance asks how many dollars posted wrong, not how many fields. 99 percent field accuracy that misses the total on the one 8,000 dollar receipt is a failure. | `sum(abs(posted - true)) / sum(true)`, plus a count over a materiality threshold |
| B3 | Control effectiveness | The controls an auditor tests: nothing at or above the 2,000 Cedar threshold auto-posted, no duplicate created, no non-reconciling receipt auto-posted. One breach is a finding. | binary per receipt, breach count |
| B4 | Review queue precision | Of receipts sent to a human, what share actually needed it. Low precision means paying analysts to rubber-stamp correct work. This is what stops "route everything to review" from scoring as success. | `true positives / all routed to review` |
| B5 | Confidence calibration | The HITL routing policy rests entirely on `confidence`. If confidence does not predict correctness, the routing threshold is arbitrary and B1 and B4 are both unmanageable. | Brier score, or accuracy per confidence bucket |
| B6 | Completion guarantee | Every receipt reaches a terminal auditable state. A lost receipt is an unreimbursed employee and an SLA breach, and it is invisible to every accuracy metric because there is no output to score. | `terminal states / receipts received` |
| B7 | Unit economics | Cost per receipt including model tokens, judge tokens, Textract, and reviewer minutes. Above the manual cost the agent is net negative regardless of accuracy. | dollars per receipt, split automated versus escalated |
| B8 | Query trust | The answer comes from the user's real data and only their own. Two failure modes: fabricated numbers, and cross-user leakage. | groundedness rate, leak count |

### The asymmetry a single score cannot express

A false clear on an 8,000 dollar duplicate and a false alarm on a 12 dollar coffee are not two
points apart on one axis. False-negative cost scales with the amount; false-positive cost is a
roughly fixed number of analyst minutes. This is why routing belongs in a **categorical** rating
scale with named business failures, not a 1 to 5 Likert.

| Label | Definition | Cost shape |
|---|---|---|
| `AutoPersistCorrect` | auto-posted and matched truth | the goal |
| `FalseClear` | auto-posted but wrong | scales with the dollar amount |
| `FalseAlarm` | sent to review but was correct | fixed reviewer cost |
| `ReviewCorrect` | sent to review and was wrong | working as designed |

## 5. Outcomes mapped onto AgentCore Evaluations features

**Status** is relative to what `agentcore/agentcore.json` declares today, not to the service.

| Outcome | Workload | Eval feature | Status | How the feature produces the outcome | Cost |
|---|---|---|---|---|---|
| B3 | Extraction | `Builtin.TrajectoryExactOrderMatch` | New | `expectedTrajectory = [submit_expense, submit_validation, save_expense]`. Any deviation means a process step was skipped. | zero, programmatic |
| B3 | Extraction | `Builtin.TrajectoryInOrderMatch` | New | Same check, tolerant of the Cedar-denial fallback inserting `human_review`. | zero, programmatic |
| B3 | Extraction | `Builtin.GoalSuccessRate` with `assertions` | New | The control owner writes the rule in English ("must not auto-persist a total at or above 2000") and the judge checks it every session. | one judge call per session |
| B3 | Extraction | `Builtin.ToolParameterAccuracy` | New | Checks the arguments handed to `save_expense`, not merely that the right tool was chosen. | one judge call per tool call |
| B3 | Extraction | `CustomCode` Lambda | New | Recomputes the `expenseId` content hash across sessions to catch a duplicate the in-Lambda hash let through. | Lambda only |
| B1 | Extraction | `CustomCode` Lambda | New | Counts the terminal outcome per session, returns STP as `value` and the outcome as `label`. | Lambda only |
| B2 | Extraction | `CustomCode` Lambda plus golden dataset | New | Reads `submit_expense` arguments from `gen_ai.tool.call.arguments`, diffs against the labelled total, weights by amount. | Lambda only |
| B4 | Extraction | `CustomCode` Lambda, categorical `label` | New | Emits the four routing labels above; precision is a ratio over them. | Lambda only |
| B5 | Extraction | `CustomCode` Lambda | New | Pairs the stated `confidence` against the B2 correctness verdict and returns a Brier score. | Lambda only |
| B6 | Extraction | `CustomCode` Lambda | New | The ledger data already exists in `ProcessingRuns`; the evaluator turns it into a rate. | Lambda only |
| B7 | Both | `CustomCode` Lambda | New | Sums `gen_ai.usage.input_tokens` and `output_tokens` across session spans and applies unit prices. | Lambda only |
| B4 | Extraction | `CustomDerived` from `ThirdParty.DeepEval.ToolUse` | New | Second opinion on the routing call, pinned to `temperature: 0.0` so scores are reproducible across runs. | your own Bedrock spend |
| B4 | Extraction | `Builtin.ToolSelectionAccuracy` | **Existing** | `save_expense` versus `human_review` is a tool-selection decision. This is the one existing choice that maps cleanly. Keep it. | already running |
| B8 | Query | `Builtin.Faithfulness` | New | Flags an answer that contradicts what the Gateway read tools actually returned. | one judge call per turn |
| B8 | Query | `ThirdParty.DeepEval.PIILeakage` | New | Receipts carry names, addresses, and card last-4. Catches them surfacing in a reply. | AWS-side |
| B8 | Query | `ThirdParty.DeepEval.KnowledgeRetention`, `TurnRelevancy` | New | `chat.py` is a multi-turn REPL. Both metrics only make sense on this path. | AWS-side |
| B8 | Query | `ThirdParty.DeepEval.TaskCompletion` | New | The query path has a real stated user goal. The extraction path does not. | AWS-side |
| B8 | Query | `Builtin.Correctness` with `expectedResponse` | **Existing, no ground truth** | Already running, but without `expectedResponse` it silently falls back to context-only mode. Supplying ground truth makes it measure something. | already running |
| B8 | Query | `Builtin.Helpfulness` | **Existing, misapplied** | Meaningful on the query path, meaningless on the S3-triggered path. Today it runs on both. Scope it. | already running |
| all | Both | `Builtin.Insight.FailureAnalysis`, weekly | New | Clusters real failures into categories and root causes, so the taxonomy comes from production rather than from guesses. | batch |
| all | Both | Dataset evaluation (preview) | New | Runs the golden set on every change. This is the regression gate the sample has nothing resembling. | per run |
| B1, B2 | Extraction | A/B test, L0 versus L2 variants | New | Answers whether the degradation ladder actually costs quality, which the sample asserts but never measures. | per run |
| mixed | Extraction | `ReceiptsExtractionQualityEvaluator` | **Existing, replace** | Blends five criteria into one score, so it maps to no single outcome and cannot be acted on. Decompose into the rows above. | already running |

**Reading of the table.** Four evaluators exist today. One maps cleanly, two map only after being
scoped or given ground truth, and one should be decomposed. Of eight business outcomes, today's
stack measures none end to end.

---

## 6. AgentCore Evaluations feature reference

Verified against AgentCore CLI v0.28.1, the `bedrock-agentcore` Python SDK, the boto3 service
models for `bedrock-agentcore` and `bedrock-agentcore-control`, and the AgentCore developer guide.

### 6.1 Provenance (`evaluatorType` / `provider`)

| Kind | `evaluatorType` | `provider` | Who runs the model | What you configure |
|---|---|---|---|---|
| Managed built-in | `Builtin` | `AWS` | AWS | nothing, immutable |
| Managed third-party | `ThirdParty` | `DeepEval` or `AutoEval` | AWS | nothing |
| Derived from a base | `CustomDerived` | inherited from base | **you** | model and inference params only |
| Custom LLM judge | `Custom` | `Custom` | you | instructions and ratingScale |
| Custom code-based | `CustomCode` | `Custom` | not applicable | arbitrary Lambda |

Managed third-party IDs follow `ThirdParty.<Provider>.<Metric>`, for example
`ThirdParty.DeepEval.TaskCompletion`. Built-in ARNs are
`arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness`; custom evaluators are
`arn:aws:bedrock-agentcore:<region>:<account>:evaluator/<id>`.

### 6.2 Levels and prompt placeholders

| Level | Required placeholders (at least one) | Ground-truth placeholders |
|---|---|---|
| SESSION | `context`, `available_tools` | `assertions`, `expected_tool_trajectory`, `actual_tool_trajectory` |
| TRACE | `context`, `assistant_turn` | `expected_response` |
| TOOL_CALL | `available_tools`, `context`, `tool_turn`, `available_skills`, `invoked_skill`, `skill_content`, `user_message` | none |

Validation requires at least one of the level's placeholders, not all of them. The sample's judge
uses `{context}` and `{actual_tool_trajectory}` and is therefore valid, but it never supplies
`{available_tools}`, so the judge cannot reason about what the agent could have called.

### 6.3 Built-in evaluator catalogue

| Evaluator | Level | Scoring |
|---|---|---|
| `Builtin.GoalSuccessRate` | SESSION | LLM judge, binary Yes/No; separate prompt when `assertions` supplied |
| `Builtin.TrajectoryExactOrderMatch` | SESSION | **programmatic**, no LLM |
| `Builtin.TrajectoryInOrderMatch` | SESSION | **programmatic**, no LLM |
| `Builtin.TrajectoryAnyOrderMatch` | SESSION | **programmatic**, no LLM |
| `Builtin.Correctness` | TRACE | LLM judge; separate binary prompt when `expectedResponse` supplied |
| `Builtin.Faithfulness` | TRACE | LLM judge, 5-point ordinal |
| `Builtin.Helpfulness` | TRACE | LLM judge |
| `Builtin.ResponseRelevance` | TRACE | LLM judge |
| `Builtin.Coherence` | TRACE | LLM judge, 5-point ordinal |
| `Builtin.Conciseness` | TRACE | LLM judge, 3-point |
| `Builtin.InstructionFollowing` | TRACE | LLM judge |
| `Builtin.Refusal` | TRACE | LLM judge |
| `Builtin.Harmfulness` | TRACE | LLM judge |
| `Builtin.Stereotyping` | TRACE | LLM judge |
| `Builtin.ToolSelectionAccuracy` | TOOL_CALL | LLM judge |
| `Builtin.ToolParameterAccuracy` | TOOL_CALL | LLM judge |
| `Builtin.SkillSelectionAccuracy` | TOOL_CALL | LLM judge |
| `Builtin.SkillInstructionFollowing` | TOOL_CALL | LLM judge |

Note: CLI v0.28.1 lists only 12 of these. The three trajectory evaluators, `Harmfulness`,
`Stereotyping`, and `ToolParameterAccuracy` appear in the developer guide but not in the CLI's
internal table. Confirm availability with `ListEvaluators` before designing around them.

### 6.4 Ground truth

| Evaluator | Level | Field | Scoring |
|---|---|---|---|
| `Builtin.Correctness` | TRACE | `expectedResponse` | LLM judge, CORRECT / INCORRECT |
| `Builtin.GoalSuccessRate` | SESSION | `assertions` | LLM judge, SUCCESS / FAILURE |
| `Builtin.TrajectoryExactOrderMatch` | SESSION | `expectedTrajectory` | programmatic |
| `Builtin.TrajectoryInOrderMatch` | SESSION | `expectedTrajectory` | programmatic |
| `Builtin.TrajectoryAnyOrderMatch` | SESSION | `expectedTrajectory` | programmatic |

Ground-truth fields are optional and evaluators fall back to their ground-truth-free prompt when
omitted. You may pass all fields in one request; unused ones come back in
`ignoredReferenceInputFields`.

Wire format on the `Evaluate` API:

```json
{
  "context": { "spanContext": { "sessionId": "...", "traceId": "..." } },
  "expectedResponse": { "text": "..." },
  "assertions": [ { "text": "..." } ],
  "expectedTrajectory": { "toolNames": ["submit_expense", "submit_validation", "save_expense"] }
}
```

### 6.5 Third-party evaluators

Three distinct integration modes, not one.

| Mode | When it earns its place |
|---|---|
| Managed (`ThirdParty.*` ID) | Zero infrastructure, zero config. AWS picks the model and manages the library version. |
| Derived (`CustomDerived`) | You need a pinned judge model or `temperature: 0.0` for reproducible scores. The base owns the prompt and the scoring. |
| Self-hosted Lambda (`CustomCode`) | You need a metric outside the launch set, or you need to pass constructor `params`. This is the CLI `--3p-template-json` route. |

Launch metric set:

- **DeepEval**: Bias, Toxicity, PIILeakage, Summarization, TaskCompletion, ConversationCompleteness,
  KnowledgeRetention, TurnRelevancy, GoalAccuracy, ToolUse
- **AutoEval**: Security, Humor, Possible

Derived evaluator config:

```json
{
  "derived": {
    "baseEvaluatorId": "ThirdParty.DeepEval.ToolUse",
    "modelConfig": {
      "bedrockEvaluatorModelConfig": {
        "modelId": "global.anthropic.claude-sonnet-4-6",
        "inferenceConfig": { "temperature": 0.0, "topP": 1.0, "maxTokens": 2048 }
      }
    }
  }
}
```

You do not set `level`, `instructions`, or `ratingScale`. The base owns all three and `level` is
read-only on `GetEvaluator`. Inference runs on **your** account and credentials, which is the key
difference from the managed mode.

AWS states explicitly that built-in evaluators are tested and benchmarked, and that it makes no
quality claims about DeepEval and AutoEval.

The CLI's self-hosted route supports exactly two libraries (`deepeval`, `autoevals`) and two model
providers (`bedrock`, `openai`), and generates a Lambda wrapping the SDK adapter in
`bedrock_agentcore.evaluation.custom_code_based_evaluators.third_party`.

### 6.6 Custom code-based evaluator contract

```python
from bedrock_agentcore.evaluation.custom_code_based_evaluators import (
    custom_code_based_evaluator, EvaluatorInput, EvaluatorOutput,
)

@custom_code_based_evaluator()
def handler(input: EvaluatorInput, context) -> EvaluatorOutput:
    # input.evaluation_level      "SESSION" | "TRACE" | "TOOL_CALL"
    # input.session_spans         raw ADOT span dicts
    # input.target_trace_id       set for TRACE
    # input.target_span_id        set for TOOL_CALL
    # input.reference_inputs      list[ReferenceInput], filtered by level
    return EvaluatorOutput(value=1.0, label="Pass", explanation="...")
```

`EvaluatorOutput` fields: `value` (optional float), `label` (**required** unless `errorCode` is
set), `explanation`, `errorCode`, `errorMessage`.

Registration:

```json
{ "codeBased": { "lambdaConfig": { "lambdaArn": "...", "lambdaTimeoutInSeconds": 60 } } }
```

Reference-input filtering by level: SESSION receives all; TRACE receives session-level plus those
matching the target `traceId`; TOOL_CALL receives session-level plus those matching the target
`spanId`.

### 6.7 Span substrate available to a code-based evaluator

Emitted by the Strands SDK and captured because the sample sets
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`:

```
gen_ai.agent.name          gen_ai.agent.tools          gen_ai.request.model
gen_ai.tool.name           gen_ai.tool.call.arguments  gen_ai.tool.call.result
gen_ai.tool.status         gen_ai.tool.definitions
gen_ai.usage.input_tokens  gen_ai.usage.output_tokens  gen_ai.usage.total_tokens
gen_ai.usage.cache_read_input_tokens
gen_ai.input.messages      gen_ai.output.messages
events: gen_ai.user.message, gen_ai.choice, gen_ai.system.message, gen_ai.tool.message
```

Every field submitted through `submit_expense` and `submit_validation` is recoverable from
`gen_ai.tool.call.arguments`. Cost per receipt is recoverable from the usage attributes. Most of the
proposed evaluators therefore need **no change to the agent**.

### 6.8 Execution modes

| Mode | API or entry point | Use |
|---|---|---|
| On-demand | `Evaluate`, synchronous, you supply spans | dev loop, unit-testing an evaluator against recorded spans |
| Online | `CreateOnlineEvaluationConfig` | continuous over live traffic |
| Batch | `StartBatchEvaluation` | many sessions, aggregate output, optional `metricsNamespace` |
| Dataset (**preview**) | `OnDemandEvaluationDatasetRunner`, `BatchEvaluationRunner` | runner invokes the agent, waits for ingestion, evaluates. First for CI, second for baselines |
| Simulation | `pip install 'bedrock-agentcore[simulation]'` | LLM-backed actor with persona and goal drives multi-turn conversations |
| Insights | `Builtin.Insight.*`, one-time or DAILY/WEEKLY/MONTHLY | failure clustering and root cause analysis |
| Recommendations | `agentcore run recommendation` | rewrites system prompts and tool descriptions using eval signal; chains off insights |
| A/B test | `abTests` in `agentcore.json` | C versus T1 variants, per-variant online eval config |

Online eval configuration shape:

```python
rule={
  "samplingConfig": {"samplingPercentage": 100.0},
  "filters": [{"key": "<span attribute>",
               "operator": "Equals",   # or NotEquals, GreaterThan, LessThan,
                                       # GreaterThanOrEqual, LessThanOrEqual,
                                       # Contains, NotContains
               "value": {"stringValue": "..."}}],
  "sessionConfig": {"sessionTimeoutMinutes": 15}
}
```

Up to 5 filters and up to 10 evaluators per configuration. Results land in
`/aws/bedrock-agentcore/evaluations/results/<configId>` unless `outputConfig` redirects them.
`outputConfig.cloudWatchConfig.metricsNamespace` is what turns scores into alarmable CloudWatch
metrics; the CLI does not set it.

### 6.9 Dataset schemas

`AGENTCORE_EVALUATION_PREDEFINED_V1`:

```json
{"scenario_id": "...", "turns": [{"input": "...", "expectedResponse": "..."}],
 "assertions": ["..."], "expected_trajectory": ["tool_a", "tool_b"]}
```

`AGENTCORE_EVALUATION_SIMULATED_V1`:

```json
{"scenario_id": "...", "input": "...",
 "actor_profile": {"traits": {...}, "context": "...", "goal": "..."},
 "max_turns": 10, "assertions": ["..."]}
```

### 6.10 Insights failure taxonomy

Three-level hierarchy: failure categories, subcategories, then root-cause clusters with affected
session counts. Documented categories: execution errors, task instruction issues, incorrect actions,
context handling, hallucinations (including parameter hallucination and fabricated tool outputs),
repetitive behaviour, orchestration errors (goal deviation, premature termination), LLM output
issues, configuration mismatch, coding-specific.

Using this **before** writing a custom taxonomy is the point. Let production say what breaks, then
write evaluators for the clusters that appear.

---

## 7. Implementation sketch

### 7.1 Split the online configuration by workload

Requires stamping a `receipts.workload` attribute on the span in `main.py`, then:

```python
# extraction pipeline
rule={
  "samplingConfig": {"samplingPercentage": 100.0},
  "filters": [{"key": "receipts.workload", "operator": "Equals",
               "value": {"stringValue": "extraction"}}],
}
evaluators=[
  {"evaluatorId": "Builtin.GoalSuccessRate"},
  {"evaluatorId": "Builtin.TrajectoryInOrderMatch"},
  {"evaluatorId": "Builtin.ToolSelectionAccuracy"},
  {"evaluatorId": "Builtin.ToolParameterAccuracy"},
  {"evaluatorId": "<ReceiptsRoutingOutcome ARN>"},
  {"evaluatorId": "<ReceiptsDollarError ARN>"},
  {"evaluatorId": "<ReceiptsCalibration ARN>"},
]
```

```python
# conversational query path
rule={
  "samplingConfig": {"samplingPercentage": 100.0},
  "filters": [{"key": "receipts.workload", "operator": "Equals",
               "value": {"stringValue": "query"}}],
}
evaluators=[
  {"evaluatorId": "Builtin.Faithfulness"},
  {"evaluatorId": "Builtin.Correctness"},
  {"evaluatorId": "Builtin.Helpfulness"},
  {"evaluatorId": "ThirdParty.DeepEval.PIILeakage"},
  {"evaluatorId": "ThirdParty.DeepEval.KnowledgeRetention"},
]
```

### 7.2 Risk-tiered evaluation

Stamp the receipt total on the span, then run the expensive judge only where the money is:

```python
"filters": [{"key": "receipts.total", "operator": "GreaterThanOrEqual",
             "value": {"doubleValue": 500.0}}]
```

Cheap deterministic evaluators run on 100 percent of traffic; the judge runs on the tail that
carries the dollars.

### 7.3 Recommended build order

1. Label the existing fixture and add the adversarial cases the sample cannot currently produce:
   non-reconciling, foreign currency, over the 2,000 threshold, near-duplicate, illegible.
2. The zero-cost tier first: two trajectory evaluators plus `GoalSuccessRate` with assertions.
   No Lambda, no custom code, and it covers B3 entirely, which is the outcome an auditor asks about.
3. One `CustomCode` Lambda carrying B1, B2, B4, B5, B6, B7. None of these are judgeable.
4. One `CustomDerived` from `ThirdParty.DeepEval.ToolUse` with a pinned model and `temperature: 0.0`.
5. Split into two online configs on `receipts.workload`.
6. Weekly `Builtin.Insight.FailureAnalysis`, then revise the taxonomy from what it finds.
7. Dataset evaluation as the CI regression gate.
8. A/B test L0 versus L2 to measure what the degradation ladder actually costs.

---

## 8. Defects in the sample that block this

| # | Defect | Effect |
|---|---|---|
| 1 | All three `Agent(...)` constructions omit `name=`. Strands defaults to `_DEFAULT_AGENT_NAME = "Strands Agents"`. | Extractor, validator, and query agent emit identical `gen_ai.agent.name`. Per-agent evaluation and validator-independence checks are impossible. One line each to fix. |
| 2 | `_tag_span_rung()` accepts `needs_review` but neither call site passes it. | `receipts.needs_review` is never emitted. The routing decision, which is the business outcome, is absent from the spans the online evaluators score. |
| 3 | `agentcore/cdk/lib/` was never committed. `bin/cdk.ts` imports `../lib/cdk-stack`; `docs/CONFIGURATION.md` points at `infra-construct.ts`. | `make synth` and `deploy.sh` cannot run as shipped, so none of this can be verified against a live stack. |
| 4 | `EXTRACTOR_PROMPT` claims it is given "the user's expense profile" and instructs category inference from "the user's default category and history", but the built prompt passes only `user_id`, OCR text, and parsed items. `get_user_profile`, `get_recent_expenses`, and `lookup_merchant` are never called in the extraction path. | The existing judge's criterion "plausible category for the merchant **and user**" is unanswerable by construction. |
| 5 | `reimbursementPolicy` is seeded in `scripts/seed_dynamodb.py` and read by nothing. | There is no policy-compliance control to evaluate, despite the data suggesting one. |
| 6 | Ladder feature flags `memoryWrite`, `merchantLookup`, `categoryInference`, `dedup` are declared and never consumed. | Any "did rung L1 shed X?" evaluator would pass vacuously. |
| 7 | `.github/workflows/ci.yml` sets `working-directory: sample`, which does not exist at this path. | CI cannot run. |
| 8 | `tests/conftest.py` claims moto mocks DynamoDB; moto is neither a dependency nor imported. | Stale docstring. |

## 9. Limits, drift, and unverified items

- Code-based evaluator Lambda: 300 second maximum, **6 MB maximum input payload**, and
  `sessionSpans` is truncated when the session exceeds it. A long ladder-retry session could lose
  spans. Write defensively and return `errorCode` rather than a wrong score.
- Enabling an online configuration **locks** every custom evaluator it references. No edits, no
  deletes, until the configuration is disabled or deleted. Clone to change.
- Quotas: 1,000 evaluation configurations per Region per account; 1 million input plus output tokens
  per minute per account in large Regions.
- Online evaluation over per-agent log groups needs `UNIFIED_TRACES_DESTINATION_ENABLED=true` on the
  Runtime. The sample sets neither this nor a dedicated log group.
- CLI v0.28.1 is behind the API. Its `agentcore.json` schema exposes neither `derived` nor
  `rule.filters`, and its evaluator table omits six built-ins. Both need the raw API or a CDK
  escape hatch until the CLI catches up.
- SDK naming drift: the developer guide shows `bedrock_agentcore.evaluation.code_based_evaluators`
  with `@code_based_evaluator()` taking one argument. The installed package exposes
  `custom_code_based_evaluators` with `@custom_code_based_evaluator()` taking `(input, context)`.
  Write against the installed package and verify.
- The CLI's self-hosted DeepEval template pins `deepeval>=2.0.0,<3.0.0` while PyPI is on 4.2.3.
- Dataset evaluation is explicitly public preview.
- **Not verified:** the `level` of most `ThirdParty.*` metrics (only `TaskCompletion` and `Security`
  are documented as TRACE). Call `ListEvaluators` before designing around them.
- **Not researched:** the partner and vendor observability ecosystem (Langfuse, Arize, Braintrust,
  Datadog and similar) hooking into AgentCore over OTLP, and published IDP benchmark definitions
  (STP rate, CER/WER, ANLS). This note covers the first-party surface only.

## 10. Action items

- [ ] Label `tests/fixtures/sample-receipt.png` and build the adversarial fixture set
- [ ] Add `name=` to the three `Agent(...)` constructions
- [ ] Pass `needs_review` at both `_tag_span_rung()` call sites; add `receipts.workload` and `receipts.total`
- [ ] Add the two trajectory evaluators and `GoalSuccessRate` with assertions to `agentcore.json`
- [ ] Write the `ReceiptsBusinessOutcome` code-based evaluator Lambda
- [ ] Split `ReceiptsEvaluation` into extraction and query configurations with filters
- [ ] Decide whether to restore or reconstruct `agentcore/cdk/lib/` before any live verification
- [ ] Confirm `ThirdParty.*` levels with `ListEvaluators`
- [ ] Check whether a newer AgentCore CLI expresses `derived` and `rule.filters` in `agentcore.json`

## References

- Evaluations overview: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html
- Third-party evaluators: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/third-party-evaluators.html
- Built-in prompt templates: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/prompt-templates-builtin.html
- Ground truth evaluations: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ground-truth-evaluations.html
- Code-based evaluators: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-based-evaluators.html
- Dataset evaluation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/dataset-evaluations.html
- Simulation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/simulation.html
- Insights, how it works: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/insights-how-it-works.html
- Create online evaluation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/create-online-evaluations.html
- Evaluations tutorials in this repo: `01-features/06-observe-evaluate-optimize-your-agent/02-evaluate`
