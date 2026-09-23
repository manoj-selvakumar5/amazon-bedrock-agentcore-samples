#!/bin/bash
set -euo pipefail

# ============================================================================
# Receipts IDP Agent with Evaluators: one-command deploy
# Usage: ./deploy.sh [region]
#
# Deploys one CloudFormation stack (AgentCore-ReceiptsAgent-dev):
#   - Supplementary infra: DynamoDB, S3 inbox, tool and pipeline Lambdas, SQS,
#     EventBridge, the AppConfig degradation ladder and its controller, Cognito,
#     the identity KMS key (agentcore/cdk/lib/infra-construct.ts)
#   - Two AgentCore Runtimes (pipeline and chat), the Gateway with its Cedar policy
#     engine, three code-based evaluators and two online evaluation configs
#     (agentcore/agentcore.json, rendered by agentcore/cdk/lib/cdk-stack.ts)
#
# No local container engine is needed: the Runtime images are built in AWS
# CodeBuild from the uploaded source, and the evaluator Lambda is packaged with uv.
#
# Requirements: AWS CLI with credentials, Node.js 20+, uv.
# ============================================================================

REGION="${1:-us-west-2}"
export AWS_REGION="$REGION"
export AWS_DEFAULT_REGION="$REGION"
export CDK_DEFAULT_REGION="$REGION"

for tool in aws node npm uv; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing required tool: $tool" >&2; exit 1; }
done

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_ACCOUNT="$ACCOUNT_ID"
echo "Deploying Receipts Agent to $ACCOUNT_ID / $REGION"

# Step 1: the deployment target the CDK app reads
cat > agentcore/aws-targets.json <<EOF
[
  {
    "name": "dev",
    "account": "$ACCOUNT_ID",
    "region": "$REGION"
  }
]
EOF

# Step 2: CDK dependencies (locked) and build
echo "Installing CDK dependencies..."
cd agentcore/cdk
[ -d node_modules ] || npm ci --no-audit --no-fund
npm run build
# Call the CDK CLI by path: this project's package.json also names its app "cdk",
# so `npx cdk` would run the app instead of the CLI.
CDK=./node_modules/aws-cdk/bin/cdk

# Step 3: bootstrap (first time per account and Region; a no-op afterwards)
echo "Checking CDK bootstrap..."
"$CDK" bootstrap "aws://$ACCOUNT_ID/$REGION"

# Step 4: deploy. Synthesis validates agentcore.json against the AgentCore schema.
echo "Deploying the stack (the first deploy builds two Runtime images in CodeBuild)..."
"$CDK" deploy --require-approval never --outputs-file ../../cdk-outputs.json
cd ../..

# Step 5: the chat online evaluation config (managed third-party evaluators, which the
# CloudFormation schema does not accept yet; see scripts/chat_online_eval.py)
echo "Applying the chat online evaluation config..."
uv run --quiet --with boto3 python scripts/chat_online_eval.py apply --region "$REGION"

# Step 6: seed sample data
echo "Seeding DynamoDB..."
uv run --quiet --with boto3 python scripts/seed_dynamodb.py --region "$REGION"

echo ""
echo "Done. Try:"
echo "   uv run --with boto3 python scripts/test_invoke.py --region $REGION"
echo "   uv run --with boto3 python scripts/chat.py --user user-001 --region $REGION"
