#!/bin/bash

# AgentCore Memory Observability Runner
# ====================================
# 
# This script runs the AgentCore Memory with Observability using OpenTelemetry instrumentation.
# It demonstrates how to use the opentelemetry-instrument command to automatically capture
# telemetry data from memory operations and send them to CloudWatch GenAI Observability.

set -e

echo "🚀 AgentCore Memory with Observability"
echo "======================================"

# Check if OpenTelemetry distro is installed
if ! python -c "import aws_opentelemetry_distro" 2>/dev/null; then
    echo "📦 Installing AWS OpenTelemetry Distro..."
    pip install aws-opentelemetry-distro
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. The script will create one automatically."
fi

# Default values
SESSION_ID=${SESSION_ID:-$(uuidgen)}
ACTOR_ID=${ACTOR_ID:-"customer_001"}
QUERY=${QUERY:-"What headphones would you recommend for gaming?"}
SEED_HISTORY=${SEED_HISTORY:-"true"}

echo ""
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

echo "🔍 Running with OpenTelemetry instrumentation..."
echo "Command: opentelemetry-instrument python agentcore_memory_observability.py $CMD_ARGS"
echo ""

# Run the script with OpenTelemetry instrumentation
eval "opentelemetry-instrument python agentcore_memory_observability.py $CMD_ARGS"

echo ""
echo "✅ Execution completed!"
echo ""
echo "📊 To view traces and metrics:"
echo "  1. Go to AWS CloudWatch Console"
echo "  2. Navigate to GenAI Observability → Bedrock AgentCore"
echo "  3. View Sessions and Traces for session: $SESSION_ID"
echo ""
echo "🔗 Direct link to CloudWatch GenAI Observability:"
echo "  https://console.aws.amazon.com/cloudwatch/home#genai-observability:bedrock-agentcore"
