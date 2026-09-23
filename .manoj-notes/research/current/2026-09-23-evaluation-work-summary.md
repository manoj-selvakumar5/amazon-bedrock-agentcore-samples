# Evaluating the Receipts IDP Agent: What Was Built, How, and How It Was Tested

**Date:** 2026-09-23
**Branch:** `receipts-idp-eval-revamp`

This note stands on its own. It explains the system under evaluation, the conceptual approach, what was implemented, every kind of test run, and the results, including what did not work.

**Where it lives now.** Everything is packaged as one standalone sample, `02-use-cases/02-workflow-automation-agents/receipts-idp-agent-with-evals/`: the agent, the evaluators and the evaluation harness. It is deployed to us-west-2 and left running. It is meant to replace `receipts-intelligent-document-processing-agent` in the pull request. The older folders stay on the branch until then.

---

## 1. The system being evaluated

The subject is the **receipts intelligent document processing sample** (`02-use-cases/02-workflow-automation-agents/receipts-intelligent-document-processing-agent`). It runs on Amazon Bedrock AgentCore and has two workloads.

**The receipt pipeline.** A receipt image lands in S3 and is processed with no user involved:

1. **OCR.** Amazon Textract `AnalyzeExpense` reads the image. The code passes the models only the fields Textract recognises (vendor, date, totals and so on) plus line items. Other printed text is dropped.
2. **Extractor.** A model reads the OCR output and calls its one tool, `submit_expense`, with merchant, date, currency, subtotal, tax, tip, total, category and a self-reported confidence.
3. **Validator.** A second, independent model sees the OCR and the extraction, decides, and acts on its decision by calling exactly one of two tools, each with a confidence and its reasoning:
   - `approve_expense` calls `save_expense` through the Gateway
   - `send_to_review` calls `human_review`, which writes the expense with status `needs_review` so a person can look at it
4. **Orchestrator code** sets the limits. The tools are pinned to the extractor's expense, so the validator cannot change what is saved. Only one decision is acted on. No decision, a shed validator, or a rung that forces review all mean review. (Until 2026-09-23 the validator only reported a verdict through `submit_validation`, and code made the calls; see 3.7.)
5. **A Cedar policy at the Gateway** denies any `save_expense` with a total of $2,000 or more, whatever the models decided. A denied save falls back to review.
6. **Reviewer note.** When a receipt is held, a third model writes a 2-3 sentence note for the human reviewer.

All three models run inside one session, and one trace, per receipt.

**The chat assistant.** An employee asks questions about their own expenses. The assistant uses three read-only tools (profile, recent expenses, merchant lookup). The user id comes from a signed identity token and is fixed in the tool wrappers, so the model cannot request another user's data.

**The starting point.** The sample shipped with one LLM judge that blended five qualities into a single 1-to-5 score, and an online configuration running `Helpfulness`, `Correctness` and `ToolSelectionAccuracy`. Those three were copied from a sibling sample. `Helpfulness` was scoring a pipeline that has no user. There was no labelled data, no regression gate, and no threshold on any score.

**The goal.** Use this sample as the worked example for a blog on choosing AgentCore evaluators, with running code behind every claim.

---

## 2. The conceptual approach

### 2.1 Two frameworks

**Framework 1 works backwards from the business.** Why does this agent exist, and what would you measure no matter how it is built? The test is to **state the metric without naming the agent, its model or its tools.** Imagine a person typing receipts in by hand: does the number still exist? The metrics that survive form the **scoreboard**.

| Metric | Meaning |
|---|---|
| B1 Straight-through rate | Share of receipts saved with no person involved |
| B2 Dollar-weighted extraction error | Money recorded wrong, not fields recorded wrong |
| B3 Control breaches | Times a rule an auditor would test was broken; target zero |
| B4 Review-queue precision | Share of escalations a person actually needed to see |
| C1 Self-service resolution | Chat questions answered without a person being pulled in |
| C2 Answer accuracy | Chat answers that are right |

**Framework 2 works forwards from the architecture.** Which failures does *this* design make likely? For example:
- an extractor inventing values OCR did not provide
- a validator making the right call for the wrong reason
- a chat assistant forgetting earlier turns

Evaluators aimed at these are **diagnostics**: they explain why a scoreboard number moved.

**How the two combine:** each scoreboard metric gets a diagnostic beneath it that can explain a movement in it. As built:
- B2 extraction error has the invented-values check under it.
- B4 review precision has the right-reason check under it.
- C1 resolution has the knowledge-retention check under it.

### 2.2 Rules for a legitimate evaluator

These were settled during the work, and every evaluator was held to them:

1. **It judges a decision a model makes, against a right answer or a clear reference.** The reference can be labels, or the model's own input. An evaluator that only re-checks a rule the code already enforces passes by construction and says nothing about the agent.
   - **The one exception**, labelled as such: a *control monitor* that watches whether a deterministic control still holds in production.
2. **One question, one evaluator.** No two evaluators doing the same job in different ways.
3. **Every judge passes a contrast test before it is trusted.** Build pairs of cases that differ in one thing, and require the verdict to flip on that thing and nothing else.
4. **Product changes only if a team would build them anyway.** Never add a step just to give an evaluator something to measure.
5. **Failures the evaluation exposes are kept unfixed.** They are the evidence the blog is built on. This covers agent failures and product bugs.

---

## 3. What was implemented

### 3.1 Making the trace carry the business outcome (agent change)

Evaluators read the trace and nothing else. Originally the trace ended at the validator's opinion. `save_expense` and `human_review` are calls made by orchestrator code, not agent tools, so nothing traced them, and a correctly processed receipt looked like a skipped step.

`app/receiptsagent/main.py` now:
- emits a tool span for every save and review call
- marks a Cedar denial as an error span
- stamps the outcome on the invocation span as `receipts.*` attributes: status, total, whether Cedar blocked it, the routing decision, both confidences, and the extracted merchant, date, currency, subtotal, tax and tip

These live in the agent rather than the test harness because a deployed trace has the same gap.

### 3.2 A local harness that runs the real code

`evals/` in the sample (first built as `receipts-idp-evaluation/`):

| File | What it does |
|---|---|
| `local_gateway.py` | A local MCP server standing in for the Gateway. Save, review and the three chat read tools run against an in-memory table, with a stand-in for the Cedar rule that can be switched off (`POLICY_ENABLED`). The recent-expenses tool deliberately copies the Lambda's order, a sort on a hashed id |
| `make_fixtures.py`, `fixtures/labels.json` | 9 synthetic receipts with their true fields and expected outcome: `clean`, `non_reconciling`, `over_threshold`, `duplicate_a` and `duplicate_b`, `split_a` and `split_b`, `injected` (a phishing instruction printed on it), `pii_heavy` (a card number and home address printed on it) |
| `run_dataset.py` | Runs every receipt through the real pipeline (Textract and Bedrock are real; Gateway and tables are local), saves each trace in ADOT format, and scores the code-based evaluators. `--without-policy` switches off the Cedar stand-in |
| `score_saved.py` | Re-scores saved traces with the built-in evaluators through the AgentCore `Evaluate` API, without re-running the agent |
| `fixtures/conversations.json` | One seeded chat user, 9 expenses (a Kuala Lumpur trip in MYR, two held for review), and 5 scripted conversations with a hand-worked expected answer per turn |
| `run_chat.py`, `score_chat.py` | Run each conversation as one session with one trace per turn, then score it |
| `run_deployed.py` | Runs the same receipts and conversations through the **deployed** stack: receipts through the real S3 front door, conversations through the chat Runtime. It collects each session's trace from CloudWatch, waiting until the trace is complete, and writes the same output shape, so the same scorers apply |

### 3.3 Product change: multi-turn chat

Each chat question used to open a fresh session with no memory, so a follow-up like "and at Starbucks?" had nothing to refer to. The chat now keeps its history within a session:
- History is held in process, keyed by **(verified user, session id)**, so a session id replayed under another identity starts empty.
- It is trimmed by a sliding window that never separates a tool call from its result.
- The REPL (`scripts/chat.py`) keeps one Runtime session for the whole chat.

**A related fix:** chat questions were writing a junk row to the receipt run ledger. They no longer do. Chat stays read-only.

### 3.4 The evaluators

**Eight evaluators are active.**

| # | Evaluator | Kind | What it judges | Serves | Runs on |
|---|---|---|---|---|---|
| 1 | `ReceiptsExtractionAccuracy` | Code | Every extracted field against the label. The value is the dollar gap on the total | B2 | Labelled set |
| 2 | `Builtin.ToolParameterAccuracy` on `submit_expense` | Built-in judge | Whether the extractor put in a value its own input never contained | B2 diagnostic | Offline, extractor part of the trace only |
| 3 | `ReceiptsRoutingOutcome` | Code | The validator's save-or-review call, as one of four outcomes. Judged on what the validator was shown: if the extraction was wrong, review was correct | B4 | Labelled set |
| 4 | `Builtin.GoalSuccessRate` with assertions | Built-in judge | Whether the validator named the actual problem | B4 diagnostic | Offline, trace through the validator |
| 5 | `ReceiptsThresholdControl` | Code, control monitor | Whether anything at or above $2,000 saved automatically | B3 | **Live in AgentCore** (`ReceiptsLive`) |
| 6 | `ThirdParty.DeepEval.ConversationCompleteness` | Third-party judge | Share of the employee's requests that were handled | C1 | **Live in AgentCore** (`ReceiptsAgent_ChatLive`) |
| 7 | `ThirdParty.DeepEval.KnowledgeRetention` | Third-party judge | Whether earlier turns are remembered | C1 diagnostic only | **Live in AgentCore** (`ReceiptsAgent_ChatLive`) |
| 8 | `Builtin.Correctness` with expected answers | Built-in judge | Each chat answer against its expected answer, matched per turn by trace id | C2 | Labelled set |

The three code-based evaluators (1, 3, 5) are deployed as AgentCore evaluators, each its own Lambda built from `evaluators/business_outcomes/`, the same code the harness calls.

**Not evaluators, but reported:**
- Straight-through rate, as a count over saved statuses.
- A cross-receipt check for duplicates and split bills. No per-receipt evaluator can see a failure that only exists between receipts.

### 3.5 Deployed to AgentCore

The sample deploys with one command (`./deploy.sh`), with no local container engine: CodeBuild builds the Runtime images, and the evaluator Lambdas are packaged with `uv`.

- **A rebuilt CDK stack.** The original sample's stack source had never been committed, because the repository's root `.gitignore` ignores every `lib/`. It was rebuilt from the sample's documentation and the sibling samples' pattern. A folder-level `.gitignore` exception keeps it in the repository, along with the Runtime's Dockerfile and the env template, which the root rules also ignore. The root file is unchanged.
- **Two Runtimes from one codebase: pipeline and chat.** Online evaluation selects sessions by service name, so each online configuration scores only its own workload.
- **Online configurations:**
  - `ReceiptsLive` is declared in `agentcore.json`.
  - `ReceiptsAgent_ChatLive` uses managed third-party evaluator ids, which the API accepts and the CloudFormation schema does not yet. So `scripts/chat_online_eval.py` creates it after the stack deploys, with an execution role the stack creates.
- **The old judges are gone:** the blended judge and the copied `Helpfulness`/`Correctness`/`ToolSelectionAccuracy` online set.

**Fixed while deploying:**
- **The container exported no traces.** It started with `python main.py`, not under `opentelemetry-instrument`, so observability and every evaluator were blind to the deployed agent. This had been in the original sample since it was first added.
- **Online evaluation passes the evaluator Lambda neither its name nor its id.** The single name-routing handler returned `UNKNOWN_EVALUATOR`, so each deployed evaluator now has its own entry point.
- **`npx cdk` ran the project's own app instead of the CDK CLI,** because `package.json` names the app `cdk`. `deploy.sh` now calls the CLI by path.

### 3.6 How some of the design problems were solved

- **Scoping what a judge sees.** In one trace holding three models, a judge scoring the extractor also saw the validator's input, which repeats the extractor's own values. So the harness sends each judge only the part of the trace up to the end of the model it is judging.
- **Assertions that do not assume a run.** The right-reason assertions come from two places: problems printed on the receipt (stored in the labels), and one assertion per field that extraction accuracy found wrong *in that run*. Receipts with nothing to name are not scored, because an assertion that never engages always passes.
- **No double counting.** Routing's expected answer switches to "review" whenever the extraction was wrong. The validator catching the extractor's mistake is then not counted as a false alarm.
- **Per-turn answers in one call.** `Correctness` is trace-level. Each chat turn is its own trace, and one `Evaluate` call carries one expected answer per turn, keyed by trace id.

### 3.7 The validator acts through its own tools

Until this change, the validator reported a verdict and orchestrator code made the save or review call. Strands does not trace calls made by code, so the Gateway calls carried hand-made spans, and the decision did not show as an agent action. The validator now calls `approve_expense` or `send_to_review` itself (ADR-0019 in the sample).

- **What stayed in code:** which tools are offered, one decision only, the fallback to review, and the expense that is written. The tools take no amounts or fields.
- **What the trace shows now:** the validator's `execute_tool approve_expense` or `send_to_review` span, with the Gateway call beneath it. On review, the note writer runs beneath it too.
- **What it changed in the harness:** the note writer and the `human_review` call now sit inside the validator's part of the trace. Selecting the validator's part by position would have included the note writer's text, which repeats the validator's concern and could earn it credit. The harness now selects each agent by name and excludes the note writer and the `human_review` call.
- **The right-reason assertion was re-worded and re-tested:** "The validator, in its decision (approve_expense or send_to_review), identifies that ...". See 4.1.
- **Verified after redeploy:**
  - Live tests: 22 of 22 user-facing (Cedar included), resilience 4 passed and 1 skipped by design.
  - The 9 labelled receipts through the front door (`out/deployed-00a58b05`). Every trace shows the decision as the validator's own tool call. The $2,400 receipt reads `approve_expense`, then `save_expense` denied by Cedar, then the note writer and `human_review`, all beneath the approval.
  - The live `ReceiptsLive` monitor scored that session `held`.
  - Scores: right reason 3 of 3; invented values 2 of 2 caught, plus the known false alarm on the honest low confidence; review-queue precision 67% (4 of 6).
  - These differ from the previous deployed run only by the validator's usual run-to-run variation, since the prompt criteria did not change. This time the extractor left `pii_heavy`'s date empty instead of inventing one, and the validator held it for the missing date. The validator held `split_a` ($1,250) for its size. Both count as false alarms. `split_b` was approved, which is the split-purchase bypass the validator cannot see from one receipt.

---

## 4. The tests

### 4.1 Contrast tests: can each judge tell good from bad?

Each judge was run on real traces and on copies with exactly one thing changed.

| Judge | Cases | Result |
|---|---|---|
| `ToolParameterAccuracy` | 7: a real correct date, the date edited to one not in the OCR, the total edited, OCR and value both changed consistently, three real invented dates | Whole trace: **4 of 7 wrong**. Extractor part only: **7 of 7 right**, naming the right field each time |
| `GoalSuccessRate` (right reason) | 14: each receipt against its own assertion and against another receipt's | **14 of 14** |
| `GoalSuccessRate`, after the validator moved to decision tools | 4, each scored twice: the real `send_to_review` trace, a terse but correct concern, a vague concern, the wrong problem named. The extractor's own "does not reconcile" flag stays in every copy | **8 of 8**; the extractor's flag did not earn the validator credit |
| `ConversationCompleteness` | A real conversation, and the same with its final answer replaced by a deflection; each scored twice | 1.0, 1.0, then **0.67, 0.67** |
| `KnowledgeRetention` | A real conversation, and the same with turn 2 re-asking for facts turn 1 gave; each scored twice | 1.0, 1.0, then **0.67, 0.67** |
| `Correctness` | A correct answer, the same edited to a wrong total, the real wrong answer, another correct total, a correct refusal; each scored twice | **10 of 10** |

### 4.2 End-to-end runs of the real pipeline

- **The labelled receipt set:** all 9 receipts through Textract and Bedrock, scored by the code-based evaluators, then re-scored with the built-in judges.
- **The control monitor, with and without the policy:** the $2,400 receipt was run with the Cedar stand-in on and off. With it off, the validator approved, the receipt saved, and the monitor reported a **breach**. With it on, that run's validator held the receipt itself, so Cedar was not exercised that time. Earlier runs had shown the validator approving at confidence 93-97 and Cedar denying.
- **The chat set:** all 5 conversations, scored by the three chat evaluators.

### 4.3 Unit tests (no AWS)

`tests/test_chat_session.py` in the agent, 6 tests:
- history is shared within one (user, session)
- a different user with the same session id starts empty
- no session id means no history
- separate sessions do not share
- the window size is fixed
- chat questions no longer write to the receipt ledger

`tests/test_decision.py`, 10 tests: approve saves; the approve tool takes no expense fields; review files the reviewer note; a second decision is refused; no decision means review; forceReview offers only review; a Cedar denial files a review; a Gateway failure is raised; and the harness trims the trace to the validator without the note writer.

All 79 unit tests in the sample pass. They include tests that the deployed evaluators route correctly on both the on-demand path (name) and the online path (neither name nor id), and that totals convert to integer cents. The code-based evaluators were also checked by calling their handler directly with hand-built spans.

### 4.4 Live tests against the deployed stack

- **User-facing tests:** pipeline, S3 front door, chat identity and IDOR, run ledger, tools, and Cedar. **All pass** after the Cedar fix below: 10 of 10 Cedar tests, 12 of 12 for the rest.
- **The deployed code-based evaluators, called by AgentCore:** the harness runs the evaluator code in-process, and the online config exercises only the threshold monitor. So the extraction and routing Lambdas had not been invoked by AgentCore. Two checks now cover them:
  - The Evaluate API on the 9 deployed receipt traces (`out/deployed-00a58b05`): the deployed extraction and routing evaluators gave the same label as the local code on all 18 scores. The two cross-receipt receipts score `FalseClear` when called directly, as expected, because leaving them out is the harness's job, not the evaluator's.
  - `tests/test_e2e_evaluators_live.py`, 13 cases through the Evaluate API: every label of all three evaluators, the "judged on what it was shown" rule, and a missing label reported as an error. **13 of 13 pass.**
- **Resilience tests:** ladder flip, the alarm-to-controller loop with its cooldown, and the L4 drain. **4 passed, 1 skipped by design**; the live Bedrock 503 test was already marked as impossible to simulate faithfully.
- **Cedar boundary cases:**
  - $2,000 and $2,000.50 denied
  - $1,999, $1,250.0, $15.90 and $1,999.99 allowed
  - a save without integer cents denied

  Before the fix, the $15.90 and $1,999.99 cases failed. See 5.2.

### 4.5 The evaluators against the deployed system

- **Live, in AgentCore:**
  - `ReceiptsAgent_ChatLive` wrote ConversationCompleteness and KnowledgeRetention scores for each conversation.
  - `ReceiptsLive` scored a $2,400 receipt `held`, "blocked by the policy".
- **On demand (`run_deployed.py`):** the 9 labelled receipts through the front door and the 5 conversations through the chat Runtime, scored with the same scorers as local runs. See 5.1.

---

## 5. Results

### 5.1 Numbers

**Local run** (the real agent code against the stand-in Gateway):

| Measure | Value |
|---|---|
| Straight-through rate | 22% (2 of 9) |
| Dollar-weighted error | 0.00% |
| Receipts with a field wrong besides the total | 3 of 9, all invented dates |
| Invented values caught by `ToolParameterAccuracy` | 3 of 3, plus 1 false alarm on an honest low confidence |
| Routing precision | 83% (5 of 6 escalations needed); 2 cross-receipt receipts not scored |
| Validator named the actual problem | 4 of 4 |
| Threshold control | 0 breaches with the policy on; 1 caught with it off |
| Chat answers correct | 10 of 11 scored turns |
| Chat completeness | 1.0 on four conversations, 0.5 on the correct refusal |

**On the deployed stack**, after the Cedar fix:
- Extraction accuracy found the same 3 invented dates; dollar error 0.00%.
- `ToolParameterAccuracy` caught 3 of 3 invented values, with the same 1 false alarm.
- The validator named the actual problem on 4 of 4.
- The two $13.49 duplicates, approved by the validator, saved automatically.
- The $2,400 receipt, approved by the validator, was blocked by the `>= $2,000` rule.
- Chat Correctness: 10 of 12 turns. Both misses were "most recent" answers, caused by the recent-expenses ordering bug below.

### 5.2 What the evaluation found in the agent and the product (kept unfixed, except the Cedar policy)

1. **Invented dates.** On three receipts Textract did not return the printed date, and the extractor made one up (2024-01-01, 1970-01-01, and 2029-11-01 taken from a card expiry) instead of reporting it missing. Dollar error read 0.00% throughout. The validator caught all three.
2. **Duplicate overwrite.** The expense id is a hash of user, merchant, date and total, and the write replaces any existing row. A second copy of a receipt silently **replaced** the first: data loss presented as deduplication.
3. **A control that held by accident.** A $2,400 dinner split into two bills went to review, but only because the validator disliked a $0.00 tip. The $2,000 rule never engaged.
4. **Cedar doing its job.** The validator approved a $2,400 receipt at high confidence, and the policy denied the save. This is the sample's central design claim.
5. **Reconciliation not enforced in code.** The extractor computes whether subtotal, tax and tip add up, but the orchestrator never reads it. Only the validator's prompt enforces it.
6. **Chat "most recent" wrong.** The recent-expenses tool promises newest first but sorts by a hashed id. The model trusted the description and named the wrong expense.
7. **The Cedar policy blocked every automatic save (fixed).** The policy compared `total >= 2000`. The Gateway passes totals such as 15.9, and even 1250.0 and 2400.0, as Cedar decimals, and Cedar will not compare a decimal with a whole number. So the policy errored, and a forbid that errors denies.
   - In the deployed sample nothing saved automatically.
   - The $2,000 rule only appeared to work, because the error blocked large receipts too.
   - The local stand-in compared plain numbers, so only a live boundary test could show it.
   - **Fixed at the user's request:** the orchestrator now sends `total_cents`, an integer, and the policy compares `total_cents >= 200000`, denying a save without it.

### 5.3 Traps in the evaluators themselves

1. **The whole-session trap.** A judge scoring one model in a multi-model trace can see later inputs that repeat that model's output, and then pass invented values. The documentation describes a narrower context than the service showed.
2. **Double counting across evaluators.** One extractor error was blamed on the validator too, until routing was judged on what the validator was shown.
3. **A judge exposing a flawed label.** The "reprint" assertion failed because the OCR step drops free text: the validator never saw the mark. The evaluation design was wrong, not the agent.
4. **Judges penalising correct behaviour.** `ToolParameterAccuracy` flags the model's honest low confidence as invented. `ConversationCompleteness` scores a correct refusal as half met.
5. **No ground truth, no view of correctness.** `ConversationCompleteness` scored a wrong answer 1.0. Only `Correctness` with an expected answer caught it.
6. **Noise.** `KnowledgeRetention` scored the same unedited conversation 0.67 once and 1.0 twice.
7. **Live and on-demand evaluation call a code-based evaluator differently.** On demand, the Lambda receives the evaluator's name; online, it received neither the name nor the id. An evaluator that routes on its name works in every local and on-demand test, then fails every live session.
8. **Deployed traces arrive over minutes.** The SDK's span collector returns as soon as any spans exist, so a trace scored straight away can be half there, and a missing save looks like a skipped step.

---

## 6. Limits

- 9 receipts and 11 scored chat turns. These show that each evaluator works, not rates that can be quoted.
- Synthetic receipts, one model, one environment.
- One deployment, one account and Region (us-west-2).
- The local stand-in for the Gateway is not the real policy engine: it compares plain numbers, which is why the Cedar bug appeared only when deployed. Anything that depends on Cedar's typing needs a live test.
- `ToolParameterAccuracy` works offline only. A live evaluation configuration scores the whole session, where the trace trap applies.
- Expected answers and labels are hand-written, so they are part of what is being trusted.
