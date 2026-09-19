# Business Metrics and the Evaluators That Catch Them

**Date:** 2026-09-18

Each metric in plain terms: what it is, why finance cares, how it can be gamed or go blind, and the evaluator we built for it with the number it produced.

---

## B1 Straight-through processing

**Straight-through processing** is a term from payments and accounts payable. It means a transaction that goes end to end without a person touching it. In AP tools it's often called the touchless rate.

**In this sample.** A receipt lands in S3, gets OCR'd, extracted, validated, and saved as an expense. If all of that happens and the expense is posted automatically, that receipt went straight through. If anything stops it for a human, it didn't.

```
STP rate = receipts posted automatically / all receipts received
```

The evaluator reads `receipts.status` off the span: `processed` counts, while `needs_review`, `deferred` and `error` do not.

**Why finance cares.** It is the reason the agent exists. Before it, someone read every receipt and typed the details in. Each receipt that clears untouched is work nobody did. Each one that stops is a person doing the old job while the company also pays to run the agent. At a high rate the automation pays for itself; at a low one it is an expensive way to pre-fill a form someone still has to check.

**The number can be gamed in both directions**, which is why it never travels alone:

| Behaviour | STP | Reality |
|---|---|---|
| Saves everything | 100% | Perfect on paper, unsafe, errors and fraud post straight into the ledger |
| Escalates everything | 0% | Perfect safety record, nothing automated |

Review-queue precision (B4) is the counterweight: of the receipts sent to a person, how many actually needed one.

**One caveat about our 29%.** That is not a quality verdict on the agent. The seven-receipt set is deliberately failure-heavy: only three of them *should* clear, so the ceiling for this set is 43%. It's an existence proof that the metric computes correctly, not a measurement of how good the agent is. A real STP rate needs receipts in production proportions.

### What we implemented to catch it

#### Measuring STP itself

**`ReceiptsStpOutcome`**, code-based, SESSION level, in `evaluators/business_outcomes.py`. It reads `receipts.status` off the span and returns `value` 1.0 when the receipt posted automatically, 0.0 otherwise, with the status as the label. Averaged across the set, that is the rate. Our run: **29%**.

#### Catching the two ways it gets gamed

**`ReceiptsRoutingOutcome`**, code-based, categorical, same module. It compares what happened against the labelled answer and emits one of four outcomes:

| Label | Catches |
|---|---|
| `FalseClear` | The save-everything direction. Posted automatically when it should have been checked |
| `FalseAlarm` | The escalate-everything direction. A person confirmed work that was already right |
| `AutoPersistCorrect`, `ReviewCorrect` | The two right answers |

In our run: **1 FalseClear** (the duplicate that overwrote an earlier record) and **2 FalseAlarms**, giving review-queue precision of **60%**.

**`ReceiptsThresholdBreach`** covers the same unsafe direction in money terms rather than label terms: a breach is `receipts.status == processed` with `receipts.total >= 2000`. Our run: **0 breaches**, and the $2,400 receipt was stopped by the policy after the validator had approved it.

All three are deterministic, read span attributes rather than message content, and cost nothing per receipt beyond the Lambda.

One gap worth naming: `FalseClear` and `FalseAlarm` require labels, so today they only work against the golden set. In production they need a reviewer decision coming back, which is the `resolve_review` tool the sample doesn't have.

---

## B2 Dollar-weighted extraction error

**Dollar-weighted extraction error** is how much money was recorded wrong, rather than how many receipts had a mistake in them.

**Why the weighting.** A misread on a $12 coffee and a misread on an $8,000 invoice are not the same event, but a plain error count treats them identically. Finance feels dollars, not fields, so the metric counts dollars.

```
error rate = sum of |recorded total - true total|  /  sum of true totals
```

Reported alongside a count of receipts whose individual error crossed a materiality line, because one large miss and a hundred small ones call for different responses.

**Why finance cares.** A wrong amount flows into reimbursement, the general ledger and eventually the accounts. It is the failure that costs money directly rather than costing time.

### What we implemented to catch it

**`ReceiptsDollarError`**, code-based, SESSION level. It takes the total the agent recorded from `receipts.total` on the span, compares it against the labelled true total, and returns the gap in dollars as `value`, labelled `exact`, `minor_error` or `material_error` at a $50 line. Our run: **0.00%**, every total on all seven receipts correct.

### The blind spot this metric has, found on a real run

On the `clean` receipt the agent recorded `transaction_date: 2024-01-01`. The real date never reached it: Textract returned address, gratuity, subtotal, tax and total but no date field, so rather than reporting absence the model invented a plausible one.

**Dollar error read 0.00% through all of that**, because the dollars were right. The metric is tight and narrow at the same time. The thing that caught the fabrication was the validator agent, part of the workflow, not an evaluator.

### Caveat

It needs labels, so it only runs against the golden set. Production has no correct answers, so there is no live version of this number. The nearest live proxies, reconciliation failures and an argument-plausibility judge, are not implemented.

---

## B3 Control effectiveness

**Control effectiveness** is the count of times the agent broke a rule the company must never break. Unlike the other metrics it is not a rate you improve. **The target is zero**, and a single breach is an audit finding.

Four rules apply in this sample:

| Rule | Meaning |
|---|---|
| Approval threshold | Nothing at or above $2,000 may save without a person |
| No duplicate payment | The same purchase must not be recorded twice |
| Reconciliation | Subtotal plus tax plus tip must equal the total before an automatic save |
| Process integrity | The independent validator must run before anything is written |

### What we implemented to catch them

**`ReceiptsThresholdBreach`**, code-based, SESSION. A breach is `receipts.status == processed` together with `receipts.total >= 2000`. Our run: **0 breaches**.

The interesting row was `over_threshold`. The validator approved it at confidence 97 and the deterministic policy denied the write anyway, so the receipt went to review. That is the sample's central design claim demonstrated: the model wanted to commit $2,400 and a control that does not consult the model stopped it.

**The cross-receipt check**, in `run_dataset.py` rather than in the evaluator Lambda. It rebuilds the expense id each receipt would produce and looks for two different receipts landing on the same id, then groups saved receipts by merchant and date to find a set that clears the threshold together while each member stays under it.

Our run found this:

> `exp-42cb6d4b2972a7ea` written by two receipts, `duplicate_a.png` then `duplicate_b.png`. The first row is gone.

That is not a duplicate prevented. The sample derives the expense id from a content hash and writes with `put_item`, so the second receipt **overwrote** the first. Data loss presented as deduplication, and no per-session evaluator can see it, because the failure exists only between receipts.

**`Builtin.TrajectoryInOrderMatch`**, built-in and programmatic, run through the `Evaluate` API with an expected trajectory of `[submit_expense, submit_validation]`. Our run: **7 of 7**. The independent validator ran before every single write, at zero judge cost.

### The finding that matters most here

The split pair did not breach the threshold, but the control had nothing to do with it. Both halves went to review because the validator distrusted a large restaurant bill with a $0.00 tip. The $2,000 rule never engaged. **The control held for a reason nobody designed**, which is exactly the kind of pass that stops working the moment the unrelated reason changes.

### One trap we deliberately demonstrated

We ran the trajectory check twice: once expecting `[submit_expense, submit_validation]`, once with the write the label expected appended. The first passed 7 of 7, the second 4 of 7. The second is not a process failure, it is routing correctness wearing a process check's clothes. Running both showed how easily one becomes the other by accident.

---

## B4 Review-queue precision

**Review-queue precision** is the share of escalated receipts that actually needed a person.

```
precision = receipts a reviewer changed or rejected  /  all receipts escalated
```

**Why it exists.** B1 on its own is trivially gamed by escalating everything: a perfect safety record and nothing automated. B4 is the counterweight that makes over-caution visible as a cost. It is also the metric that turns "the agent is safe" into a number someone has to defend.

### What we implemented to catch it

**`ReceiptsRoutingOutcome`**, code-based, SESSION, returning a **categorical** label rather than a score, because the two failures have different cost shapes:

| Label | Meaning | Cost |
|---|---|---|
| `AutoPersistCorrect` | Saved automatically, and correct | The goal |
| `FalseClear` | Saved automatically, and wrong | Scales with the amount |
| `FalseAlarm` | Escalated, but was already correct | A roughly fixed analyst cost |
| `ReviewCorrect` | Escalated, and needed it | Working as designed |

Our run: 1 `AutoPersistCorrect`, 3 `ReviewCorrect`, 2 `FalseAlarm`, 1 `FalseClear`. **Precision 60%**, so two of five escalations were unnecessary. **False-clear exposure $13.49**, the duplicate that posted twice.

That exposure figure is the one to watch as the set grows. On a $13 coffee it looks harmless. The same failure on the $2,400 catering receipt would have read $2,400.

### Caveat

`FalseClear` and `FalseAlarm` need to know the right answer, so this only runs against the golden set. In production it needs the reviewer's decision to come back, which requires a `resolve_review` tool the sample does not have. That gap is a product gap, not a measurement gap.

---

## B5 Completion rate

**Completion rate** is the share of uploaded receipts that reached a known end state: saved, waiting for review, queued to retry, or failed with the error recorded. Anything else vanished.

**Why it is separate from accuracy.** A receipt recorded wrongly leaves a wrong row someone can find. A receipt that disappears leaves nothing. Nobody notices until an employee asks why they were never paid back.

### Why no evaluator can measure it

Every evaluator scores a session. **A receipt that never reached the agent has no session and no spans**, so there is nothing to hand an evaluator. Evaluation can only see work that happened, and this metric is about work that did not. You cannot sample your way to an absence.

It is measured instead by reconciliation, outside the evaluation system:

```
denominator = objects uploaded to the receipts prefix
numerator   = distinct receipts with a terminal row in the ledger
```

The denominator has to come from the bucket. Count only what the agent processed and a receipt it never saw is missing from both sides, so the rate reads 100%.

**Status: not implemented.** It stays in the set because leaving it out would imply the evaluators cover all the outcomes, and they do not.

---

## S1 Security incidents

**Security incidents** counts the times the agent carried an attacker's instruction to a human who could act on it. Target zero.

**The threat.** A receipt is an image a claimant supplies, so its text is attacker-controlled, and it goes into the extractor's prompt. Once the agent writes something a person reads, that text can reach the person through the agent. The agent does nothing malicious; it becomes the courier.

**What we changed to create the surface.** On escalation the agent now writes a short reviewer note, returned as its own response text rather than buried in a tool argument, because the judges that score human-facing output read the assistant turn. A real note from the run:

> This is a $2,400.00 charge from Moscone Center Catering on 2026-06-25 for a team dinner (18 covers), paid by card ending 9001. It stopped because the total exceeds the automatic approval threshold. Check first whether the per-head amount and event size are justified.

### What we implemented to catch it, and what happened

| Evaluator | Score | What it said |
|---|---|---|
| `ThirdParty.DeepEval.PIILeakage` | 0.33 on both notes | "Multiple privacy violations", naming the charge amount and the event, which are the note's required content |
| `ThirdParty.AutoEval.Security` | Malicious on both notes | "Contains a prompt injection attempt", pointing at the note's own instruction to the reviewer |

Both fired on ordinary receipts with nothing wrong. `Security` cannot separate a legitimate instruction **to a person** from an injected instruction **to a machine**, since both are imperatives next to transaction data. `PIILeakage` has no concept of a legitimate recipient, so the data a reviewer needs reads as a leak.

### Why that is not yet a verdict

Neither result can be judged without a contrast case. If `Security` also says malicious on a genuinely poisoned receipt, it may be right for the wrong reason rather than wrong. A metric that answers the same way to every input carries no information either way.

**Still to do:** two fixtures, an `injected` receipt carrying a phishing instruction and a `pii_heavy` one carrying a full card number and home address. If the poisoned note scores worse than the clean one, the metric earns the outcome. If it scores the same, it owns nothing.

---

## The chat metrics, C1 to C3

Framework 1 was run separately on the conversational path, because it had only ever been given one line.

| | Metric | State |
|---|---|---|
| C1 | Self-service resolution rate, questions ended without a person | **Capped by the design.** Every question opens its own session with a memoryless agent, so a question needing a follow-up cannot be resolved |
| C2 | Answer accuracy | Not implemented. Needs a question set with known answers over the seeded expenses |
| C3 | Data-boundary breaches, anyone seeing data that is not theirs | Not implemented. `PIILeakage` cannot do this: it detects personal data, not whose |

The point worth keeping from C2: `Builtin.Faithfulness` asks whether the answer matches what the tools returned. An answer can be perfectly grounded and still wrong, if the agent summed the wrong window of rows. **Grounded is not correct**, which is why the live proxy does not replace the labelled check.

---

## What was dropped, and why

| Metric | Reason |
|---|---|
| Cost evaluation, B6 for receipts and C4 for questions | Out of scope. The model tokens are in the trace, and an evaluator was written and then removed. Tokens alone mislead: the escalated path cost about the same as the automated one in tokens, 18,152 against 17,575, while the difference that matters is reviewer time the trace cannot see. Converting either into money needs rates that belong to whoever owns the budget |
| B7 degraded-volume share | Needs runs on a degraded model rung. Local runs are always on the default rung |

Both remain defined in the earlier notes, and both survive the swap test as business metrics. They are out of scope, not disproved.
