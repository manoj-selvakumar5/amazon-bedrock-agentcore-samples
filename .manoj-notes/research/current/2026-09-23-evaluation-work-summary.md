# Evaluating the Receipts IDP Agent: What Was Built, How, and How It Was Tested

**Date:** 2026-09-23
**Branch:** `receipts-idp-eval-revamp`

This note stands on its own. It explains the system under evaluation, the conceptual approach, what was implemented, every kind of test run, and the results, including what did not work.

---

## 1. The system being evaluated

The subject is the **receipts intelligent document processing sample** (`02-use-cases/02-workflow-automation-agents/receipts-intelligent-document-processing-agent`). It runs on Amazon Bedrock AgentCore and has two workloads.

**The receipt pipeline.** A receipt image lands in S3 and is processed with no user involved:

1. **OCR.** Amazon Textract `AnalyzeExpense` reads the image. The code passes the models only the fields Textract recognises (vendor, date, totals and so on) plus line items. Other printed text is dropped.
2. **Extractor.** A model reads the OCR output and calls its one tool, `submit_expense`, with merchant, date, currency, subtotal, tax, tip, total, category and a self-reported confidence.
3. **Validator.** A second, independent model sees the OCR and the extraction, and calls `submit_validation` with a routing decision (`AUTO_PERSIST` or `NEEDS_REVIEW`), a confidence and its concerns.
4. **Orchestrator code** acts on the decision:
   - it calls `save_expense`, or
   - it calls `human_review`, which writes the expense with status `needs_review` so a person can look at it.
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

`02-use-cases/02-workflow-automation-agents/receipts-idp-evaluation/`:

| File | What it does |
|---|---|
| `local_gateway.py` | A local MCP server standing in for the Gateway. Save, review and the three chat read tools run against an in-memory table, with a stand-in for the Cedar rule that can be switched off (`POLICY_ENABLED`). The recent-expenses tool deliberately copies the Lambda's order, a sort on a hashed id |
| `make_fixtures.py`, `fixtures/labels.json` | 9 synthetic receipts with their true fields and expected outcome: `clean`, `non_reconciling`, `over_threshold`, `duplicate_a` and `duplicate_b`, `split_a` and `split_b`, `injected` (a phishing instruction printed on it), `pii_heavy` (a card number and home address printed on it) |
| `run_dataset.py` | Runs every receipt through the real pipeline (Textract and Bedrock are real; Gateway and tables are local), saves each trace in ADOT format, and scores the code-based evaluators. `--without-policy` switches off the Cedar stand-in |
| `score_saved.py` | Re-scores saved traces with the built-in evaluators through the AgentCore `Evaluate` API, without re-running the agent |
| `fixtures/conversations.json` | One seeded chat user, 9 expenses (a Kuala Lumpur trip in MYR, two held for review), and 5 scripted conversations with a hand-worked expected answer per turn |
| `run_chat.py`, `score_chat.py` | Run each conversation as one session with one trace per turn, then score it |

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
| 5 | `ReceiptsThresholdControl` | Code, control monitor | Whether anything at or above $2,000 saved automatically | B3 | Live-capable |
| 6 | `ThirdParty.DeepEval.ConversationCompleteness` | Third-party judge | Share of the employee's requests that were handled | C1 | Live-capable |
| 7 | `ThirdParty.DeepEval.KnowledgeRetention` | Third-party judge | Whether earlier turns are remembered | C1 diagnostic only | Live-capable |
| 8 | `Builtin.Correctness` with expected answers | Built-in judge | Each chat answer against its expected answer, matched per turn by trace id | C2 | Labelled set |

**Not evaluators, but reported:**
- Straight-through rate, as a count over saved statuses.
- A cross-receipt check for duplicates and split bills. No per-receipt evaluator can see a failure that only exists between receipts.

### 3.5 How some of the design problems were solved

- **Scoping what a judge sees.** In one trace holding three models, a judge scoring the extractor also saw the validator's input, which repeats the extractor's own values. So the harness sends each judge only the part of the trace up to the end of the model it is judging.
- **Assertions that do not assume a run.** The right-reason assertions come from two places: problems printed on the receipt (stored in the labels), and one assertion per field that extraction accuracy found wrong *in that run*. Receipts with nothing to name are not scored, because an assertion that never engages always passes.
- **No double counting.** Routing's expected answer switches to "review" whenever the extraction was wrong. The validator catching the extractor's mistake is then not counted as a false alarm.
- **Per-turn answers in one call.** `Correctness` is trace-level. Each chat turn is its own trace, and one `Evaluate` call carries one expected answer per turn, keyed by trace id.

---

## 4. The tests

### 4.1 Contrast tests: can each judge tell good from bad?

Each judge was run on real traces and on copies with exactly one thing changed.

| Judge | Cases | Result |
|---|---|---|
| `ToolParameterAccuracy` | 7: a real correct date, the date edited to one not in the OCR, the total edited, OCR and value both changed consistently, three real invented dates | Whole trace: **4 of 7 wrong**. Extractor part only: **7 of 7 right**, naming the right field each time |
| `GoalSuccessRate` (right reason) | 14: each receipt against its own assertion and against another receipt's | **14 of 14** |
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

All 64 unit tests in the sample pass. The code-based evaluators were also checked by calling their handler directly with hand-built spans.

### 4.4 Deploy-time tests (written, not yet run)

`tests/test_e2e_cedar_live.py` gains boundary cases against the real Gateway:
- $2,000.00: denied
- $1,999: allowed
- $2,000.50: denied
- $15.90 and $1,999.99: allowed

The two cases with cents under the limit settle an open question. The policy's own description suggests a total with cents makes the comparison fail and the save be denied. They skip cleanly because no stack is deployed.

---

## 5. Results

### 5.1 Latest numbers

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

### 5.2 What the evaluation found in the agent and the product (all kept unfixed)

1. **Invented dates.** On three receipts Textract did not return the printed date, and the extractor made one up (2024-01-01, 1970-01-01, and 2029-11-01 taken from a card expiry) instead of reporting it missing. Dollar error read 0.00% throughout. The validator caught all three.
2. **Duplicate overwrite.** The expense id is a hash of user, merchant, date and total, and the write replaces any existing row. A second copy of a receipt silently **replaced** the first: data loss presented as deduplication.
3. **A control that held by accident.** A $2,400 dinner split into two bills went to review, but only because the validator disliked a $0.00 tip. The $2,000 rule never engaged.
4. **Cedar doing its job.** The validator approved a $2,400 receipt at high confidence, and the policy denied the save. This is the sample's central design claim.
5. **Reconciliation not enforced in code.** The extractor computes whether subtotal, tax and tip add up, but the orchestrator never reads it. Only the validator's prompt enforces it.
6. **Chat "most recent" wrong.** The recent-expenses tool promises newest first but sorts by a hashed id. The model trusted the description and named the wrong expense.
7. **Open:** whether the deployed policy blocks every total with cents.

### 5.3 Traps in the evaluators themselves

1. **The whole-session trap.** A judge scoring one model in a multi-model trace can see later inputs that repeat that model's output, and then pass invented values. The documentation describes a narrower context than the service showed.
2. **Double counting across evaluators.** One extractor error was blamed on the validator too, until routing was judged on what the validator was shown.
3. **A judge exposing a flawed label.** The "reprint" assertion failed because the OCR step drops free text: the validator never saw the mark. The evaluation design was wrong, not the agent.
4. **Judges penalising correct behaviour.** `ToolParameterAccuracy` flags the model's honest low confidence as invented. `ConversationCompleteness` scores a correct refusal as half met.
5. **No ground truth, no view of correctness.** `ConversationCompleteness` scored a wrong answer 1.0. Only `Correctness` with an expected answer caught it.
6. **Noise.** `KnowledgeRetention` scored the same unedited conversation 0.67 once and 1.0 twice.

---

## 6. Limits

- 9 receipts and 11 scored chat turns. These show that each evaluator works, not rates that can be quoted.
- Synthetic receipts, one model, one environment.
- Nothing is deployed:
  - The Gateway, tables and Cedar policy ran as local stand-ins.
  - The sample cannot deploy from the repository as it stands. Its CDK stack source was never committed, because a blanket `lib/` rule in the repository's root ignore file swallowed it.
- `ToolParameterAccuracy` works offline only. A live evaluation configuration scores the whole session, where the trace trap applies.
- Expected answers and labels are hand-written, so they are part of what is being trusted.
