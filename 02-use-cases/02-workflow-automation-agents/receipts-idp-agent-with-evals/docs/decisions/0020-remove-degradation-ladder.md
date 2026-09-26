# ADR-0020: Remove the Degradation Ladder, Keep Live Model Settings

**Status:** Accepted
**Date:** 2026-09-25

## Context

This sample started from the receipts IDP sample, whose distinct contribution was a **model degradation ladder**: five rungs (L0 to L4) in AppConfig, each with its own model and feature flags; an in-agent step-down to the next rung's model on a Bedrock `503`; an alarm-driven controller that moved the active rung for every run; and at L4, an SQS defer queue with a jittered drain (formerly ADRs 0007, 0010 and 0011).

This sample's subject is evaluation, and the ladder works against it:

- **The pipeline was not one pipeline.** From L2 down the validator is shed and every receipt goes to review. `ReceiptsRoutingOutcome` would then score each clean receipt a false alarm, blaming a validator that never ran. That breaks the rule that an evaluator judges a decision a model made ([ADR-0017](0017-evaluators-from-business-outcomes.md)).
- **Deferred runs had nothing to score.** An L4 run stamps no total, so the live threshold monitor records an error for every deferred session.
- **Scores mixed configurations silently.** An L1 run uses another model, and nothing in the evaluators separated it from L0.

Making every evaluator rung-aware would keep the complexity and add to it.

## Decision

Remove the ladder from this sample: the rungs, the step-down loop, the step-down metric and alarm, the controller Lambda, the defer queue and drain Lambda, `forceReview`, validator shedding, and the fault-injection hook. The validator always runs.

Keep the part a team would keep anyway: **the model and its inference parameters are still read live from AppConfig** ([ADR-0008](0008-appconfig-over-hand-rolled-flags.md)), now by both Runtimes, so they can be changed without a redeploy.

## Reasoning

- **Every evaluated run is the same pipeline.** Extractor, validator, save or review, with no path where a model's decision is replaced by configuration.
- **What a live setting changes, the trace records.** A different model is still possible, but it is a deliberate change, and the model id is on each run's result and ledger row.
- **Resilience to Bedrock capacity events is a different subject.** It is demonstrated by the original receipts IDP sample, which keeps the ladder.

## Alternatives Considered

- **Keep the ladder and make the evaluators rung-aware** (routing "not applicable" from L2 down, deferred runs as "not engaged", scores reported per rung). Fewer changes, but every evaluator and every reader carries the ladder's cases.
- **Remove AppConfig as well** and set the model by environment variable. Simpler, but every model or parameter change becomes a Runtime redeploy.

## Consequences

- One fixed shape per receipt. A `503` that exhausts the SDK's retries now fails the run, which the run ledger records as `error` and the error rule alerts on; nothing is queued for replay.
- Fewer resources: no alarm, controller, defer queue or drain.
- Evaluation results from before this change were all produced at L0, the same pipeline as now, so they remain comparable.
