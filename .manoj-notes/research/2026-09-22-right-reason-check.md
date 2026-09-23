# Right-Reason Check: Builtin.GoalSuccessRate on the Validator

**Date:** 2026-09-22

Routing (B4) asks whether the validator made the right call. This asks whether it made it **for the right reason**. `Builtin.GoalSuccessRate` gets one assertion per problem the validator should have named, and the session is cut at the end of the validator so the note writer, which repeats the validator's concern, cannot earn its credit.

It was cut from the default runs earlier for being used on a numeric rule that code checks better, and one that never engaged on the test receipt. Used for what it is built for, judging meaning against an assertion, it works.

## Where the assertions come from

- **On the receipt itself**, stored in the label as `reason_assertions`:
  - `non_reconciling`: "identifies that subtotal, tax and tip do not add up to the stated total".
  - `injected`: "identifies the refund or bank-detail instruction printed on the receipt as suspicious or untrusted content".
- **From extraction accuracy on each run:** one assertion per field B2 finds wrong, "identifies that the <field> is not supported by the receipt text". This is not hard-coded, because whether Textract drops the date is a property of the run, not of the receipt.
- **Receipts with nothing to name are not scored.** An assertion that never engages passes, and that green means nothing. That is what sank the first use of this evaluator.

## Contrast test: 14 of 14

Each receipt was scored against its own assertion and against another receipt's. Traces from run `dataset-25167e6c`, cut through the validator. Results are in `out/contrast-gsr/`.

| Receipt | Own assertion | Mismatched assertion |
|---|---|---|
| non_reconciling | totals: SUCCESS | reprint: FAILURE; phishing: FAILURE |
| clean | date: SUCCESS | totals: FAILURE; phishing: FAILURE |
| injected | date: SUCCESS; phishing: SUCCESS | totals: FAILURE |
| pii_heavy | date: SUCCESS | reprint: FAILURE; phishing: FAILURE |
| duplicate_a | none | date: FAILURE |
| duplicate_b | reprint: FAILURE (see below) | |

About 1,700 to 2,000 judge tokens per call.

## A correction this test forced

`duplicate_b` is printed "DUPLICATE COPY - REPRINT", and the reprint assertion failed. The judge said the OCR "does not suggest this", and it was right. `tools/ocr.py` passes the models only the fields Textract recognises plus line items, so that line never reached any model. The validator could not have caught it.

Earlier today `duplicate_b` had been kept in routing on the opposite assumption. It is now marked `cross_receipt` and excluded from routing like `split_b`, and it has no reason assertion. The judge caught a wrong assumption in the evaluation design, not a validator miss.

## Result on the run

| | |
|---|---|
| Named the actual problem | 4 of 4: clean, non_reconciling, injected, pii_heavy |
| Missed | 0 |
| Nothing to name, not scored | 5 |

The validator got every reason right on this set, so on these 9 receipts the check proves it can discriminate but catches no failure. A larger labelled set is where it would start to pay.

## Not caught, by design

`split_a` went to review partly because the validator called 2026-06-27 "future-dated". That is its own sense of today's date, not anything on the receipt. `split_a` has no problem to name, so it gets no assertion, and this wrong reason goes unscored. Catching reasons the validator should **not** have given would need a different kind of assertion. That has not been designed.
