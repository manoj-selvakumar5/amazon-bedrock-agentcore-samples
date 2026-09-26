# Configuration

Everything the agent reads comes through one seam — `app/receiptsagent/config.py`. The agent depends only on environment variables and AppConfig, never on CLI/CDK specifics, so the deploy mechanism stays replaceable ([ADR-0001](decisions/0001-agentcore-cli-plus-cdk.md)). This document covers the env vars, the live model settings in AppConfig, the Cedar policy, and the tuning knobs.

## Environment variables (the seam)

All set by the CDK stack at deploy time; `.env.example` mirrors them for running the agent locally.

| Variable | Purpose | Set by |
|----------|---------|--------|
| `AGENT_MODEL_ID` | The default model: the local-dev model and the fallback when AppConfig is unreachable. **Not** the live model in a deployed stack; that comes from the AppConfig model settings. | `agentcore.json` envVars |
| `APPCONFIG_APPLICATION` / `_ENVIRONMENT` / `_PROFILE` | AppConfig coordinates for the live model settings, on both Runtimes. Unset (local dev) ⇒ run on `AGENT_MODEL_ID` with the model's default inference parameters. | CDK (parent stack) |
| `AGENTCORE_GATEWAY_URL` | The MCP Gateway endpoint. | CDK (from the Gateway resource) |
| `AGENTCORE_GATEWAY_TOKEN_ENDPOINT` / `_CLIENT_ID` / `_CLIENT_SECRET` / `_OAUTH_SCOPES` | Cognito M2M `client_credentials` for agent-as-principal auth ([ADR-0004](decisions/0004-agent-as-principal-m2m-over-per-user-jwt.md), [ADR-0014](decisions/0014-cognito-secret-via-cdk-injection.md)). | CDK (from Cognito) |
| `MEMORY_ID` | AgentCore Memory id. Optional — the agent runs without it. | CDK |
| `RUN_EVENT_BUS` | The run-ledger EventBridge bus ([ADR-0015](decisions/0015-processing-runs-ledger.md)). Unset (local dev) ⇒ no ledger emit, agent runs normally. | CDK |
| `IDENTITY_KEY_ID` | KMS HMAC key for conversational-query identity ([ADR-0016](decisions/0016-conversational-identity-no-idor.md)). The agent verifies the signed token to derive `user_id` (never from the request body). | CDK |

Lambda-side env (not the agent seam): the trigger reads `AGENTCORE_RUNTIME_ARN` + `DEFAULT_USER_ID`; the ledger writer reads `RUNS_TABLE`.

## Live model settings (AppConfig)

The model and its inference parameters live in a freeform JSON profile in AppConfig (application `ReceiptsAgent-ModelSettings`, profile `model-settings`), deployed by the CDK and editable at runtime with no stack redeploy ([ADR-0008](decisions/0008-appconfig-over-hand-rolled-flags.md)). Shape:

```json
{
  "modelId": "global.anthropic.claude-opus-4-8",
  "temperature": 0.2,
  "maxTokens": 4096,
  "topP": 0.9
}
```

- **`modelId`** (required): a `global.` inference profile id. Read the exact ids from `aws bedrock list-inference-profiles` in your account; the suffix convention is **not** uniform (`opus-4-6` is `...-opus-4-6-v1`). The Runtime role can invoke any Anthropic inference profile.
- **`temperature`, `maxTokens`, `topP`** (optional): passed to every model call (extractor, validator, reviewer note and chat). A key left out keeps the model's default; a malformed value is ignored. The sample deploys `modelId` only.

Both Runtimes read the profile at the start of each run and cache it for the poll interval AppConfig returns (about 60 seconds), so a change reaches new runs within a minute; a run in flight keeps the settings it started with. If AppConfig is unreachable or the document is malformed, the agent runs on `AGENT_MODEL_ID` with the model's defaults. The model each run used is returned in its result and recorded on its `ProcessingRuns` row.

To change a setting: create a new hosted configuration version and deploy it.

```bash
APP=$(aws appconfig list-applications --query "Items[?Name=='ReceiptsAgent-ModelSettings'].Id" --output text)
ENV=$(aws appconfig list-environments --application-id "$APP" --query "Items[?Name=='dev'].Id" --output text)
PROFILE=$(aws appconfig list-configuration-profiles --application-id "$APP" --query "Items[?Name=='model-settings'].Id" --output text)
STRATEGY=$(aws appconfig list-deployment-strategies --query "Items[?Name=='ReceiptsAgent-AllAtOnce'].Id" --output text)

echo '{"modelId": "global.anthropic.claude-opus-4-8", "temperature": 0.2}' > settings.json
VERSION=$(aws appconfig create-hosted-configuration-version --application-id "$APP" \
  --configuration-profile-id "$PROFILE" --content-type application/json \
  --content fileb://settings.json /dev/null --query VersionNumber --output text)
aws appconfig start-deployment --application-id "$APP" --environment-id "$ENV" \
  --configuration-profile-id "$PROFILE" --deployment-strategy-id "$STRATEGY" \
  --configuration-version "$VERSION"
```

When comparing evaluation results, keep the settings fixed for the whole run, or group results by the recorded model.

## Cedar policy

Two policies on the Gateway's policy engine (`agentcore.json` → `policyEngines`), both `IGNORE_ALL_FINDINGS` ([ADR-0013](decisions/0013-ignore-all-findings-policy-validation.md)):

- **`AllowAllTools`** — `permit(principal, action, resource is AgentCore::Gateway)`. Allow-all baseline.
- **`BlockExcessiveExpense`** — forbids a `save_expense` of $2,000 or more, routing it to review instead ([ADR-0012](decisions/0012-cedar-on-tool-input.md)). It compares `total_cents`, an integer the orchestrator sends with every save, and denies a save without it. Cedar will not compare a decimal with a whole number, and the Gateway passes totals such as `15.9` or `1250.0` as decimals. To change the threshold, edit the `>= 200000` (cents) in the policy statement. To add a category block, add another `forbid` keyed on `context.input.category` (guard `context has input` first).

## Tuning knobs

Sample defaults; tune them for your account.

| Knob | Where | Default | Notes |
|------|-------|---------|-------|
| AppConfig deployment strategy | `infra-construct.ts` → `ModelSettingsStrategy` | all-at-once, no bake | A production deploy adds a bake window + an alarm rollback. |
| Cedar threshold | `agentcore.json` → `BlockExcessiveExpense` | `200000` cents | The auto-persist ceiling ($2,000). |
