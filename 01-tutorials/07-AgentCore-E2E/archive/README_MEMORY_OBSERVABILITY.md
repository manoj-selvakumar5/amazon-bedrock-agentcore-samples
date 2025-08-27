# AgentCore Memory with Observability

This implementation combines **AgentCore Memory** functionality from `lab-02-agentcore-memory.ipynb` with comprehensive **OpenTelemetry observability** from `Optional-lab-agentcore-observability.ipynb`.

## 🎯 What This Provides

### Memory Capabilities
- **Short-Term Memory (STM)**: Immediate conversation context within sessions
- **Long-Term Memory (LTM)**: Persistent customer preferences and semantic information
- **Multi-tenant Memory**: Isolated customer data with namespace organization
- **Automatic Memory Hooks**: Seamless context retrieval and interaction storage

### Observability Features
- **OpenTelemetry Instrumentation**: Automatic tracing of all memory operations
- **CloudWatch GenAI Observability**: Rich dashboards and trace visualization
- **Session Correlation**: Track customer interactions across conversations
- **Performance Monitoring**: Memory operation timing and success metrics

## 🚀 Quick Start

### Prerequisites
```bash
# Install required packages
pip install strands-agents boto3 aws-opentelemetry-distro python-dotenv

# Ensure CloudWatch Transaction Search is enabled
# https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html
```

### Basic Usage

1. **Run with default settings:**
```bash
./run_memory_observability.sh
```

2. **Run with custom parameters:**
```bash
SESSION_ID="my-session-123" \
ACTOR_ID="customer_002" \
QUERY="I need help with my laptop" \
SEED_HISTORY="true" \
./run_memory_observability.sh
```

3. **Run directly with Python:**
```bash
opentelemetry-instrument python agentcore_memory_observability.py \
  --session-id "session-123" \
  --actor-id "customer_001" \
  --query "What gaming headphones do you recommend?" \
  --seed-history
```

## 📊 Observability Features

### 1. Memory Operation Tracing
Every memory operation is automatically traced:
- **Memory Creation**: Resource provisioning and strategy setup
- **Event Storage**: Saving customer interactions to memory
- **Memory Retrieval**: Context lookup and preference matching
- **Hook Execution**: Automatic memory integration with agent conversations

### 2. Session Correlation
All operations are correlated by session ID using OpenTelemetry baggage:
```python
# Session context is automatically set
context_token = memory_obs.set_session_context(session_id)
```

### 3. CloudWatch Integration
Traces appear in CloudWatch GenAI Observability with:
- **Agent Sessions**: Grouped by customer and session
- **Trace Waterfall**: Visual timeline of memory operations
- **Performance Metrics**: Memory operation latencies
- **Error Tracking**: Automatic exception capture

## 🧠 Memory Architecture

### Memory Strategies
```python
strategies = [
    {
        "USER_PREFERENCE": {
            "name": "CustomerPreferences",
            "description": "Captures customer preferences and behavior",
            "namespaces": ["support/customer/{actorId}/preferences"],
        }
    },
    {
        "SEMANTIC": {
            "name": "CustomerSupportSemantic", 
            "description": "Stores facts from conversations",
            "namespaces": ["support/customer/{actorId}/semantic"],
        }
    },
]
```

### Memory Hooks Integration
The `ObservableCustomerSupportMemoryHooks` class provides:
- **Pre-processing**: Retrieve customer context before agent processing
- **Post-processing**: Save interactions after agent responses
- **Observability**: Trace all hook operations with OpenTelemetry

## 🔧 Configuration

### Environment Variables
The system automatically creates a `.env` file with:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# OpenTelemetry Configuration
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=agents/customer-support-assistant-logs,x-aws-log-stream=default,x-aws-metric-namespace=agents
OTEL_RESOURCE_ATTRIBUTES=service.name=customer-support-assistant-memory
AGENT_OBSERVABILITY_ENABLED=true
```

### Command Line Arguments
```bash
python agentcore_memory_observability.py --help

options:
  --session-id SESSION_ID    Session ID for trace correlation
  --actor-id ACTOR_ID        Customer identifier
  --query QUERY              Test query for the agent
  --seed-history             Seed sample customer history
  --region REGION            AWS region to use
```

## 📈 Monitoring and Debugging

### CloudWatch GenAI Observability
1. **Navigate to CloudWatch Console**
2. **Go to GenAI Observability → Bedrock AgentCore**
3. **View Sessions** to see customer interactions
4. **View Traces** to see detailed operation timing

### Key Metrics to Monitor
- **Memory Operation Latency**: Time to retrieve/store memories
- **Context Retrieval Success Rate**: How often relevant context is found
- **Memory Processing Time**: LTM extraction timing
- **Session Continuity**: Cross-session memory persistence

### Trace Analysis
Look for these span names in traces:
- `memory.create_memory`: Memory resource creation
- `memory.retrieve_memories`: Context retrieval operations
- `memory.create_event`: Interaction storage
- `hooks.retrieve_customer_context`: Pre-processing hooks
- `hooks.save_support_interaction`: Post-processing hooks
- `agent.invoke`: Complete agent interaction

## 🔍 Example Trace Flow

```
agent.invoke
├── hooks.retrieve_customer_context
│   ├── memory.retrieve_memories (preferences)
│   └── memory.retrieve_memories (semantic)
├── [Agent Processing with Tools]
└── hooks.save_support_interaction
    └── memory.create_event
```

## 🛠 Troubleshooting

### Common Issues

1. **Memory processing taking long**: LTM extraction can take 20-30 seconds
2. **No context found**: Customer may be new or LTM not yet processed
3. **OpenTelemetry not working**: Check AWS credentials and CloudWatch Transaction Search
4. **SSM parameter errors**: Script handles missing parameters gracefully

### Debug Tips
- Check CloudWatch Logs for detailed error messages
- Use `--seed-history` to create test data
- Monitor memory processing with `wait_for_memory_processing()`
- Verify AWS permissions for Memory, CloudWatch, and SSM

## 🔗 Related Documentation

- [Amazon Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- [AgentCore Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
- [CloudWatch GenAI Observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-GenAI-Observability.html)
- [AWS OpenTelemetry Python](https://aws-otel.github.io/docs/getting-started/python-sdk)

## 🎯 Key Benefits

1. **Complete Observability**: Every memory operation is traced and monitored
2. **Production Ready**: Built for scale with automatic error handling
3. **Customer Context**: Persistent memory across sessions for personalized experiences
4. **Easy Integration**: Drop-in replacement for basic agents with memory capabilities
5. **Rich Debugging**: Detailed traces help troubleshoot memory and agent issues
