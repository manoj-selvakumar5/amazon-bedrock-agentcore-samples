# The Deployed Sample and Its Evaluators

**Date:** 2026-09-23

The receipts agent and its evaluation suite are now one standalone, deployable sample, `02-use-cases/02-workflow-automation-agents/receipts-idp-agent-with-evals/`. It is deployed to us-west-2 and left running. It is meant to replace `receipts-intelligent-document-processing-agent` in the eventual pull request.

## What was built

- **The agent**, with its trace telemetry, multi-turn chat and ledger fix.
- **A rebuilt CDK stack.** The original sample's stack source had never been committed, because the repository's root `.gitignore` ignores every `lib/`. It was rebuilt from the sample's documentation and the sibling samples' pattern, and a folder-level `.gitignore` exception keeps it in the repository. The root file is unchanged.
- **Two Runtimes from one codebase:** the pipeline and chat. Online evaluation selects sessions by service name, so each config scores only its own workload.
- **Evaluators in AgentCore:**
  - three code-based evaluators, each its own Lambda with its own entry point
  - `ReceiptsLive` (the threshold control monitor) in `agentcore.json`
  - `ReceiptsAgent_ChatLive` (DeepEval ConversationCompleteness and KnowledgeRetention), created through the API by `scripts/chat_online_eval.py`
  - The old blended judge and the copied `Helpfulness`/`Correctness`/`ToolSelectionAccuracy` online set are gone.
- **`evals/run_deployed.py`:** sends the labelled receipts through the real S3 front door and the conversations through the chat Runtime. It collects each session's trace from CloudWatch and writes the same output shape as the local runners, so the same scorers apply.
- **Docs:** README, deployment, architecture, tutorial, AGENTS.md, `evals/README.md`, ADR-0017 (evaluators) and ADR-0018 (chat Runtime), and dated updates to ADR-0001 and ADR-0005.

## Problems found while deploying, and fixed

| Problem | Cause | Fix |
|---|---|---|
| `cdk deploy` did nothing and reported success | The project's `package.json` names its own app `cdk`, so `npx cdk` ran the app, not the CDK CLI | `deploy.sh` calls `node_modules/aws-cdk/bin/cdk` |
| CloudFormation rejected the chat online config | Its resource schema accepts only `Builtin.*` or custom evaluator ids; the API also accepts `ThirdParty.*` | The stack creates the config's execution role; a script creates the config after deploy, and `destroy.sh` removes it first |
| **The deployed agent exported no traces at all** | The container started with `python main.py`, not `opentelemetry-instrument python main.py` (both sibling samples use the wrapper). This is in the original upstream sample | Dockerfile `CMD` fixed. Without it, observability and every evaluator are blind to the deployed agent |
| Deployed traces were incomplete when scored | The SDK span collector returns as soon as any spans exist, while spans arrive over minutes | `run_deployed.py` re-collects until the count holds and, for chat, there is one trace per turn |
| The live threshold monitor returned `UNKNOWN_EVALUATOR` | The handler routed on the evaluator name. The online path passes neither the name nor the id in the Lambda event (on-demand passes the name) | Each deployed evaluator has its own entry point; name routing stays only for local and on-demand use |
| The first commit of the new folder lacked its Dockerfile and `.env.example` | The root `.gitignore` ignores every `Dockerfile` and `.env.*`. The original sample's copies are force-tracked, but `git add` of a new folder skips ignored files, so a clone of the new folder could not build | Two more lines in the folder-level `.gitignore` exception; the new folder now tracks every file the original tracks |
| Scripts could pick the wrong Runtime | With two Runtimes, a substring match on `RuntimeArn` is ambiguous | Chat callers use the `ChatRuntimeArn` output |

No local container engine was needed: CodeBuild builds the Runtime images, and the evaluator Lambda is packaged with `uv`.

## Verification

- **Unit tests:** 68 of 68 pass, including new tests for chat history and both evaluator call paths.
- **Live user-facing tests:** 18 of 20 pass (pipeline, S3 front door, chat identity and IDOR, run ledger, tools, Cedar). The 2 failures are the Cedar finding below.
- **Live resilience tests:** 4 passed, 1 skipped by design (ladder flip, alarm-to-controller loop with cooldown, L4 drain; the live 503 test was already marked unsimulatable).
- **Live evaluation in AgentCore:** `ChatLive` wrote ConversationCompleteness and KnowledgeRetention scores. `ReceiptsLive` scored a $2,400 receipt `held`, "blocked by the policy".

## The deployed evaluation run

The 9 labelled receipts went through the front door, and the 5 conversations through the chat Runtime.

**Receipts:**
- **Extraction accuracy:** the same 3 invented dates as locally (clean, injected, pii_heavy); dollar error 0.00%.
- **ToolParameterAccuracy:** 3 of 3 invented values caught, plus the same false alarm on the honest low confidence.
- **Right reason:** 4 of 4.
- **Routing precision:** 71% (5 of 7).
- **Every receipt ended in review.** See the finding below.

**Chat:**
- **Correctness:** 10 of 12 turns right. Both misses are "most recent" answers: `single_question` again, and this time `merchant_followups` turn 3, which named Starbucks.
- **ConversationCompleteness:** 1.0 on both misses' conversations except one (0.67 on `merchant_followups`), and 0.5 on the correct refusal.
- **KnowledgeRetention:** 1.0 everywhere.

## The main new finding: the Cedar policy blocked every save (now fixed)

The Cedar policy compares `context.input.total >= 2000`. The agent sends every total as a decimal (15.9, 13.49, even 1250.0 and 2400.0), and the deployed engine errors on a decimal: "type error: expected long, got decimal". A forbid policy that errors denies. So **every automatic save is blocked**, whatever the amount:
- `duplicate_a` ($13.49) and `split_a` ($1,250.0) were approved by the validator (`AUTO_PERSIST`) and still sent to review.
- The live boundary tests confirm it: $15.90 and $1,999.99 are denied; only whole-number totals sent as integers behave.

Consequences:
1. **In production, nothing auto-saves.** The straight-through rate is zero by construction.
2. **The $2,000 control holds for the wrong reason.** `over_threshold` was blocked by the type error, not the rule. The monitor reports `held, blocked by the policy`, which is true but cannot show that the rule never ran.
3. **Routing blames the validator for Cedar's block.** `duplicate_a` and `split_a` count as false alarms. As a business number the queue precision is still right (those escalations were unneeded), but the cause is Cedar, not validator caution. The local stand-in compares plain numbers, so no local run could show any of this.

**Fixed the same day, at the user's request.** The orchestrator now sends `total_cents` (an integer) with every save. The policy compares `total_cents >= 200000` and denies a save without it (fail closed). A decimal-only comparison would not work, because the Gateway passes `2000` as a whole number and `2000.0` as a decimal.

Verified live:
- **All 10 Cedar tests pass:** $15.90, $1,250.0 and $1,999.99 allowed; $2,000, $2,000.50 and $2,400 denied; a save without cents denied.
- **The other user-facing live tests pass:** 12 of 12.
- **Labelled receipts through the front door:**
  - `duplicate_a` and `duplicate_b` ($13.49, validator `AUTO_PERSIST`) now **save**, which also brings back the duplicate overwrite, still kept as evidence.
  - `over_threshold` ($2,400, validator `AUTO_PERSIST`) is blocked by the actual `>= $2,000` rule.
  - Every other review is the validator's own decision.
  - Each hold now has one clear owner.

## Still open

- Distinguishing a Cedar block from a validator decision in the routing evaluator's explanation (`receipts.cedar_blocked` is already on the span).
- The old two folders stay on the branch until the pull request.
