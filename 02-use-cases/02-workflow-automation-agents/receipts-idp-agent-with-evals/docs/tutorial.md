# Tutorial

A guided run, then four experiments that exercise the parts that make this sample interesting: the event-driven front door, the Cedar guardrail, changing the model live, and adding a tool. Assumes you've deployed — see [deployment.md](deployment.md).

Prerequisites: the stack is deployed (`./deploy.sh us-west-2`), and the model's global inference profile (`global.anthropic.claude-opus-4-8` by default) is enabled in your account (`aws bedrock list-inference-profiles`).

## The guided run

**1. Confirm the agent responds.** Upload the sample receipt and invoke directly:

```bash
python3 scripts/upload_sample_receipt.py --region us-west-2      # prints the s3:// URI
python3 scripts/test_invoke.py --region us-west-2 \
    --s3-uri s3://receipts-inbox-<account>-us-west-2/receipts/sample-receipt.png \
    --user-id user-001
```

The response is a structured result: `{status, needs_review, model, extractor_confidence, validator, expense, ...}`. `status` is `processed` or `needs_review`, and `model` is the model the run used.

**2. See it in DynamoDB.** The expense row landed under the user:

```bash
aws dynamodb query --table-name ReceiptsAgent-Expenses \
    --key-condition-expression "userId = :u" \
    --expression-attribute-values '{":u":{"S":"user-001"}}' \
    --region us-west-2
```

**3. See the trace.** CloudWatch → GenAI Observability → your runtime. Each run is one session; the invocation span carries the outcome as `receipts.*` attributes (status, total, whether Cedar blocked it, both confidences), which the evaluators read.

## Experiment 1 — the event-driven front door

No direct invoke. Just drop a file and watch the pipeline run itself ([ADR-0006](decisions/0006-s3-eventbridge-over-direct-invoke.md)):

```bash
aws s3 cp tests/fixtures/sample-receipt.png \
    s3://receipts-inbox-<account>-us-west-2/receipts/alice/lunch.png --region us-west-2
```

The key `receipts/alice/lunch.png` makes the trigger derive `user_id=alice`. After ~90s, query the Expenses table for `userId = alice` — the row is there, written by a run nobody invoked by hand. S3 → EventBridge → trigger Lambda → Runtime.

## Experiment 2 — the Cedar guardrail

`save_expense` is gated at the Gateway: an expense ≥ $2,000 cannot auto-persist, it routes to review — deterministically, independent of the agents ([ADR-0012](decisions/0012-cedar-on-tool-input.md)). The `tests/test_e2e_cedar_live.py` test drives this directly through the Gateway with the agent's M2M token: a small total is allowed, a $2,000+ total is denied and the agent falls back to `human_review`. Run it against the live stack:

```bash
AWS_REGION=us-west-2 python3 -m pytest tests/test_e2e_cedar_live.py -v
```

## Experiment 3 — change the model live (no redeploy)

The model and its inference parameters live in AppConfig, and both Runtimes read them at the start of each run ([ADR-0008](decisions/0008-appconfig-over-hand-rolled-flags.md)). Deploy a new version of the settings, for example a lower `temperature` or another model id, with the commands in [CONFIGURATION.md](CONFIGURATION.md#live-model-settings-appconfig). Within about a minute, re-run step 1 of the guided run: the result's `model` shows the new model, and the stack was never redeployed.

Keep the settings fixed while running the labelled evaluations, so every scored run used the same model.

## Experiment 4 — add a new tool

Two config surfaces stay in sync ([ADR-0001](decisions/0001-agentcore-cli-plus-cdk.md), [ADR-0003](decisions/0003-gateway-lambda-targets-over-co-located-tools.md)):

1. **The Lambda:** `lambdas/<new_tool>/handler.py` + `lambdas/schemas/<new_tool>.json` (keep the schema in sync with the handler's parameters, or the agent won't see a field).
2. **`agentcore.json`:** add a Gateway target with a `PLACEHOLDER_<NEW_TOOL>` ARN + the schema file.
3. **`cdk-stack.ts` / `infra-construct.ts`:** create the Lambda (with least-privilege grants) and patch its real ARN into the `lambdaArnMap` so the placeholder is replaced at synth.
4. **The agent:** reference the tool by name from the Gateway tool list in `main.py`.

`make synth` validates the wiring before you deploy.

## Evaluations

Three evaluators score production traffic continuously, one online config per Runtime:
- `ReceiptsThresholdControl` watches every pipeline session. It is a monitor on the Cedar control: did anything at or above $2,000 save automatically?
- ConversationCompleteness and KnowledgeRetention score every chat session.

Results land in CloudWatch under `/aws/bedrock-agentcore/evaluations/results/`, a few minutes after a session goes idle.

The evaluators that need a right answer run against the labelled receipts and conversations in `evals/`:

```bash
cd evals
.venv/bin/python run_deployed.py                                # through the deployed stack
.venv/bin/python score_saved.py --run out/deployed-<id>
.venv/bin/python score_chat.py  --run out/deployed-chat-<id>
```

Why these evaluators, and what their contrast tests found: [ADR-0017](decisions/0017-evaluators-from-business-outcomes.md).
