# Stage 1: Outcome Telemetry in the Receipts Agent, and the Stage 2 Plan

**Date:** 2026-09-17

Stage 0 is done and Stage 1 is now done and verified locally. This note records why Stage 1 touched the agent rather than the harness, exactly what changed, what the verified trace looks like, and what Stage 2 does next.

## Why this change was needed

Stage 0 proved the pipeline runs and that its trace is incomplete in one specific way: **the action the business cares about is invisible.**

The extractor and validator are Strands agents, and their tools are registered on the agent, so Strands traces them automatically:

```text
execute_tool submit_expense
execute_tool submit_validation
```

The final `save_expense` / `human_review` call is not an agent tool call. It is an orchestrator MCP call made by `_process()` after both agents finish, so nothing traced it. Stage 0's trace ended with the validator's opinion and never showed the action taken.

That matters because the Stage 2 evaluators read the trace and nothing else:

- `Builtin.TrajectoryInOrderMatch` expects `save_expense` in the trajectory. Without the span, a correct run looks like a skipped step.
- `ThirdParty.DeepEval.ToolUse` judges the action taken. Without the span, it can only see the validator's routing argument, not what actually happened.
- `Builtin.GoalSuccessRate` would have to infer the outcome. With `receipts.status` on the span it can read it.

`writes.json` proved the save happened, but the evaluation service never receives `writes.json`. It receives `adot.json`. So the fix has to be in the trace.

## Why the agent, not the harness

The harness could have faked these spans. I put them in `main.py` instead, because the two problems are different:

| Instrumentation | Reason it exists | Needed when deployed? |
|---|---|---|
| Synthetic `receipts.invocation` span, `session.id` stamping, in-memory exporter | Local run has no AgentCore Runtime | No. Runtime injects `session.id` and exports via ADOT |
| `execute_tool save_expense` / `human_review` spans, outcome attributes | The call is orchestrator code, outside the Strands agent loop | **Yes** |

The first group is a local substitute for Runtime. The second is a genuine gap in the application's own telemetry, and it exists whether the code runs locally or deployed. If the spans lived only in the harness, Stage 2 would prove the evaluator wiring but not that deployed traces contain the same trajectory — which is the thing the blog needs to claim.

`save_expense` could instead have been registered as a Strands agent tool, which would make Strands trace it for free. I did not do that: it would hand the persistence decision to the model, and the whole design point is that the independent validator plus deterministic Cedar policy own that decision, not the LLM.

## What changed

One file: `app/receiptsagent/main.py`. No prompts, no routing rules, no tools, no models, no dependencies, no deploy config.

**1. Both write calls now go through one helper.** `gateway.call_tool_sync(...)` for save and review is replaced by `_call_gateway_tool(...)`, which emits the span Strands would have emitted if this were an agent tool:

```text
name                     execute_tool save_expense
gen_ai.operation.name    execute_tool
gen_ai.system            strands-agents
gen_ai.tool.name         save_expense        (stable, not the resolved Gateway target name)
gen_ai.tool.call.id      <same id passed to the Gateway>
gen_ai.tool.status       success | error
events                   gen_ai.tool.message (arguments), gen_ai.choice (result)
```

The stable `semantic_name` is deliberate: `_tool_name()` may resolve to a namespaced target name in a deployed Gateway, and the evaluators match on `save_expense` / `human_review`.

**2. A returned Cedar denial is marked as an error span.** A policy denial is not an exception — it comes back as an error-status `ToolResult`, which `_is_denied()` already recognises. So the helper marks that span `error` explicitly. Otherwise a blocked save would appear successful in the trace and the trajectory would read as a clean auto-persist.

**3. The invocation span carries the final outcome:**

```text
receipts.status               processed | needs_review | error
receipts.needs_review
receipts.cedar_blocked
receipts.validator.routing
receipts.total
receipts.extractor.confidence
receipts.validator.confidence
```

The root span status is also set (previously `UNSET`).

### The constraint that shaped the implementation

Telemetry must never change what happens to a receipt. First draft wrapped the Gateway call in `start_as_current_span(...)` as a context manager; semantic review caught that the span is created on `__enter__` and closed on `__exit__`, both outside the best-effort guard — so a tracer failure could block the call, and an exporter failure *after* a successful write could surface as an exception over a save that already happened.

Rewritten to use `start_span()` and end the span manually, so the business call sits outside the telemetry lifecycle entirely. Verified by fault injection: tracer-start failure, span-end failure, and a raised Gateway error each produce exactly one Gateway call, the original result or the identical exception object, and no fallback that wasn't already there.

## Verified result

Real run `local-3dd922dab5e843499d9007830196b654`, same Blue Bottle fixture, 13 spans → 14:

```text
receipts.invocation
├── invoke_agent Strands Agents        extractor
│   ├── chat
│   ├── execute_tool submit_expense
│   └── chat
├── invoke_agent Strands Agents        validator
│   ├── chat
│   ├── execute_tool submit_validation
│   └── chat
└── execute_tool save_expense          ← new
```

Root span, status now `OK`:

```json
{
  "receipts.status": "processed",
  "receipts.needs_review": false,
  "receipts.cedar_blocked": false,
  "receipts.validator.routing": "AUTO_PERSIST",
  "receipts.total": 15.9,
  "receipts.extractor.confidence": 97,
  "receipts.validator.confidence": 97
}
```

The save span is parented to `receipts.invocation`, reports `gen_ai.tool.status: success`, and carries both content events. `result.json` says `processed`, `writes.json` has one `save_expense` at $15.90 — trace, result, and write now agree.

`adot.json`: 25 records (14 spans, 11 correlated logs), one session id, and the save span has its correlated content log. So the span survives `convert_strands_to_adot()`, which is what Stage 2 sends.

**Checks run:** `py_compile`, ruff lint + format, 58 existing unit tests, success/denial span behaviour, telemetry fault injection, ADOT conversion, and a semantic review (approved, no blockers).

**Environment note:** system Python had neither pytest nor ruff, so validation ran from a git-ignored `.venv` in `receipts-idp-evaluation` with pinned `pytest==8.4.2` and `ruff==0.12.12`. No project dependency file changed — `aws-opentelemetry-distro` was already a runtime dependency, so Stage 1 added nothing.

## Gaps closed after review

The review of `f70baf60` raised two items, both now fixed in `9f705dcd`.

**1. Every terminal return is tagged.** Outcome attributes were stamped only on the success path and on an exception during the write phase. The earlier returns produced a trace with `receipts.ladder.*` but no `receipts.status`, so a span-based STP rate would have dropped deferred and failed receipts out of the denominator rather than counting them as non-STP. All five now tag:

| Path | `receipts.status` |
|---|---|
| Missing `s3_uri` | `error` |
| L4 defer | `deferred` |
| OCR failure | `error` |
| Step-down to defer | `deferred` |
| Extractor submitted nothing | `error` |

`_tag_span_outcome` gained defaults for the sparse paths, and `receipts.validator.routing` and `receipts.total` are written only when they have a value, so a deferred receipt does not get a misleading `total: 0`. Span status is `ERROR` for errors and `OK` for a defer, which is not a failure.

**2. `receipts.s3_uri` is stamped.** Distinct from the "missing `s3_uri`" return path above. An evaluator needs the receipt key to tell a real duplicate from two separate purchases that share merchant, date, and amount, and it is the only way to join a trace back to its `ProcessingRuns` row, since `receiptId = hash(s3_uri)`.

Also fixed: the `except Exception: pass` in the span cleanup now logs at debug level. It was clean under the pinned `ruff==0.12.12` but flagged as `S110` by current ruff, which is what CI installs.

## A real bug the verification run exposed

`e3a7fd90`. The first real run failed with `InvalidS3ObjectException` from Textract against a bucket that plainly existed.

`tools/ocr.py` created its client as `boto3.client("textract")` with no region — the only client in the agent that did not pass `region_name=REGION`; KMS, CloudWatch, EventBridge, SQS and AppConfig all do. It therefore used the profile's default region (`us-east-1` here) while the receipt sat in `us-west-2`. Setting `AWS_REGION` does not help, because it does not override a region configured in an AWS profile.

Fixed in `ocr.py` through the config seam, and `capture_trace.py` now also sets `AWS_DEFAULT_REGION` so any unparameterised client follows `--region`. This would affect anyone whose default region differs from where they deployed.

The failed run also served as unplanned proof of the new error tagging on real traffic: `receipts.status=error`, `receipts.s3_uri` present, span status `ERROR`. Exactly the case that previously produced an unlabelled trace.

## Verified again after the fixes

Real run `local-26e754e8b9104a549ec645292b828218`, same fixture, 14 spans, root status `OK`, `execute_tool save_expense` parented to `receipts.invocation` with `gen_ai.tool.status: success` and both content events. Root attributes now include `receipts.s3_uri`, `receipts.validator.routing=AUTO_PERSIST`, `receipts.total=15.9`, and both confidences (97 extractor, 96 validator). `adot.json`: 25 records under one session id.

## Still open

`parse_rate` reports `1.0` while every pre-parsed line item has `unitPrice: null` and `amount: null`. It counts rows, not field completeness. The LLM recovered the prices from the OCR text, so output was fine, but the metric is misleading and should not be used as a deterministic-parse quality signal.

## Stage 2 plan

No agent changes. Reuse the saved trace, don't re-run the agent per attempt.

1. Take `adot.json` from `local-26e754e8b9104a549ec645292b828218`, the post-fix run.
2. Call `Evaluate` with the three planned evaluators:
   - `Builtin.TrajectoryInOrderMatch`, expected trajectory including `save_expense`
   - `Builtin.GoalSuccessRate`, one assertion
   - `ThirdParty.DeepEval.ToolUse`
3. Done when three scores print.

**The question Stage 2 answers:** does the service read a manually emitted span as a tool call? The span now carries the documented identifying attributes (`gen_ai.operation.name`, `gen_ai.tool.name`) and both content events, and it survives ADOT conversion — but that only proves the payload is well-formed, not that the service accepts it. If it doesn't, the plan still holds and code-based evaluators carry more of the load.

Worth confirming in the same run: the payload lands as **one session** (25 records, one `session.id`), the custom `receipts.invocation` root is accepted alongside the Strands spans, and the correlated log records are read rather than ignored.

Then Stage 3: the STP + 2,000-rule code-based evaluator tested against the saved spans via `handler.unwrapped`, the four-receipt golden dataset, and the dataset runner. The failure-path tagging that blocked this is now done, so the dataset's failure cases will come back labelled.
