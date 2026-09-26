# Architecture

A receipt lands in S3; a dual-agent pipeline on AgentCore Runtime extracts a structured expense, an independent validator decides whether to auto-persist or route to human review, and the whole run is traced and evaluated in CloudWatch. A read-only chat assistant, on its own Runtime, answers an employee's questions about their own expenses. The model and its inference parameters are read live from AppConfig, so they change without a redeploy. This document is the map; the *why* behind each choice lives in [decisions/](decisions/).

![Receipts IDP architecture](diagrams/architecture.png)

![Event-driven front door](diagrams/front-door.png)

## The two planes

```mermaid
flowchart TB
    subgraph FD["Front door"]
        S3[("S3 inbox<br/>receipts/&lt;user&gt;/&lt;file&gt;")]
        EB["EventBridge rule<br/>(Object Created)"]
        TRIG["Trigger Lambda<br/>invoke_agent_runtime"]
        S3 -->|object created| EB --> TRIG
    end

    subgraph DP["Data plane — one receipt run (Runtime microVM)"]
        AGENT["Dual agent:<br/>0. read model settings (cached)<br/>1. OCR (Textract)<br/>2. EXTRACTOR → structured<br/>3. VALIDATOR → approve or review<br/>(pinned tools)"]
        GW["AgentCore Gateway<br/>(1 MCP endpoint)<br/>Cedar on every tool call"]
        DDB[("DynamoDB<br/>Users / Expenses")]
        BR["Bedrock<br/>(global inference profile)"]
        AGENT -->|tool calls MCP| GW -->|Lambda targets| DDB
        AGENT -->|model call| BR
    end

    AC["AWS AppConfig<br/>model id + inference parameters"]
    OBS["CloudWatch GenAI Observability<br/>+ Evaluations (aws/spans, online eval)"]

    TRIG -->|M2M, {s3_uri, user_id}| AGENT
    AC -.->|cached read at invoke start| AGENT
    AGENT -->|spans per step, outcome on the invocation span| OBS
```

**Front door** (event-driven, [ADR-0006](decisions/0006-s3-eventbridge-over-direct-invoke.md)) — upload → S3 → EventBridge → trigger Lambda → Runtime. No logged-in user; the agent authenticates as itself ([ADR-0004](decisions/0004-agent-as-principal-m2m-over-per-user-jwt.md)).

**Data plane** — one receipt = one Runtime session = a tree of spans. The agent reads its model settings from AppConfig (cached), OCRs the receipt with Textract, runs the extractor then the independent validator ([ADR-0002](decisions/0002-dual-agent-over-single-agent.md)), and persists or routes to review through the Gateway. It never touches DynamoDB directly — the Gateway is the one place auth, Cedar authorization, and observability are enforced ([ADR-0003](decisions/0003-gateway-lambda-targets-over-co-located-tools.md)).

## The pipeline, step by step

1. **Read the model settings.** `get_model_settings()` reads the model id and inference parameters from AppConfig via the `appconfigdata` data API ([ADR-0008](decisions/0008-appconfig-over-hand-rolled-flags.md), [ADR-0009](decisions/0009-appconfigdata-not-lambda-extension.md)), cached in-process. Falls back to `AGENT_MODEL_ID` if AppConfig is unreachable — the agent never hard-fails on its settings.
2. **OCR.** Textract `analyze_expense` reads the receipt straight from S3 (`S3Object`) and returns summary fields + line-item groups with per-field confidence.
3. **Table parse.** A deterministic Markdown-table parser turns the line-item block into structured rows; the agent only re-derives rows the parser couldn't (hybrid extraction).
4. **Extractor agent.** A Strands agent on the configured model produces a structured expense via a forced `submit_expense` tool call — machine-checkable, not free text.
5. **Validator agent.** An independent agent sees only the OCR + the extractor's output, decides, and acts by calling exactly one of two pinned tools: `approve_expense` or `send_to_review` ([ADR-0019](decisions/0019-validator-acts-through-pinned-tools.md)). The tools take its confidence and reasoning, never the expense fields, so it cannot change what is saved.
6. **Persist or review.** `approve_expense` calls `save_expense` (Cedar-gated) through the Gateway; a Cedar denial files a `human_review` instead. `send_to_review` writes the reviewer note and calls `human_review`. If the validator decides nothing, code files the review.
7. **Return + observe.** A structured result with `confidence`, `needs_review`, and the `model` the run used. The invocation span carries the outcome as `receipts.*` attributes (status, total, whether Cedar blocked it, both confidences, the extracted fields), and the save or review call has its own tool span. The evaluators read these; without them a correct save would look like a skipped step.

## Evaluation

Evaluators were chosen from the business outward and contrast-tested before being trusted ([ADR-0017](decisions/0017-evaluators-from-business-outcomes.md)).

- **Live, in AgentCore:**
  - `ReceiptsLive` scores every pipeline session with `ReceiptsThresholdControl`, a monitor on the Cedar control.
  - `ReceiptsAgent_ChatLive` scores every chat session with ConversationCompleteness and KnowledgeRetention.
  - Online configs select sessions by service name, which is why chat has its own Runtime ([ADR-0018](decisions/0018-separate-chat-runtime.md)).
- **On labelled data, in `evals/`:**
  - extraction accuracy and routing (code-based, deployed as the same Lambda)
  - ToolParameterAccuracy on the extractor's part of the trace
  - GoalSuccessRate with per-receipt assertions on the trace through the validator
  - Correctness per chat turn

  These run locally or against the deployed stack.

## Live model settings

The model id and its inference parameters (`temperature`, `maxTokens`, `topP`) live in one AppConfig profile, read by both Runtimes at the start of each run ([ADR-0008](decisions/0008-appconfig-over-hand-rolled-flags.md)). Deploying a new version changes them for every new run within about a minute, with no redeploy; see [CONFIGURATION.md](CONFIGURATION.md#live-model-settings-appconfig).

This sample originally carried a model degradation ladder (per-rung models and feature flags, a step-down on Bedrock `503`, an alarm-driven controller and an SQS defer queue). It was removed so that every evaluated run is the same pipeline ([ADR-0020](decisions/0020-remove-degradation-ladder.md)). Transient Bedrock errors are retried by the SDK; a run that still fails is recorded as `error` in the run ledger, which alerts through SNS.

## AgentCore services used

| Service | Role here |
|---------|-----------|
| **Runtime** | Two Runtimes from one codebase: the pipeline (the dual-agent orchestrator, code-based, not the managed Harness, because IDP needs a custom OCR step and forced structured output) and the chat assistant (multi-turn within a session). |
| **Gateway** | Turns the DynamoDB read/write Lambdas into governed MCP tools through one endpoint. The single enforcement point. |
| **Policy (Cedar)** | Gates `save_expense` on the tool input (amount ≥ $2,000 → review), deterministically, independent of the agents ([ADR-0012](decisions/0012-cedar-on-tool-input.md)). |
| **Observability** | OTel traces/logs/metrics → CloudWatch GenAI Observability; the outcome stamped on the invocation span. Auto-instrumented (the Runtime is CLI/CDK-deployed). |
| **Evaluations** | Three code-based evaluators (one Lambda), a live config per Runtime, and built-in and third-party judges run on labelled data. See [Evaluation](#evaluation). |
| **Memory** | Integrated in the agent for per-user facts in custom `receipts/...` namespaces. The stack does not create a Memory resource by default, and the agent degrades gracefully without one. |

## Component inventory

- **`app/receiptsagent/`** — the agent. `main.py` (dual-agent entrypoint), `config.py` (the single env-read seam), `model/settings.py` (the live model settings + the appconfigdata reader), `tools/` (OCR, structured output, the table parser), `gateway_auth.py` (M2M token), `memory/`, `mcp_client/`.
- **`lambdas/`** — the Gateway tools (`get_user_profile`, `get_recent_expenses`, `lookup_merchant`, `save_expense`, `human_review`) + the front-door `trigger` + the run-ledger writer, each with its schema under `lambdas/schemas/`.
- **`agentcore/agentcore.json`** — the AgentCore resources: two Runtimes, the Gateway and targets, the PolicyEngine and Cedar policies, the code-based evaluators, the `ReceiptsLive` online config.
- **`evaluators/business_outcomes/`** — the code-based evaluators, deployed as one Lambda.
- **`evals/`** — the evaluation harness, labelled receipts and conversations, and the deployed-stack runner.
- **`agentcore/cdk/`** — the supplementary infra (DynamoDB, S3, Cognito, SQS, AppConfig, alarms, EventBridge, the Lambdas) + the glue stack ([ADR-0001](decisions/0001-agentcore-cli-plus-cdk.md)).

See [CONFIGURATION.md](CONFIGURATION.md) for the knobs and [tutorial.md](tutorial.md) for a guided run.
