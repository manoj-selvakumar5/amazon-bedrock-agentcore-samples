# Framework 1 on the Chat Workload

**Date:** 2026-09-17

Framework 1 was only ever run on the extraction pipeline. That produced B1 to B7. The conversational path got a single line, "query trust", and no economics at all. This note runs the same three questions on the chat workload, so the work proposed for it traces back to a business number instead of to a list of metrics it would unlock.

## Question 1: why does this agent exist

So an employee can find out what happened to their own money without asking anyone. Today that question goes to a finance mailbox, a manager, or an expense tool nobody can navigate.

The agent is not there to hold a conversation. It is there to end a question.

## Question 2: what would you measure regardless of implementation

Apply the swap test. Replace the agent with a finance analyst answering emails, a monthly PDF statement, or a BI dashboard. Four measures survive all three.

| | Metric | What it means and why the business should care | How it is measured |
|---|---|---|---|
| C1 | Self-service resolution rate | The share of questions the employee gets a usable answer to without a person being pulled in. This is the chat path's version of straight-through processing, and it is the only number that says whether the agent replaced any work. If people ask the agent and then email finance anyway, the agent added cost. | Questions resolved without escalation divided by questions asked. Example: 100 questions, 78 resolved, 22 escalated or abandoned, gives 78%. |
| C2 | Answer accuracy | Of the answers it gave, how many were right. A wrong spending figure is worse than no answer, because the employee acts on it: they file a duplicate claim, or they argue with finance using a number the agent invented. | Compare answers against known values for a fixed set of questions. Report the rate of answers that were wrong, not just the rate that were vague. |
| C3 | Data-boundary breaches | The number of times anyone saw data that was not theirs. One breach is an incident, not a percentage point, so the target is zero rather than a good average. | Count answers containing another user's data. Every one is investigated individually. |
| C4 | Cost per question | What it costs to answer one question, against what it cost when a person answered it. If a question costs more to answer automatically, the agent is not saving anything however good the answers are. | Model and tool charges divided by questions answered, with escalated questions charged at analyst time. |

### What the test rejects

`Helpfulness`, `KnowledgeRetention`, `TurnRelevancy`, `ConversationCompleteness` all fail the swap test: each one presupposes an agent holding a conversation. A PDF statement has no turns to be relevant to.

That does not make them useless. They are the diagnostics that explain why C1 moved. If self-service resolution drops, forgetting what the user said two turns ago is one of the few reasons it can drop. They belong to Framework 2, not here.

## Question 3: how those translate into evaluators

| Metric | Level | Approach | Why |
|---|---|---|---|
| C1 | SESSION | Code-based, with `GoalAccuracy` or `ConversationCompleteness` as a judge proxy | Resolution only exists across a whole conversation. A single reply cannot be "resolved". |
| C2 | TRACE | Code-based against known answers offline; `Builtin.Faithfulness` as the live proxy | The comparison is arithmetic when the answer is known. In production no answer is known, so the fallback is whether the reply is consistent with what the tools actually returned. |
| C3 | SESSION | Code-based scan for another user's values | `PIILeakage` cannot do this. It detects personal data, not whose. The agent is supposed to show the user their own card details. |
| C4 | SESSION | Code-based over span token usage | Arithmetic. |

Same shape as the extraction result: the business metrics are mostly computed, not judged.

## What the sample can produce today

**Bucket A, computable now:** C4. Token usage is already on the spans.

**Bucket B, needs a labelled set:** C2 and C3. Both need known answers, which the sample can supply cheaply because the expense data is seeded: `seed_dynamodb.py` writes one user, and `user-demo.sh` writes three expenses whose totals are known (MYR 30.91 + 37.10 = 68.01, and a Starbucks 18.50). A fixed question set over that data has arithmetic answers. C3 needs a second user with distinctive values, which is what the existing `test_e2e_chat_live.py` cross-user test already does with a unique amount.

**Bucket C, needs new code:** C1, and not for a small reason.

## The structural blocker on C1

Each question opens its own runtime session (`ask.py` mints a new `runtimeSessionId` per call) and builds a fresh agent with no history. Three consequences:

- **There is no conversation to resolve.** Any question that needs a clarifying follow-up cannot be answered, so C1 is capped by the design rather than by the model.
- **SESSION and TRACE collapse.** Every session holds exactly one turn, so session-level evaluators measure the same thing as trace-level ones.
- **The multi-turn judges have nothing to score.** This is why they currently look inapplicable.

The fix is small: reuse one session id for a chat, and attach a session manager. `strands.session.FileSessionManager` does this with no AWS dependency, and AgentCore Memory is already wired into the extraction path if a deployed version is wanted.

## A bug this exposed

In a deployed stack, every chat question writes a row to the **receipt** ledger. `invoke()` calls `_emit_run_ledger()` for all results, including query-mode ones, and `build_run_event` is handed `s3_uri=None`. So:

- `receiptId` is `hash("")`, a constant: `rcpt-e3b0c44298fc1c14`. Every question writes to the same row.
- `status` is `unknown`, because a query result has neither a status nor an error.

Two effects. The receipt ledger accumulates a junk row that "what happened to receipt X" queries can hit, and there is no per-question record anywhere, so C1 and C4 have no durable substrate outside traces.

Cheapest fix: skip the emit in query mode. Better fix: emit a separate question event, which is also what C1 needs to count escalations.

## What I would build, in order

1. **Stop the chat path writing to the receipt ledger.** One condition in `invoke()`.
2. **One session per chat, with history.** Unlocks C1 as a measurable quantity and makes the four multi-turn judges applicable.
3. **A fixed question set over the seeded expenses.** Unlocks C2 and C3, and reuses the cross-user check that already exists as an e2e test.
4. **Reuse the extraction cost evaluator for C4.** Token attributes are identical.

## How the three proposed ideas map now

| Idea | Business metric | Workload |
|---|---|---|
| Multi-turn chat | C1 self-service resolution, C2 answer accuracy | Chat |
| Adversarial receipts | B3 control effectiveness, B2 dollar-weighted error | Extraction |
| Reviewer note | B6 cost per receipt, B4 review-queue precision, B3 via leakage | Extraction |

Before this note, multi-turn chat was the weakest of the three: it unlocked five third-party metrics and moved no business number, which is exactly what Framework 1 exists to catch. With C1 and C2 defined it becomes the enabler of a business outcome, and the third-party metrics become the diagnostics underneath it.
