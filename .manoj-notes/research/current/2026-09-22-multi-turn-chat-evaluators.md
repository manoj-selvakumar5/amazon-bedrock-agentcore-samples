# Multi-Turn Chat, Scored by ConversationCompleteness and KnowledgeRetention

**Date:** 2026-09-22

The chat assistant answered each question in its own session with no memory, so C1 self-service resolution was capped by design (09-17 chat note). This note covers the product change that fixes that, and the two managed third-party evaluators it makes applicable.

## The product change

- **`main.py`:** chat keeps its history within a session.
  - It is keyed by **(verified user, session id)**, so a session id replayed under another identity starts empty. That keeps the ADR-0016 guarantee.
  - The session id is the Runtime's own session id when deployed, or `payload["session_id"]` locally.
  - History is held in process. AgentCore Runtime pins a session to one microVM, so that is the platform's session model. It is trimmed by Strands' `SlidingWindowConversationManager` (40 messages), which never splits a tool call from its result.
  - AgentCore Memory was rejected: its strategies are namespaced for receipt recall, and chat turns would pollute them.
  - The prompt gains one line: use earlier turns to resolve follow-ups, but look the data up again before stating figures.
- **`chat.py`:** the REPL keeps one Runtime session for the whole chat. `ask.py` one-shots stay stateless.
- **Ledger fix:** chat questions no longer write a junk row under `hash("")` to the receipt run ledger. That was the bug in the 09-17 chat note, and multi-turn would have multiplied it.
- **Tests:** `tests/test_chat_session.py`, 6 unit tests with no AWS. All 64 unit tests pass.
- Chat stays read-only. ADR-0016 is unchanged.

## The harness

`receipts-idp-evaluation`:
- `local_gateway.py` gains the three chat read tools.
- `fixtures/conversations.json`: one seeded user, 9 expenses, a Kuala Lumpur trip in MYR, two held for review, and 5 scripted conversations.
- `run_chat.py` runs each conversation as one session, with one trace per turn.
- `score_chat.py` scores each session.

History works. In `merchant_followups`, "And at Starbucks?" was read as a spend question, and "Which of these was the most recent?" compared all three expenses.

## Contrast tests

Each one edits a single assistant answer; results are in `out/contrast-chat/`.

| Evaluator | Conversation | As run | One answer edited | Verdict |
|---|---|---|---|---|
| ConversationCompleteness | `held_explained`, final answer replaced by "I'm not able to help with that." | 1.0, 1.0 | 0.67, 0.67 | **Passes.** It named the one intention left unmet |
| KnowledgeRetention | `trip_context`, turn-2 answer replaced by "Which trip do you mean?" | 1.0, 1.0 | 0.67, 0.67 | **Passes**, with the reliability caveats below |

## Real run, `chat-e33d8497`

| Conversation | Turns | Completeness | Retention | What actually happened |
|---|---|---|---|---|
| held_explained | 3 | 1.0 | 1.0 | All three answers right |
| trip_context | 3 | 1.0 | 0.67 (1.0 on two re-scores) | Right. The judge's "forgot June 27" is false: no expense exists that day |
| merchant_followups | 3 | 1.0 | 0.5 | Right, apart from one slip ("two Starbucks purchases"). The judge also called the looked-up dates and amounts "fabricated" |
| cannot_write | 2 | **0.5** | 1.0 | Correct refusal of a delete, then the right date |
| single_question | 1 | **1.0** | 1.0 | **Wrong answer** (see below) |

## What the judges get wrong, stated plainly

1. **Completeness cannot tell an answer from a correct answer.** `single_question` scored 1.0 while the agent named the wrong most recent expense. It has no ground truth, so it judges only whether the request looked handled.
2. **Completeness punishes a correct refusal.** `cannot_write` scored 0.5 because the delete request, correctly refused under the read-only design, counts as an unmet intention. Read a low score next to what was asked.
3. **KnowledgeRetention is noisy on real conversations.** The same `trip_context` trace scored 0.67 once and 1.0 twice. On `merchant_followups` it treated facts the agent looked up as "never part of the prior knowledge", so it counts tool results as invented. It passes a clean contrast, but a single score on one conversation is not reliable. Use it only as an aggregate diagnostic.

Verdict: **ConversationCompleteness joins the evaluator set** as the live C1 signal, with limits 1 and 2 stated. **KnowledgeRetention joins as a diagnostic only**, never quoted per conversation.

## A product bug the run exposed

The "most recent expense" answer was wrong because of the tool, not the model. `get_recent_expenses` promises "newest first" in its schema, but it queries with `ScanIndexForward=False` on the `expenseId` sort key, and that key is a content hash. So the order is effectively random, and the model trusted the description and took the first row. The local gateway mirrors the Lambda's order, so the deployed sample has the same bug.

No evaluator here catches it, because none has the right answer for chat. Catching it would need `Builtin.Correctness` with expected answers over the seeded data. It is not fixed, pending the decision on whether product bugs stay as evidence.
