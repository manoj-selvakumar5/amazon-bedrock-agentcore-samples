# ADR-0008: AWS AppConfig for Live Model Settings

**Status:** Accepted (revised 2026-09-25, see [ADR-0020](0020-remove-degradation-ladder.md))
**Date:** 2026-06-24

## Context

The model an agent runs on, and its inference parameters, are settings a team changes more often than code: a newer model becomes available, a temperature needs tuning, a response is being cut short by `maxTokens`. Changing them should not need a redeploy of the Runtime, and a bad value should not take the agent down. Where do those settings live?

## Decision

Store them in **AWS AppConfig** as a freeform JSON profile:

```json
{"modelId": "global.anthropic.claude-opus-4-8", "temperature": 0.2, "maxTokens": 4096, "topP": 0.9}
```

Only `modelId` is required; a parameter left out keeps the model's default. Both Runtimes (pipeline and chat) read the profile at the start of each run, through a cached reader (`app/receiptsagent/model/settings.py`). Changing a setting is a new AppConfig configuration version and deployment, not a stack redeploy.

## Reasoning

AppConfig gives, out of the box, what a hand-rolled settings store (a DynamoDB item, an S3 object) would force us to reinvent:
- A **validation gate** before a config goes live (catch a malformed document or unknown model id at deploy, not at 3am).
- **Gradual deployment strategies** (bake time + rollout percentage).
- **Alarm-backed automatic rollback**: wire a CloudWatch alarm to the deployment, and a bad config self-reverts during the bake window.

The agent caches the settings in-process (TTL from the server), so reading them is a local lookup, not a per-receipt network call. If AppConfig is unreachable or the document is malformed, the reader falls back to `AGENT_MODEL_ID` with the model's defaults and never hard-fails.

## Alternatives Considered

- **A DynamoDB item or S3 object as a settings store:** workable, but we'd hand-roll validation, staged rollout, and rollback.
- **Environment variables only:** every change becomes a Runtime redeploy. `AGENT_MODEL_ID` is kept, but only as the local default and the fallback.

## Consequences

The Runtime reads the profile via the `appconfigdata` data API, not the Lambda extension ([ADR-0009](0009-appconfigdata-not-lambda-extension.md)). The sample uses an all-at-once, no-bake strategy for fast demos; a production deploy adds a bake window + the alarm rollback.

A settings change takes effect within one poll interval (about 60 seconds), for new runs only; a run in flight keeps the settings it started with. The model id is recorded on every run's result and ledger row, so an evaluation run can be tied to the model that produced it. When comparing evaluation results, hold the settings fixed across the run, or compare runs by model.

Originally this profile held the degradation ladder: an active rung plus per-rung models and feature flags. The ladder was removed from this sample; the profile now holds only the model settings ([ADR-0020](0020-remove-degradation-ladder.md)).
