# Receipts IDP Evaluation Revamp: Experiment and Implementation Plan

**Date:** 2026-09-16

Here's the order I'd follow. Each step answers one question and leaves you with something that works, and deploying comes last, because deploying starts with rebuilding the missing CDK code.

## Ground rules

- **Extraction path only** until it works end to end. Leave chat for later.
- **One receipt before a dataset.**
- **Record the trace once, then test evaluators against the saved file.** That way you don't re-run the agent or pay for Bedrock on every attempt.
- **One evaluator of each kind before many:** one built-in, one third-party, one code-based.

## Stage 0: see what the trace contains
**Build**
- A small local stand-in for the Gateway: a FastMCP server with `save_expense` and `human_review`, an in-memory store instead of DynamoDB, and a rule that rejects any save of 2,000 or more with "denied by policy".
- A harness script that captures spans in memory, wraps `_process()` in a parent span with a `session.id`, and runs the Blue Bottle fixture from an S3 bucket you own.

**Done when:** `spans.json` is on disk.

**Answers:** you see with your own eyes that the extraction is recorded and the save isn't. You also get a recorded trace that every later stage reuses.

## Stage 1: make the outcome visible
**Build:** the two `main.py` changes. Stamp the outcome attributes on the span, and emit tool-call spans around the save and review calls.

**Done when:** re-running the harness shows `receipts.status` and an `execute_tool save_expense` span.

**Answers:** whether the core code change works. It touches no prompts or tools.

## Stage 2: first scores, still nothing deployed
**Build:** convert the spans with `convert_strands_to_adot()` and call `Evaluate` with three evaluators:
- `Builtin.TrajectoryInOrderMatch`, with `save_expense` in the expected trajectory
- `Builtin.GoalSuccessRate`, with one assertion
- `ThirdParty.DeepEval.ToolUse`

**Done when:** three scores print.

**Answers:** the biggest open question, whether the service treats your manual spans as tool calls. If it doesn't, the plan still works, with code-based evaluators carrying more of the load. This stage also shows third-party evaluators working on this sample.

## Stage 3: one business metric end to end
**Build:**
- One code-based evaluator for STP outcome plus the 2,000 rule (B1 and B3). Test it locally via `handler.unwrapped` against `spans.json`, with no Lambda yet.
- A small golden dataset: the clean receipt, one whose numbers don't add up, one at 2,000 or more, and a near-duplicate pair. The existing fixture is a rendered image, so these can be generated the same way.
- A run through `OnDemandEvaluationDatasetRunner` with an in-memory span collector and an invoker that calls the local agent.

**Done when:** you have one results table showing each evaluator's score for each receipt.

**Answers:** whether Framework 1 metrics can be measured with this code. That's what the blog needs.

## Stage 4: deploy
**Build:**
- Recover or rebuild `agentcore/cdk/lib/`, plus the `.gitignore` exception.
- Deploy the stack and pause the old three-judge online config.
- Deploy and register the code-based evaluator Lambda.

**Then:** online evaluation, batch evaluation, and Insights on real traffic.

## Stage 5, optional: chat path
Session reuse and history, a named endpoint, the multi-turn third-party evaluators, and Simulation.

## Practical notes

- **Where it lives:** a new `evals/` folder in the sample on the `receipts-idp-eval-revamp` branch, holding the local gateway, the harness, the evaluators, and the dataset. Agent changes stay limited to Stage 1.
- **What you need up front:** AWS credentials with Bedrock and Textract access, and one S3 bucket.
- **Cost:** `AGENT_MODEL_ID` sets the model for local runs. A cheaper model keeps costs down while you're checking wiring, and you can switch back when you want realistic extraction quality.
