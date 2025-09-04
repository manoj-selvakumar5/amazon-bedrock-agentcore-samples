### Step 4: AgentCore Observability

[AgentCore Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) provides monitoring and tracing capabilities for AI agents using Amazon OpenTelemetry Python Instrumentation and Amazon CloudWatch GenAI Observability.

Default AgentCore Runtime configuration automatically enables comprehensive observability across all components, giving you complete visibility into your agent's production behavior without any additional configuration.

#### Understanding AgentCore's Built-in Observability

AgentCore automatically instruments your agents with **Amazon OpenTelemetry Python Instrumentation**, providing:

- **Automatic Trace Generation** - Every agent request creates distributed traces
- **Span Creation** - Individual operations become spans with timing and metadata  
- **Context Propagation** - Trace context flows across Runtime, Memory, and Gateway
- **Metric Collection** - Performance metrics automatically sent to CloudWatch
- **Zero Configuration** - Built-in instrumentation requires no code changes

**How OpenTelemetry Enables Observability:**

```
Customer Request → Runtime (span) → Memory (span) → Gateway (span) → Tool (span)
                     ↓                ↓               ↓              ↓
                 Trace Context → Trace Context → Trace Context → Trace Context
                     ↓                ↓               ↓              ↓
                CloudWatch      CloudWatch      CloudWatch     CloudWatch
                 Metrics         Metrics         Metrics        Metrics
```

This foundation enables three layers of production observability:
1. **GenAI Observability Dashboard** - Visual trace analysis and session monitoring
2. **CloudWatch Metrics** - Real-time performance monitoring across all components
3. **CloudWatch Logs & CloudTrail** - Deep debugging and security auditing

## Agents

Default AgentCore Runtime configuration allows for logging our agent's traces on CloudWatch by means of **AgentCore Observability**. These traces can be seen on the AWS CloudWatch GenAI Observability dashboard. Navigate to CloudWatch → GenAI Observability → Bedrock AgentCore.

![Agents Overview on CloudWatch](images/observability_agents.png)

The Agents view provides a high-level performance overview across your account:
- **Session distribution** by agent and time period
- **Error rate visualization** and performance trends  
- **Agent comparison** for multi-agent deployments
- **Real-time activity monitoring** and usage patterns

## Sessions

The Sessions view shows the list of all the sessions associated with all agents in your account.

![Sessions Overview](images/sessions_lab5_observability.png)

Session monitoring provides valuable insights into customer interactions:
- **Complete session lifecycle** from start to completion
- **Cross-session analysis** for returning customers
- **Session duration patterns** and conversation flows
- **User engagement metrics** and interaction patterns

## Traces

Trace view lists all traces from your agents in this account. To work with traces:

- Choose Filter traces to search for specific traces.
- Sort by column name to organize results.
- Under Actions, select Logs Insights to refine your search by querying across your log and span data or select Export selected traces to export.

![Traces Overview](images/traces_lab4_observability.png)

**Working with Traces:**
- **Filter by latency patterns** - Find all traces exceeding SLA thresholds
- **Error correlation analysis** - Identify patterns in failed requests
- **Component bottleneck identification** - Determine which spans contribute most to latency
- **Export selected traces** for offline analysis and reporting

#### 4.1 Monitor Agent Performance with CloudWatch Metrics

Your agent publishes detailed performance metrics to CloudWatch under the `AWS/Bedrock-AgentCore` namespace. Let's explore how to monitor your customer support agent's health and performance across all components.

**Use Case**: *"How many customers are using my agent today? Are they getting fast responses? Which tools are performing well?"*

##### Finding Your Agent Metrics

1. **Navigate to CloudWatch**
   - Open AWS Console → CloudWatch → Metrics → All metrics
   - Find namespace: **AWS/Bedrock-AgentCore**

*[Screenshot placeholder: CloudWatch metrics browser showing AWS/Bedrock-AgentCore namespace]*

2. **Search for Your Agent Components**
   - Use the search bar to find your Runtime ARN from Step 3
   - Search for your Memory ARN from Lab 2
   - Search for your Gateway ARN from Lab 3

*[Screenshot placeholder: Search results showing agent component metrics]*

##### Key Runtime Metrics Dashboard

Create a comprehensive dashboard to track your agent's health:

**Invocations** - *"How busy is my agent?"*
- Shows total customer queries processed
- Helps identify peak usage times and capacity needs
- Recommended statistic: **Sum**

**Latency** - *"How fast are my responses?"*
- End-to-end response time from request to final response token
- Target: Keep under 5 seconds for good customer experience
- Recommended statistic: **Average, P90, P99**

**Sessions** - *"How many concurrent customers?"*
- Active agent sessions for capacity planning
- Helps understand user engagement patterns
- Recommended statistic: **Average**

**Error Metrics** - *"What's going wrong?"*
- **UserErrors**: Client-side errors (400, 404, 403)
- **SystemErrors**: Internal server errors (500) requiring investigation
- **Throttles**: Requests rejected due to rate limits (429)
- Recommended statistic: **Sum**

*[Screenshot placeholder: Runtime metrics dashboard showing Invocations, Latency, Sessions, and Errors]*

##### Memory Operations Monitoring

**Use Case**: *"Why is my agent slow to remember what customers said earlier?"*

**Key Memory Metrics:**

**RetrieveMemoryRecords** - *"How long does context lookup take?"*
- Measures time to find relevant conversation history
- Slow retrieval directly impacts agent response times
- Target: Keep under 2 seconds
- Recommended statistic: **Average**

**Consolidation** - *"How is background memory processing performing?"*
- Background memory optimization and merging operations
- Runs after conversations to improve future retrieval
- Monitor for processing efficiency
- Recommended statistic: **Average** (latency), **Sum** (invocations)

**CreateEvent** - *"How efficiently are conversations being recorded?"*
- Recording new conversation events in real-time
- Should be fast and reliable for all interactions
- Recommended statistic: **Average** (latency), **Sum** (invocations)

##### Quick Memory Setup

1. In CloudWatch Metrics, search for your Memory ARN
2. Select dimension combination: **"Operation, Resource"**
3. Add these key metrics:
   - `RetrieveMemoryRecords Latency` (Average)
   - `RetrieveMemoryRecords Invocations` (Sum)
   - `Consolidation Latency` (Average)
   - `CreateEvent Invocations` (Sum)
4. Set period to 1 hour for debugging, 1 day for trends

*[Screenshot placeholder: Memory metrics showing RetrieveMemoryRecords performance over time]*

#### 4.2 Track Tool Execution with Gateway Metrics

Your agent calls tools through the Gateway using the Model Context Protocol (MCP). Let's monitor which tools are performing well and identify bottlenecks.

**Use Case**: *"My agent calls tools to help customers, but some seem slow. Which tools need optimization?"*

##### Key Gateway Performance Metrics

**CallToolMcp TargetExecutionTime** - *"How long do my tools actually take to run?"*
- Actual execution time for Lambda functions or API calls
- Most important metric for tool performance analysis
- Compare different tools to find bottlenecks
- Recommended statistic: **Average**

**CallToolMcp Latency** - *"How much overhead does the Gateway add?"*
- Gateway processing time vs actual tool execution
- Should be minimal compared to TargetExecutionTime
- Target: Gateway overhead < 20% of total time
- Recommended statistic: **Average**

**CallToolMcp Invocations** - *"Which tools are used most?"*
- Shows tool popularity and usage patterns
- Helps identify critical tools needing optimization
- Recommended statistic: **Sum**

**MCP Protocol Health:**
- **InitializeMcp** - Connection establishment monitoring
- **ListToolsMcp** - Tool discovery performance
- Monitor for protocol stability and reliability

##### Gateway Performance Analysis

1. **Search for Your Gateway ARN** in CloudWatch Metrics
2. **Select dimension combination:** **"Operation, Resource"**
3. **Add key metrics:**
   - `CallToolMcp TargetExecutionTime` (Average)
   - `CallToolMcp Latency` (Average)
   - `CallToolMcp Invocations` (Sum)
4. **Create performance comparison:**
   - Filter by different tool operations
   - Compare execution times across tools
   - Identify slow vs fast tools

*[Screenshot placeholder: Gateway metrics comparing tool execution times]*

**Performance Benchmarks:**
- TargetExecutionTime: < 2000ms for Lambda functions
- Gateway Latency: < 200ms for processing overhead  
- Error rates: < 5% UserErrors, 0% SystemErrors
- Gateway overhead: < 20% of total execution time

#### 4.3 Debug Issues with CloudWatch Logs

When customers report problems, use CloudWatch Logs to investigate what happened during their conversation. AgentCore automatically creates structured log groups with trace correlation identifiers.

**Log Structure:**

**Runtime Application Logs**
- Location: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT`
- Content: Agent conversations, tool invocations, memory operations
- Format: JSON with trace IDs, session IDs, request identifiers

**Runtime System Logs**
- Location: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT/runtime-logs`
- Content: Container lifecycle events, infrastructure messages
- Use: Deployment troubleshooting, resource monitoring

##### Practical Debugging Scenarios

**Scenario 1**: *"Customer says agent response was very slow"*

1. **Navigate to Logs**
   - CloudWatch → Logs → Log groups
   - Find: `/aws/bedrock-agentcore/runtimes/{your-runtime-id}-DEFAULT`

*[Screenshot placeholder: CloudWatch Logs groups list showing Runtime logs]*

2. **Use CloudWatch Logs Insights**
   - Go to Logs Insights
   - Select your Runtime log group
   - Query for slow responses:

```sql
fields @timestamp, traceId, sessionId, latency
| filter latency > 5000
| sort @timestamp desc
| limit 20
```

*[Screenshot placeholder: Logs Insights query showing slow response entries]*

**Scenario 2**: *"Agent gave wrong answer to customer question"*

1. **Find Customer Session**
   - Use session ID or timestamp from customer complaint
   - Follow complete conversation flow in logs

2. **Analyze Agent Reasoning**
   - Track which tools were called
   - Verify memory retrieval results
   - Review model response generation

```sql
fields @timestamp, sessionId, operation, toolName, duration
| filter sessionId = "your-session-id"
| sort @timestamp asc
```

*[Screenshot placeholder: Log entries showing agent reasoning flow for a specific session]*

##### Advanced Log Analysis

**Error Pattern Investigation:**
```sql
fields @timestamp, level, message, error
| filter level = "ERROR"
| stats count() by error
| sort count desc
```

**Tool Performance Analysis:**
```sql
fields @timestamp, toolName, executionTime
| filter operation = "CallTool"
| stats avg(executionTime), max(executionTime) by toolName
| sort avg(executionTime) desc
```

**Cross-Component Correlation:**
- **traceId** - Links to GenAI Observability traces
- **sessionId** - Connects multiple requests in conversations
- **requestId** - Enables distributed request tracking

#### 4.4 Security Auditing with CloudTrail

Track who's using your agent and ensure secure access with CloudTrail. CloudTrail provides immutable audit trails for all AgentCore API operations.

**Use Case**: *"I need to show compliance officers who accessed the agent and when"*

##### AgentCore API Event Auditing

CloudTrail automatically records every API interaction with your AgentCore resources:

**Management Plane Events:**
- `CreateRuntime`, `UpdateRuntime`, `DeleteRuntime` - Runtime lifecycle
- `CreateMemory`, `GetMemory`, `DeleteMemory` - Memory management  
- `CreateGateway`, `CreateTarget`, `DeleteGateway` - Gateway operations

**Data Plane Events:**
- `InvokeAgentRuntime` - Every customer interaction with your agent
- Includes user identity, session context, request metadata
- Enables usage analytics and compliance reporting

##### Viewing Agent Access

1. **Open CloudTrail Console**
   - AWS Console → CloudTrail → Event history

*[Screenshot placeholder: CloudTrail console event history view]*

2. **Filter for Your Agent**
   - Search for event name: **InvokeAgentRuntime**
   - Filter by your Runtime ARN
   - View user identity and access times

*[Screenshot placeholder: CloudTrail events filtered for agent invocations]*

##### Key Security Information Available

**Who**: User identity from authentication tokens  
**When**: Precise timestamps of each interaction
**What**: API calls made (create, invoke, update, delete)
**Where**: IP address and geographic location
**Result**: Success or failure status with error details

*[Screenshot placeholder: CloudTrail event detail showing user identity and action details]*

##### Security Monitoring Queries

**Identity and Access Analysis:**
```sql
-- Track runtime management operations by user
SELECT userIdentity.principalId, eventName, eventTime, sourceIPAddress
FROM cloudtrail_logs
WHERE eventName LIKE '%Runtime%' 
AND eventTime > '2024-01-01'
ORDER BY eventTime DESC
```

**Usage Pattern Analytics:**
```sql
-- Analyze invocation patterns by time and user
SELECT DATE(eventTime) as date, COUNT(*) as invocations
FROM cloudtrail_logs  
WHERE eventName = 'InvokeAgentRuntime'
GROUP BY DATE(eventTime)
ORDER BY date DESC
```

#### 4.5 Production Best Practices

##### Unified Observability Strategy

**Incident Response Workflow:**

1. **Alert Triage (Metrics)**
   - Check Runtime latency for performance issues
   - Review Memory operation metrics for context problems
   - Analyze Gateway metrics for tool execution bottlenecks

2. **Root Cause Analysis (Logs)**
   - Use trace IDs to follow requests across components
   - Query specific time windows identified in metrics
   - Analyze JSON payloads for detailed error context

3. **Security Validation (CloudTrail)**
   - Verify user identity and authorization context
   - Check for configuration changes affecting performance
   - Validate API usage patterns and access controls

##### Recommended Alert Configuration

**Runtime Alerts:**
- Latency > 5 seconds (Average over 5 minutes)
- Error rate > 5% (Math expression: Errors/Invocations * 100)
- Invocation anomalies (Anomaly detection)

**Memory Alerts:**
- RetrieveMemoryRecords latency > 2 seconds
- Consolidation failures (SystemErrors > 0)
- Memory operation anomalies

**Gateway Alerts:**
- TargetExecutionTime > 10 seconds
- MCP connection failures (InitializeMcp errors)
- Tool error rate > 5%

##### Dashboard Strategy

**Executive Dashboard:**
- Customer sessions and conversation success rates
- Agent availability and uptime metrics
- Business KPIs correlated with performance

**Operations Dashboard:**
- P50/P90/P99 latencies across all components
- Error distributions and failure patterns
- Resource utilization and capacity metrics

**Security Dashboard:**
- Access patterns and authentication metrics
- Failed login attempts and security events
- Configuration change audit trail

---

### Key Takeaways - Production Observability

With comprehensive AgentCore observability, you now have:

✅ **Complete Performance Visibility** - Real-time metrics across Runtime, Memory, and Gateway components

✅ **Deep Debugging Capabilities** - Structured logs with trace correlation and advanced query capabilities

✅ **Enterprise Security Auditing** - Immutable audit trails for compliance and access monitoring

✅ **Proactive Issue Prevention** - Integrated alerting and monitoring across all observability pillars

✅ **Production Excellence** - Best practices for enterprise-scale agent operations

Your AgentCore deployment now operates with full transparency, enabling proactive monitoring, rapid issue resolution, and comprehensive security compliance - exactly what you need for production AI agents serving real customers.

---

### What's Next?

With production-ready observability established across all AgentCore primitives, you're prepared for Lab 5 where you'll build a customer-facing interface that leverages this robust, monitored infrastructure for reliable customer interactions.