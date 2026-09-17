# Receipts IDP Evaluation

Evaluation work for the [receipts-intelligent-document-processing-agent](../receipts-intelligent-document-processing-agent) sample, built in stages. Only Stage 0 exists so far.

## Stage 0: capture one receipt's trace

Runs the real receipts pipeline (Amazon Textract OCR, then the extractor agent, then the validator agent) on one receipt, on your machine, and saves every OpenTelemetry span. Nothing is deployed.

| File | What it does |
|---|---|
| `capture_trace.py` | Runs the receipts sample's `_process()` in this process, captures spans in memory, and writes them to `out/<session id>/`. |
| `local_gateway.py` | Local stand-in for the AgentCore Gateway: `save_expense` and `human_review` over MCP, an in-memory store, and the 2,000 policy block. |

### Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- AWS credentials with access to Amazon Bedrock (default model `global.anthropic.claude-opus-4-8`) and Amazon Textract
- An S3 bucket in the Region you run in. Textract reads the receipt from S3 in that Region.

### Run

```bash
cd 02-use-cases/02-workflow-automation-agents/receipts-idp-evaluation
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt

aws s3 cp ../receipts-intelligent-document-processing-agent/tests/fixtures/sample-receipt.png \
  s3://<your-bucket>/receipts/sample-receipt.png

python capture_trace.py --s3-uri s3://<your-bucket>/receipts/sample-receipt.png --region us-west-2
```

Add `--model <inference profile id>` to use a cheaper model while you check the wiring.

### Output

| File | Contents |
|---|---|
| `spans.json` | Raw OpenTelemetry spans, for reading |
| `adot.json` | The same spans in ADOT format, for the `Evaluate` API in Stage 2 |
| `result.json` | What the pipeline returned |
| `writes.json` | What the local gateway recorded |

### What to look for

- **`save_expense in trace: no`.** The save happens after both agents finish, through the MCP client, which creates no span. Stage 1 fixes this.
- **Two `invoke_agent Strands Agents` spans.** Neither agent sets `name=`, so extractor and validator spans look alike.

### Cost per run

One Textract AnalyzeExpense page, plus a few Amazon Bedrock model calls: each agent typically calls the model before and after its tool call.
