#!/bin/bash

# AgentCore Memory with Native Observability Runner
# ================================================
# 
# This script demonstrates AgentCore Memory's BUILT-IN observability features
# instead of manually implementing OpenTelemetry instrumentation.
#
# Native AgentCore Memory provides:
# - Automatic spans for all memory operations
# - Built-in extraction/consolidation logs
# - CloudWatch metrics in AWS/Bedrock/AgentCore/Memory namespace
# - Seamless integration with CloudWatch GenAI Observability

set -e

echo "🚀 AgentCore Memory with NATIVE Observability"
echo "=============================================="
echo ""
echo "This uses AgentCore Memory's built-in observability features:"
echo "• Automatic spans for CreateEvent, RetrieveMemoryRecords, etc."
echo "• Native extraction/consolidation logs"
echo "• Built-in CloudWatch metrics"
echo "• No manual OpenTelemetry setup required!"
echo ""

# Default values
SESSION_ID=${SESSION_ID:-$(uuidgen)}
ACTOR_ID=${ACTOR_ID:-"customer_001"}
QUERY=${QUERY:-"What headphones would you recommend for gaming?"}
SEED_HISTORY=${SEED_HISTORY:-"true"}

echo "🔧 Configuration:"
echo "  Session ID: $SESSION_ID"
echo "  Actor ID: $ACTOR_ID"
echo "  Query: $QUERY"
echo "  Seed History: $SEED_HISTORY"
echo ""

# Build the command arguments
CMD_ARGS="--session-id $SESSION_ID --actor-id $ACTOR_ID --query \"$QUERY\""
if [ "$SEED_HISTORY" = "true" ]; then
    CMD_ARGS="$CMD_ARGS --seed-history"
fi

echo "🔍 Running with NATIVE AgentCore Memory observability..."
echo "Command: python agentcore_memory_native_observability.py $CMD_ARGS"
echo ""

# Run the script with native observability (no OpenTelemetry wrapper needed)
eval "python agentcore_memory_native_observability.py $CMD_ARGS"

echo ""
echo "✅ Execution completed with native observability!"
echo ""
echo "📊 View native AgentCore Memory observability data:"
echo ""
echo "🔍 CloudWatch GenAI Observability:"
echo "  https://console.aws.amazon.com/cloudwatch/home#genai-observability:bedrock-agentcore"
echo ""
echo "📈 CloudWatch Metrics (Memory namespace):"
echo "  https://console.aws.amazon.com/cloudwatch/home#metricsV2:graph=~();query=AWS%2FBedrock%2FAgentCore%2FMemory"
echo ""
echo "📋 CloudWatch Logs (Memory operations):"
echo "  • /aws/vendedlogs/bedrock-agentcore/memory/extraction"
echo "  • /aws/vendedlogs/bedrock-agentcore/memory/consolidation"
echo ""
echo "🎯 Key spans to look for in GenAI Observability:"
echo "  • CreateEvent (when saving interactions)"
echo "  • RetrieveMemoryRecords (when getting context)"
echo "  • GetEvent, ListEvents (internal operations)"
echo ""
