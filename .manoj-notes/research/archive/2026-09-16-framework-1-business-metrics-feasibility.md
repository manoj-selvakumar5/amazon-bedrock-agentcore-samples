# Framework 1: Business Metrics Feasibility for the Receipts IDP Sample

**Date:** 2026-09-16

Verified against the code. Here is what Framework 1 yields for this use case, bucketed by **what the sample can actually produce**, since that determines what you have to build.

## The Framework 1 set

Derived from the economics of the job itself, not from a metric catalogue. 
- Seven survive the "measurable regardless of implementation" test, meaning the business metric would still make sense and still be tracked if you replaced the agent with a rules engine, an outsourced data-entry team, or a person typing receipts in by hand:

| | Metric | What it means and why the business should care | How it is measured |
|---|---|---|---|
| B1 | Straight-through processing rate | The share of receipts the agent finishes completely on its own, with no person needing to look at them. The company built the agent to stop paying staff to type receipts in by hand, so this is the main sign of whether that is working. If the agent finishes 90 of every 100 receipts, staff only handle 10. If it finishes 30, staff still handle 70, and the company pays for that manual work plus the cost of running the agent. | Receipts saved automatically (status `processed`) divided by all receipts received. Example: 100 receipts, 72 saved automatically, 28 sent to a person, gives 72%. If this drops suddenly, look up which of these fields changed in the `ProcessingRuns` table: `validatorRouting` (the validator agent chose review), `rung` (reduced mode switched the validator off or forced review), `cedarBlocked` (the policy blocked a save of 2,000 or more), or `status` (receipts were `deferred` or ended in `error`). Each cause is recorded, so the table tells you which one moved. |
| B2 | Dollar-weighted extraction error | How much money was recorded wrong, rather than how many receipts had a mistake. A mistake on a $12 coffee and a mistake on an $8,000 invoice are not equally bad, but a simple error count treats them the same. Measuring in dollars keeps attention on the mistakes that actually cost the company. | For each receipt, take the difference between the amount the agent recorded and the correct amount. Add those differences up and divide by the total of the correct amounts. Example: $10,000 of receipts with $150 recorded wrong gives 1.5%. Also count how many single receipts were off by more than a set amount, such as $50, since those need individual follow-up. |
| B3 | Control breach count | The number of times the agent broke a rule the company must never break. For this sample the rules are: never save an expense of $2,000 or more without a person approving it, never record the same expense twice, and never save a receipt whose subtotal, tax, and tip do not add up to the total. Auditors check these rules one by one and even a single break is a problem, so the goal is zero, not a good average. | Count the receipts that broke each rule, with one count per rule. Do not combine them into a single score, because each rule is owned by a different person and fixed in a different way. |
| B4 | Review-queue precision | Of the receipts the agent sent to a person, how many actually needed a person. If the agent sends receipts to review that were already correct, staff waste time approving work that was fine, and the savings from B1 disappear. It also exposes an agent that only looks safe because it sends everything to review. | Of the receipts sent to review, the share where the person actually corrected or rejected something. Example: 40 sent to review, 30 approved exactly as-is, 10 corrected, gives 25%, meaning three quarters of the reviews were unnecessary. This needs the reviewer's decision recorded back in the system, which the sample does not do today. |
| B5 | Completion rate | The share of uploaded receipts that ended in a known result: saved, waiting for review, queued to retry later, or failed with the error recorded. A receipt that silently disappears is worse than one recorded wrongly, because nobody notices until the employee complains they were never paid back. Accuracy checks cannot catch this, since there is nothing to check. | Receipts with a known result divided by receipts uploaded. The upload count must come from the upload location itself, not from the agent's own records. Otherwise a receipt the agent never saw is missing from both numbers and the rate looks perfect. |
| B6 | Cost per receipt | What it costs on average to process one receipt, including the AI model, the text-reading (OCR) service, and staff time for receipts sent to review. If this is higher than what it cost to have staff type receipts in by hand, the agent is not saving money, however accurate it is. | Add up model charges, OCR charges, and staff time spent on reviews, then divide by the number of receipts. Report two versions: the cost of a receipt the agent finished alone, and the cost of one that went to a person. When B1 drops, more receipts take the expensive path, so this rises even if nothing else changed. |
| B7 | Degraded-volume share | The share of receipts processed while the system was in a reduced mode. When the main AI model is too busy, the sample automatically switches to an older backup model and turns off some checks. That keeps receipts moving but can lower quality. The business needs to know how much of its expense data was produced this way, both to judge the other numbers fairly and because an auditor may ask. | Receipts processed in reduced mode divided by all receipts, shown for each level (the sample calls these rungs L1 to L4). Then compare B1 and B2 for reduced-mode receipts against normal ones, to see whether the reduced mode actually hurts results. |

B7 is specific to this sample. The other six would appear on any accounts-payable automation scorecard; this one exists because the sample's headline feature is a model degradation ladder.

## Bucket A: computable today, no new data

| Metric | Data source | Notes |
|---|---|---|
| B1 STP rate | `ProcessingRuns.status`, or the terminal tool span | Ready now |
| B3 threshold breach | `gen_ai.tool.call.arguments` on `save_expense`, or ledger `total` + `cedarBlocked` | Ready now |
| B3 process conformance | tool-call sequence in spans | Ready now, `Builtin.TrajectoryInOrderMatch` |
| B3 non-reconciling auto-post | `submit_expense` **returns** `{"reconciles": bool}`, so it is in `gen_ai.tool.call.result` | Ready in spans. Not in the ledger. One-line fix to `build_run_event` if you want it queryable. |
| B6 cost per receipt | `gen_ai.usage.input_tokens` / `output_tokens` across session spans | Ready now. Reviewer time needs an assumed constant until Bucket C lands. |
| B7 degraded share | ledger `rung`, span `receipts.ladder.rung` | Ready now |

## Bucket B: needs a labeled golden dataset

This is a data file, not an architecture change. The existing fixture is fully determined already (Blue Bottle Coffee, 2026-06-23, 12.75 + 1.15 + 2.00 = 15.90) and has no label beside it.

| Metric | What the labels unlock |
|---|---|
| B2 dollar-weighted error | compare `submit_expense` total against truth |
| B3 duplicate suppression | requires crafted near-duplicate pairs in the fixture set |
| B4 routing correctness (false clear vs false alarm) | you only know a review was unnecessary if you know the truth |
| confidence calibration | needs correctness to correlate against |

**A real bug to build a fixture around.** `expenseId = sha256(user|merchant|date|total)` and `save_expense` uses `put_item`. Two genuinely distinct purchases at the same merchant, same day, same amount, two identical coffees, collapse to one row and **one silently overwrites the other**. That is data loss presented as deduplication, and it is invisible to every metric you currently have. A two-receipt fixture makes it measurable.

## Bucket C: needs new code

| Metric | What is missing | Size |
|---|---|---|
| **B4 review precision, in production** | `human_review` writes `status: "needs_review"` and **nothing ever resolves it**. No reviewer signal returns. You need a `resolve_review` Gateway tool plus a `reviewOutcome` field (`approved_unchanged` / `corrected` / `rejected`). Without it B4 is offline-only forever. | one Lambda, one schema, one ledger field |
| B5 completion denominator | The ledger only has rows for receipts the Runtime was invoked for. A trigger failure leaves no row at all, so the denominator is wrong. Needs an S3 inventory reconcile or a trigger-side count. | small |
| B6 full unit cost | Reviewer minutes need B4's resolution data. Until then, use a constant and label it an assumption. | trivial once B4 exists |
| Cycle time | The EventBridge event `time` is available in the trigger but never propagated. Ledger has `processedAt` only. | small |
| Deferred-recovery rate | `receiptId = hash(s3_uri)` plus `put_item` means a drained replay **overwrites** the deferred row. The fact a receipt was ever deferred disappears. Needs a counter or an append. | small |

## What I would build, in order

1. **Golden dataset.** Unlocks all of Bucket B and costs no architecture. Include the duplicate pair, a non-reconciling receipt, one over the 2,000 threshold, and a foreign-currency one, since none of those exist today.
2. **`resolve_review` tool plus `reviewOutcome`.** This is the one addition that changes what is measurable rather than just what is computed. Without it, review-queue precision, the metric that stops "route everything to review" from scoring as success, cannot exist in production at all.
3. **Three ledger fields:** `reconciles`, `receivedAt`, `deferCount`. Each unblocks a metric and each is a few lines.

Everything in Bucket A can be written as evaluators against the sample exactly as it stands, so you can have working code to point at before touching any of the above.
