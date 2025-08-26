# AgentCore Observability Gap Analysis Report

## Executive Summary

This report analyzes the observability gaps in the AgentCore E2E workshop by comparing AWS's native AgentCore observability capabilities against what's currently implemented. The workshop demonstrates only ~20% of available observability features, focusing primarily on basic tracing while missing critical metrics, monitoring, and operational insights.

---

## 1. Overall Observability Coverage

### Available AgentCore Observability Features vs Workshop Implementation

| **Primitive** | **Native Features Available** | **Workshop Implementation** | **Coverage** |
|--------------|-------------------------------|----------------------------|--------------|
| **Runtime** | Metrics, Traces, Spans, Logs | Basic traces only | 25% |
| **Memory** | Metrics, Spans, Logs | None | 0% |
| **Gateway** | Metrics | None | 0% |
| **Identity** | Limited native support | Basic JWT auth | N/A |
| **Built-in Tools** | Metrics | Not applicable | N/A |

---

## 2. Traces & Spans Analysis

### ✅ What AgentCore Provides Natively

#### **Runtime Traces**
- Full request flow visualization
- Session correlation
- Tool invocation tracking
- Model interaction spans
- Error propagation paths
- Available in CloudWatch GenAI Observability

#### **Memory Spans** (Requires enablement)
```
- CreateEvent (memory.id, session.id, event.id, actor.id)
- GetEvent (memory.id, session.id, event.id)
- ListEvents (memory.id, session.id)
- DeleteEvent (memory.id, session.id, event.id)
- RetrieveMemoryRecords (memory.id, namespace)
- ListMemoryRecords (memory.id, namespace)
```

### ❌ What's Missing in the Workshop

| **Gap** | **Impact** | **Implementation Effort** |
|---------|-----------|-------------------------|
| Memory spans not enabled | Cannot trace memory operations | Low - Config change |
| Custom span attributes missing | No business context in traces | Medium - Code instrumentation |
| Cross-primitive correlation weak | Hard to trace full request flow | Medium - Add trace context |
| Gateway tool spans not shown | Cannot see tool execution details | Low - Enable in config |

### 📊 Workshop Trace Coverage

```
Current Implementation:
├── ✅ Basic session traces
├── ✅ Agent invocation spans  
├── ✅ CloudWatch GenAI dashboard view
└── ❌ Missing:
    ├── Memory operation spans
    ├── Gateway tool execution spans
    ├── Custom business attributes
    └── Error span details
```

---

## 3. Metrics Analysis

### ✅ What AgentCore Provides Natively

#### **Runtime Metrics** (CloudWatch + GenAI Observability)
| Metric | Description | Dashboard Location |
|--------|-------------|-------------------|
| `Invocations` | Total API requests/min | GenAI + CloudWatch |
| `Throttles` | 429 errors/min | GenAI + CloudWatch |
| `SystemErrors` | 5xx errors/min | GenAI + CloudWatch |
| `UserErrors` | 4xx errors/min | GenAI + CloudWatch |
| `Latency` | Response time (ms) | GenAI + CloudWatch |
| `SessionCount` | Active sessions | GenAI + CloudWatch |
| `TotalErrors` | Error percentage | GenAI + CloudWatch |

#### **Gateway Metrics** (CloudWatch only)
| Metric | Description | Dashboard Location |
|--------|-------------|-------------------|
| `Invocations` | Requests per API | CloudWatch only |
| `Duration` | End-to-end time | CloudWatch only |
| `TargetExecutionTime` | Lambda/OpenAPI execution | CloudWatch only |
| `TargetType` | Breakdown by target type | CloudWatch only |

#### **Memory Metrics** (CloudWatch only)
| Metric | Description | Dashboard Location |
|--------|-------------|-------------------|
| `Latency` | Operation time | CloudWatch only |
| `CreationCount` | Memories created/min | CloudWatch only |
| `Invocations` | API calls/min | CloudWatch only |
| `Errors` | Failure count | CloudWatch only |

### ❌ What's Missing in the Workshop

```yaml
Runtime Metrics (0% shown):
  - No metric dashboards created
  - No performance baselines
  - No capacity monitoring
  - No cost tracking

Gateway Metrics (0% shown):
  - No per-tool metrics
  - No target execution analysis  
  - No tool failure rates
  - No latency breakdowns

Memory Metrics (0% shown):
  - No memory operation metrics
  - No creation rate tracking
  - No retrieval performance
  - No memory growth monitoring
```

---

## 4. Logging Analysis

### ✅ What AgentCore Provides Natively

#### **Memory Logs** (When enabled)
```json
{
  "Extraction Logs": {
    "fields": ["resource_arn", "memory_strategy_id", "namespace", "actor_id", "session_id"],
    "events": ["start", "completion", "errors", "memories_extracted"]
  },
  "Consolidation Logs": {
    "fields": ["resource_arn", "memory_strategy_id", "namespace", "session_id"],
    "events": ["start", "completion", "additions", "updates", "failures"]
  }
}
```

### ❌ What's Missing in the Workshop
- Memory extraction/consolidation logs not configured
- No structured logging implementation
- No log correlation with traces
- No custom log groups for primitives

---

## 5. Operational Observability Gaps

### Critical Missing Components

| **Component** | **Native Support** | **Workshop Status** | **Business Impact** |
|--------------|-------------------|-------------------|-------------------|
| **CloudWatch Alarms** | Full support | ❌ Not implemented | No proactive alerting |
| **Custom Dashboards** | Full support | ❌ Not created | No operational view |
| **Cost Metrics** | Via CloudWatch | ❌ Not tracked | No cost visibility |
| **Performance Baselines** | Metrics available | ❌ Not established | Cannot detect degradation |
| **Error Categorization** | Error codes available | ❌ Not utilized | Poor troubleshooting |
| **Capacity Planning** | Throttle metrics available | ❌ Not monitored | Risk of hitting limits |

---

## 6. Implementation Priority Matrix

### High Priority (Quick Wins - Native Features)

| **Task** | **Effort** | **Impact** | **Implementation** |
|----------|-----------|-----------|-------------------|
| Enable Memory metrics | Low | High | Add CloudWatch config |
| Create Runtime dashboard | Low | High | Use CloudWatch console |
| Enable Gateway metrics | Low | High | Configuration change |
| Add CloudWatch alarms | Medium | High | CloudFormation template |

### Medium Priority (Enhanced Visibility)

| **Task** | **Effort** | **Impact** | **Implementation** |
|----------|-----------|-----------|-------------------|
| Enable Memory spans/logs | Medium | Medium | Code instrumentation |
| Cross-primitive correlation | Medium | High | Add trace context |
| Custom metric dashboards | Medium | High | CloudWatch dashboards |
| Cost tracking dashboard | Low | Medium | Use token metrics |

### Low Priority (Advanced Features)

| **Task** | **Effort** | **Impact** | **Implementation** |
|----------|-----------|-----------|-------------------|
| Custom span attributes | High | Medium | Code changes |
| Business KPI metrics | High | Medium | Custom metrics |
| Advanced log analytics | High | Low | CloudWatch Insights |

---

## 7. Recommended Workshop Enhancements

### 📝 New Lab: "Lab 7 - Production Observability"

```markdown
### Lab Objectives:
1. Enable ALL native AgentCore metrics
2. Create operational dashboards for each primitive
3. Set up CloudWatch alarms for SLA monitoring
4. Implement cost tracking and optimization
5. Configure memory operation tracking

### Deliverables:
- Runtime performance dashboard
- Gateway tool usage dashboard  
- Memory operations dashboard
- Cost analysis dashboard
- Alert configuration (errors, latency, throttling)
- Runbook for common issues
```

### 🔧 Enhance Existing Labs

**Lab 2 (Memory):**
```python
# Add memory observability configuration
memory_config = {
    "enableSpans": True,
    "enableLogs": True,
    "logGroup": "/aws/vendedlogs/bedrock-agentcore/memory/",
    "metrics": ["CreationCount", "Latency", "Errors"]
}
```

**Lab 3 (Gateway):**
```python
# Show Gateway metrics
gateway_metrics = {
    "dashboard": "TargetExecutionTime by Tool",
    "alarms": ["High Error Rate", "Slow Tool Response"],
    "metrics": ["Invocations", "Duration", "TargetType"]
}
```

**Lab 4 (Runtime):**
```python
# Complete observability setup
runtime_observability = {
    "metrics": ["All CloudWatch metrics"],
    "dashboards": ["Performance", "Errors", "Capacity"],
    "alarms": ["SLA breaches", "High error rate"],
    "logs": ["Structured logging with correlation"]
}
```

---

## 8. Detailed Gap Analysis by Primitive

### 🏃 AgentCore Runtime Gaps

**Available but Not Shown:**
- Invocation metrics (requests/min)
- Error breakdown (4xx vs 5xx)
- Throttling patterns
- Session aggregation
- Latency percentiles

**Implementation Path:**
1. Query CloudWatch metrics namespace: `AWS/Bedrock/AgentCore/Runtime`
2. Create custom dashboard with widgets for each metric
3. Set up alarms for SLA thresholds
4. Enable detailed logging with correlation IDs

### 🔌 AgentCore Gateway Gaps

**Available but Not Shown:**
- Per-tool invocation counts
- Target execution breakdown (Lambda vs OpenAPI)
- Tool-specific error rates
- Duration vs execution time analysis

**Implementation Path:**
1. Enable Gateway metrics collection
2. Query CloudWatch namespace: `AWS/Bedrock/AgentCore/Gateway`
3. Create tool performance dashboard
4. Monitor tool SLAs separately

### 🧠 AgentCore Memory Gaps

**Available but Not Shown:**
- Memory creation rates
- Retrieval latency
- Extraction/consolidation logs
- Memory operation spans

**Implementation Path:**
1. Configure memory log groups
2. Enable span collection
3. Query CloudWatch namespace: `AWS/Bedrock/AgentCore/Memory`
4. Create memory analytics dashboard

---

## 9. Production Readiness Checklist

### Essential Observability Components

```bash
# Metrics Configuration
□ Enable all Runtime metrics
□ Enable all Gateway metrics  
□ Enable all Memory metrics
□ Configure metric retention policies

# Dashboards
□ Create Runtime performance dashboard
□ Create Gateway tool usage dashboard
□ Create Memory operations dashboard
□ Create cost analysis dashboard
□ Create executive summary dashboard

# Alerting
□ Error rate > 5% alarm
□ P99 latency > 3s alarm
□ Throttling rate > 1% alarm
□ Memory creation failures alarm
□ Tool invocation failures alarm

# Logging
□ Enable structured JSON logging
□ Configure log retention
□ Set up log aggregation
□ Enable memory operation logs
□ Implement correlation IDs

# Tracing
□ Enable memory spans
□ Add custom span attributes
□ Configure trace sampling
□ Set up trace retention
□ Enable cross-service correlation

# Cost Management
□ Track token usage metrics
□ Monitor model invocation costs
□ Set up budget alerts
□ Create cost allocation tags
□ Implement cost optimization rules
```

---

## 10. Metrics Deep Dive

### Runtime Metrics Details

```yaml
Invocations:
  Type: Count
  Unit: Count/Minute
  Use: Track request volume trends
  Alert: Sudden spikes or drops

Latency:
  Type: Duration
  Unit: Milliseconds
  Use: Monitor response times
  Alert: P99 > 3000ms

SystemErrors:
  Type: Count
  Unit: Count/Minute
  Use: Track infrastructure issues
  Alert: > 1% of invocations

UserErrors:
  Type: Count  
  Unit: Count/Minute
  Use: Track client issues
  Alert: > 5% of invocations

Throttles:
  Type: Count
  Unit: Count/Minute
  Use: Capacity planning
  Alert: Any throttling
```

### Gateway Metrics Details

```yaml
Duration:
  Type: Duration
  Unit: Milliseconds
  Use: End-to-end tool time
  Alert: > 5000ms

TargetExecutionTime:
  Type: Duration
  Unit: Milliseconds
  Use: Actual tool execution
  Alert: > 3000ms

TargetType:
  Type: Count by Type
  Unit: Count/Minute
  Use: Tool type distribution
  Alert: Unusual patterns
```

### Memory Metrics Details

```yaml
CreationCount:
  Type: Count
  Unit: Count/Minute
  Use: Memory generation rate
  Alert: Failures or spikes

Latency:
  Type: Duration
  Unit: Milliseconds  
  Use: Operation performance
  Alert: > 1000ms

Errors:
  Type: Count
  Unit: Count/Minute
  Use: Failure tracking
  Alert: Any errors
```

---

## 11. Conclusion

### Current State
- **20% feature utilization** - Workshop uses minimal observability features
- **Trace-focused** - Only basic tracing, missing metrics entirely
- **No operational readiness** - Missing dashboards, alarms, and monitoring

### Required State
- **Full metrics enablement** - Use all native CloudWatch metrics
- **Complete primitive coverage** - Monitor Runtime, Gateway, and Memory
- **Production readiness** - Dashboards, alarms, and runbooks

### Impact of Gaps
- **Operational blindness** - Cannot detect issues proactively
- **No capacity planning** - Risk of hitting limits unexpectedly
- **Poor troubleshooting** - Limited visibility into failures
- **No cost control** - Token usage and costs not tracked

### Recommendation
Implement the high-priority items immediately as they require only configuration changes and provide significant observability improvements. The workshop should demonstrate production-grade observability using AgentCore's native features before considering custom implementations.

---

## Appendix A: Implementation Scripts

### Enable Memory Observability
```python
import boto3

def enable_memory_observability(memory_id):
    """Enable full observability for AgentCore Memory"""
    logs = boto3.client('logs')
    
    # Create log group
    log_group = f"/aws/vendedlogs/bedrock-agentcore/memory/{memory_id}"
    logs.create_log_group(logGroupName=log_group)
    
    # Configure memory with observability
    memory_config = {
        "memoryId": memory_id,
        "observability": {
            "enableSpans": True,
            "enableLogs": True,
            "enableMetrics": True,
            "logGroup": log_group
        }
    }
    return memory_config
```

### Create Runtime Dashboard
```python
def create_runtime_dashboard(runtime_name):
    """Create CloudWatch dashboard for Runtime metrics"""
    cloudwatch = boto3.client('cloudwatch')
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Bedrock/AgentCore/Runtime", "Invocations", {"stat": "Sum"}],
                        [".", "Latency", {"stat": "Average"}],
                        [".", "SystemErrors", {"stat": "Sum"}],
                        [".", "UserErrors", {"stat": "Sum"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": f"{runtime_name} Performance"
                }
            }
        ]
    }
    
    cloudwatch.put_dashboard(
        DashboardName=f"{runtime_name}-dashboard",
        DashboardBody=json.dumps(dashboard_body)
    )
```

---

## Appendix B: Quick Reference

### CloudWatch Namespaces
- Runtime: `AWS/Bedrock/AgentCore/Runtime`
- Gateway: `AWS/Bedrock/AgentCore/Gateway`  
- Memory: `AWS/Bedrock/AgentCore/Memory`

### Log Groups
- Runtime: `/aws/bedrock-agentcore/runtimes/{runtime-id}`
- Memory: `/aws/vendedlogs/bedrock-agentcore/memory/{memory-id}`
- Gateway: `/aws/bedrock-agentcore/gateway/{gateway-id}`

### Key Metrics to Monitor
1. **Error Rate**: (SystemErrors + UserErrors) / Invocations
2. **Availability**: 1 - (SystemErrors / Invocations)
3. **Performance**: P50, P90, P99 Latency
4. **Capacity**: Throttles / Invocations
5. **Cost**: Token usage * Model pricing