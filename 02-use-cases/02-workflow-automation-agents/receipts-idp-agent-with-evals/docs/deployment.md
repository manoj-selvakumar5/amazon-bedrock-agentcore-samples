# Deployment

One command deploys everything as a single CloudFormation stack ([ADR-0001](decisions/0001-agentcore-cli-plus-cdk.md)):
- the AgentCore resources: two Runtimes, the Gateway, the Cedar policy engine, the evaluators and a live evaluation config
- the supplementary AWS infrastructure: DynamoDB, S3, Cognito, SQS, AppConfig, alarms, EventBridge, KMS and the Lambdas

## Prerequisites

- The AWS CLI with credentials for a dev account. The sample provisions real resources.
- Node.js 20 or later, and `uv`.
- **No local container engine.** The Runtimes are `Container` builds ([ADR-0005](decisions/0005-container-build-over-codezip.md)), but the images are built in AWS CodeBuild from the uploaded source. The evaluator Lambda is packaged with `uv`, cross-compiled for ARM64.
- The **four ladder global inference profiles** available in the account. `aws bedrock list-inference-profiles` should list `global.anthropic.claude-opus-4-8`, `...-opus-4-7`, `...-opus-4-6-v1` and `...-sonnet-4-6`. Copy the ids verbatim, because the suffix convention is not uniform.

## Deploy

```bash
./deploy.sh us-west-2
```

This runs, in order:
1. Writes the deployment target.
2. Builds the CDK app.
3. Bootstraps CDK, which is a no-op after the first time.
4. Deploys `AgentCore-ReceiptsAgent-dev` with the project's own CDK CLI. Synthesis validates `agentcore.json` against the AgentCore schema.
5. Applies the chat live-evaluation config with `scripts/chat_online_eval.py`. It uses managed third-party evaluators, which the CloudFormation schema does not accept yet.
6. Seeds a sample user.

The slowest stage is the two Runtime image builds in CodeBuild.

The stack also enables CloudWatch **Transaction Search** (account- and Region-level, left enabled on delete). Online evaluation reads spans from the `aws/spans` log group it creates. It takes about 10 minutes to become active the first time.

Confirm:

```bash
uv run --with boto3 python scripts/test_invoke.py --region us-west-2 \
    --s3-uri s3://receipts-inbox-<account>-us-west-2/receipts/sample-receipt.png
```

## Tear down

```bash
./destroy.sh us-west-2
```

It deletes the chat live-evaluation config first, then runs `aws cloudformation delete-stack` with DELETE_FAILED recovery, and leaves nothing billable.

### Teardown and DELETE_FAILED recovery

The AgentCore control-plane resources (Runtime, Gateway, GatewayTarget, PolicyEngine, Evaluator) occasionally fail to delete on the first pass, because of control-plane resource ordering, leaving the stack in `DELETE_FAILED`. `destroy.sh` handles this:

1. **Retry once.** Most ordering orphans are transient, and a second `delete-stack` clears them.
2. **Retain the stuck ones.** If specific resources are still stuck, it re-issues the delete with `--retain-resources <LogicalId ...>`. CloudFormation then deletes everything else, so nothing billable is left running.
3. **Report for manual cleanup.** It prints each retained resource as `ResourceType -> PhysicalResourceId`.

Delete a retained resource with the matching control-plane call, for example:

```bash
aws bedrock-agentcore-control delete-gateway        --gateway-identifier <id>       --region us-west-2
aws bedrock-agentcore-control delete-gateway-target --gateway-identifier <gw> --target-id <id> --region us-west-2
aws bedrock-agentcore-control delete-agent-runtime  --agent-runtime-id <id>         --region us-west-2
```

If teardown still cannot complete, inspect the failure reasons:

```bash
aws cloudformation describe-stack-events --stack-name AgentCore-ReceiptsAgent-dev --region us-west-2 \
  --query "StackEvents[?ResourceStatus=='DELETE_FAILED'].[LogicalResourceId,ResourceStatusReason]" --output table
```

## Local inner loop

The evaluation harness runs the real agent code on your machine against a stand-in Gateway, with no deploy:

```bash
cd evals && uv venv --python 3.12 && uv pip install -r ../app/receiptsagent/requirements.txt "bedrock-agentcore>=1.22" pillow
.venv/bin/python run_chat.py                          # the chat assistant, scripted conversations
.venv/bin/python run_dataset.py --bucket <bucket>     # the pipeline on the labelled receipts
```

With AppConfig and the Gateway env unset, the agent runs on the L0 default model with all features on. The ladder is a deployed-stack concern.

## Automated end-to-end

`make e2e` (or `scripts/e2e.sh`) is a one-shot **real** deploy, then assertions against the live stack, then destroy, exiting with the test result. `make unit` runs the tests that need no AWS. `make synth` builds and synthesizes the CDK app without creating resources.

## What gets created

The stack `AgentCore-ReceiptsAgent-dev` contains:
- **AgentCore:**
  - two Runtimes (pipeline and chat), with their CodeBuild image builders and ECR repositories
  - the Gateway with 5 Lambda targets
  - the PolicyEngine with 2 Cedar policies
  - three code-based evaluators (one Lambda each)
  - the `ReceiptsLive` online evaluation config, plus the execution role for the chat config
- **DynamoDB:** `ReceiptsAgent-Users`, `-Expenses`, `-Merchants` and `-ProcessingRuns`.
- **Storage and identity:**
  - an S3 inbox bucket, `receipts-inbox-<account>-<region>`, with EventBridge enabled
  - a Cognito M2M pool with a domain
  - a KMS HMAC identity key
- **Queues and events:**
  - SQS: `-L4Defer` and the trigger DLQ
  - EventBridge: a run-ledger event bus and rules, and the `ModelStepDowns` alarm
  - an SNS error topic
- **The ladder:** AppConfig (application, environment, profile, strategy) holding the ladder config.
- **Lambdas:** trigger, controller, drain, ledger writer and the five tools.

Everything is on-demand or serverless, and `destroy.sh` removes it.
