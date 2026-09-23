# Chat Answer Accuracy (C2) with Builtin.Correctness

**Date:** 2026-09-23

C2, chat answer accuracy, was the one Framework 1 scoreboard metric with no evaluator. The two chat evaluators take no ground truth, and `ConversationCompleteness` scored `single_question` 1.0 while the agent named the wrong "most recent expense".

## How it works

- `fixtures/conversations.json` holds an expected answer per turn, written as the facts a correct reply must contain. `trip_context` turn 1 only sets context, so it has none and is not scored.
- `score_chat.py` sends each conversation to `Builtin.Correctness` in **one** `Evaluate` call, with one reference per turn keyed by that turn's trace id (`spanContext: {sessionId, traceId}`). `run_chat.py` already gives each turn its own trace.
- **Mapping check first.** On `merchant_followups`, the call returned one verdict per trace, and each explanation quoted that turn's own expected answer.
- Expected answers are read from the fixture, not from the saved run, so improved answers apply to runs already on disk.

## Contrast test: 10 of 10

Each case was scored twice; results are in `out/contrast-chat/correctness.json`.

| Case | Want | Got |
|---|---|---|
| `merchant_followups` turn 1 as run (68.01) | Correct | Correct, Correct |
| Same turn edited to 86.01 | Incorrect | Incorrect, Incorrect |
| `single_question` as run (the real wrong answer) | Incorrect | Incorrect, Incorrect |
| `held_explained` turn 3 as run (796.20) | Correct | Correct, Correct |
| `cannot_write` turn 1 as run (correct refusal) | Correct | Correct, Correct |

## Result on run `chat-e33d8497`

| Conversation | Completeness (C1) | Retention | Correctness (C2) |
|---|---|---|---|
| held_explained | 1.0 | 1.0 | 3/3 |
| trip_context | 1.0 | 1.0 | 2/2 |
| merchant_followups | 1.0 | 0.5 | 3/3 |
| cannot_write | 0.5 | 1.0 | 2/2 |
| single_question | **1.0** | 1.0 | **0/1** |

**10 of 11 scored turns correct.** The one miss is the real bug.

## What it adds, in one table

| Case | Completeness says | Correctness says | Truth |
|---|---|---|---|
| `single_question`, wrong most recent expense | handled (1.0) | **Incorrect** | wrong, from the `get_recent_expenses` hash ordering |
| `cannot_write`, correct refusal to delete | half met (0.5) | **Correct** | right, chat is read-only |

The two disagree in both directions, which is why both are kept. Completeness asks "was it handled?" and can run live. Correctness asks "was it right?" and needs labels. One question each.

The ordering bug stays unfixed as evidence. It is now caught by an evaluator rather than by reading transcripts.

## Limits

- 5 conversations, 11 scored turns: enough to show it discriminates, not enough to quote a rate.
- Offline only. Live chat has no expected answers.
- The expected answers are hand-written over seeded data. A wrong expected answer produces a wrong verdict, so they are part of what is being trusted.

## Evaluator count now

8 active:
- 5 on the receipt pipeline, including the threshold monitor.
- 3 on chat: Completeness (C1), Correctness (C2), Retention (diagnostic).
