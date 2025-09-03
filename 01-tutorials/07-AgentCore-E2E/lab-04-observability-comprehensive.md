### Step 4: AgentCore Observability

[AgentCore Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) provides monitoring and tracing capabilities for AI agents using Amazon OpenTelemetry Python Instrumentation and Amazon CloudWatch GenAI Observability.

#### Agents

Default AgentCore Runtime configuration allows for logging our agent's traces on CloudWatch by means of **AgentCore Observability**. These traces can be seen on the AWS CloudWatch GenAI Observability dashboard. Navigate to Cloudwatch → GenAI Observability → Bedrock AgentCore.

![Agents Overview on CloudWatch](images/observability_agents.png)

#### Sessions

The Sessions view shows the list of all the sessions associated with all agents in your account.

![sessions](images/sessions_lab5_observability.png)

#### Traces

Trace view lists all traces from your agents in this account. To work with traces:

- Choose Filter traces to search for specific traces.
- Sort by column name to organize results.
- Under Actions, select Logs Insights to refine your search by querying across your log and span data or select Export selected traces to export.

![traces](images/traces_lab4_observability.png)

---

## Production Monitoring with CloudWatch Metrics

Beyond GenAI Observability traces, AgentCore publishes detailed performance metrics to CloudWatch under the `AWS/Bedrock-AgentCore` namespace. These metrics provide real-time visibility into your agent's production behavior across all components.

### Runtime Metrics

AgentCore Runtime publishes metrics at request boundaries and aggregates them per dimension, giving you precise visibility into agent performance:

**Finding Your Runtime Metrics**
1. Navigate to CloudWatch Console → Metrics → All metrics
2. Select the `AWS/Bedrock-AgentCore` namespace
3. Search for your Runtime ARN from Step 3
4. Choose dimension combinations to analyze specific aspects

**Key Runtime Metrics**
- **Invocations** - Total requests processed by your agent's Data Plane API
- **Latency** - End-to-end processing time from request receipt to final response token
- **Sessions** - Total active agent sessions for capacity planning
- **UserErrors** - Client-side errors (400, 404, 403) indicating request issues
- **SystemErrors** - Internal server errors (500) requiring infrastructure investigation
- **Throttles** - Requests rejected due to TPS or quota limits (429)

**Creating Runtime Dashboards**
Build comprehensive monitoring dashboards with widgets for:
- Invocation rates over time (line graph)
- Average latency trends (number widget)
- Error rate percentages (gauge widget)
- Active session counts (bar chart)

### Memory Metrics

AgentCore Memory operations emit metrics for retrieval, consolidation, and extraction workflows, enabling you to optimize memory performance:

**Key Memory Operations**
- **RetrieveMemoryRecords** - Memory searches during agent reasoning
- **Consolidation** - Background processing to optimize memory structure
- **Extraction** - Key information extraction from conversations
- **CreateEvent** - New memory event creation
- **GetMemory** - Memory configuration retrieval
- **CreateMemory** - Memory resource initialization

**Memory Dimension Combinations**
Memory metrics require specific dimension combinations for proper querying:
- `Resource + Operation` - Most important for analyzing specific memory workflows
- `Resource` alone - Aggregated view across all memory operations

**Memory Analysis Periods**
- **5m-15m** - Real-time memory debugging during active conversations
- **1h-3h** - Session-level memory pattern analysis
- **1d-7d** - Long-term memory consolidation trends

### Gateway Metrics

Gateway publishes tool execution metrics through MCP protocol operations, focusing on tool performance and infrastructure efficiency:

**Key Gateway Operations**
- **CallToolMcp** - Tool execution through MCP protocol (most critical metric)
- **TargetExecutionTime** - Actual tool execution time (Lambda, OpenAPI)
- **Latency** - Gateway processing overhead
- **InitializeMcp** - MCP connection establishment
- **ListToolsMcp** - Tool discovery during initialization

**Gateway Performance Analysis**
- **TargetExecutionTime vs Latency** - Tools should do most work, not gateway
- **Target Type Distribution** - Compare Lambda, OpenAPI, and MCP performance
- **MCP Protocol Health** - Monitor connection stability

**Performance Benchmarks**
- TargetExecutionTime: <2000ms for Lambda functions
- Gateway Latency: <200ms for processing overhead
- Gateway overhead: <20% of total execution time
- Error rates: <5% UserErrors, 0% SystemErrors

---

## CloudWatch Logs for Deep Analysis

AgentCore Runtime streams structured logs to CloudWatch Logs, with JSON-formatted entries providing detailed operational insights:

### Log Structure

**Application Logs**
- Location: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT`
- Content: Agent conversations, tool invocations, memory operations, model interactions
- Format: Structured JSON with request IDs, session IDs, and trace identifiers
- Use cases: Debugging agent logic, analyzing conversation patterns, optimizing responses

**System Logs**
- Location: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT/runtime-logs`
- Content: Container lifecycle events, infrastructure messages, resource utilization
- Format: System-level events with timestamps and severity levels
- Use cases: Troubleshooting deployments, monitoring infrastructure health

### CloudWatch Logs Insights Queries

Leverage CloudWatch Logs Insights for powerful log analysis:

**Finding Slow Responses**
- Identify requests exceeding performance SLAs
- Correlate slow responses with specific tools or memory operations
- Analyze patterns in response time degradation

**Session Flow Analysis**
- Follow complete conversations from start to finish
- Track memory retrievals and tool invocations within sessions
- Debug context switching and state management issues

**Error Pattern Investigation**
- Locate error messages and stack traces quickly
- Identify recurring error patterns and root causes
- Track error frequency trends over time

### Log Correlation

Log entries include correlation identifiers:
- **traceId** - Links to GenAI Observability traces
- **sessionId** - Connects multiple requests within conversations
- **requestId** - Enables cross-component request tracking

---

## Security Auditing with CloudTrail

CloudTrail records API invocations as immutable event records, providing comprehensive auditing across all AgentCore components:

### Event Categories

**Runtime Management Events**
- `CreateRuntime` - Agent deployment to production
- `UpdateRuntime` - Configuration changes and updates
- `DeleteRuntime` - Agent removal and cleanup
- `GetRuntime` - Configuration retrieval and status checks

**Memory Management Events**
- `CreateMemory` - Memory resource creation
- `GetMemory` - Memory configuration access
- `DeleteMemory` - Memory resource cleanup

**Gateway Management Events**
- `CreateGateway` - Gateway resource creation
- `CreateTarget` - Tool target configuration
- `DeleteGateway` - Gateway cleanup

**Invocation Events**
- `InvokeAgentRuntime` - Every customer interaction with agents
- Includes session identifiers, user context, and request metadata
- Enables usage analytics and billing reconciliation

### CloudTrail Analysis

**Identity and Access Monitoring**
- Track who performs management operations
- Monitor authentication patterns and access attempts
- Identify privilege escalation or unauthorized access

**Usage Pattern Analytics**
- Analyze customer interaction frequencies
- Identify peak usage times for capacity planning
- Track geographic distribution of requests

**Compliance Auditing**
- Maintain complete audit trails for regulatory requirements
- Generate user activity reports for compliance officers
- Demonstrate proper access controls and data handling

---

## Unified Observability Strategy

Combine metrics, logs, and CloudTrail data for comprehensive production monitoring:

### Three Pillars Integration

**Performance Monitoring (Metrics)**
- Real-time visibility across Runtime, Memory, and Gateway operations
- Proactive alerting on SLA violations and error rates
- Capacity planning through usage trend analysis

**Operational Insights (Logs)**
- Deep debugging capabilities for customer-specific issues
- Pattern analysis across conversations and tool usage
- Performance optimization through detailed execution traces

**Security and Compliance (CloudTrail)**
- Complete API activity audit trail across all components
- Access pattern monitoring and anomaly detection
- Regulatory compliance documentation and reporting

### Practical Troubleshooting Workflow

When investigating production issues:

1. **Start with Metrics Dashboard**
   - Review Runtime latency for performance issues
   - Check Memory consolidation metrics for context problems
   - Analyze Gateway tool execution times for infrastructure bottlenecks

2. **Correlate Across Components**
   - Memory retrieval spikes may correlate with Gateway tool calls
   - Runtime errors might trace back to Gateway target failures
   - Session metrics help identify user-specific vs system-wide issues

3. **Deep Dive with Logs**
   - Use trace IDs to follow requests across all components
   - Query specific time windows identified in metrics
   - Analyze JSON payloads for detailed error context

4. **Verify with CloudTrail**
   - Confirm identity and authorization context
   - Check for configuration changes affecting performance
   - Validate proper API usage patterns

### Production Best Practices

**Alert Configuration**
- Runtime: Latency >5s, Error rate >5%, Invocation anomalies
- Memory: RetrieveMemoryRecords failures, Consolidation errors
- Gateway: TargetExecutionTime >10s, MCP connection failures

**Dashboard Organization**
- Business metrics: Customer sessions, conversation success rates
- Technical metrics: P50/P90/P99 latencies across all components
- Infrastructure metrics: Error distributions, resource utilization

**Monitoring Cadence**
- Real-time: Critical error alerts and SLA violations
- Daily: Performance trend review and capacity analysis
- Weekly: Deep dive into optimization opportunities
- Monthly: Security audit and compliance reporting

---

## Key Takeaways

With AgentCore's comprehensive observability platform:

✅ **Complete Visibility** - Metrics, logs, and audit trails across Runtime, Memory, and Gateway

✅ **Proactive Monitoring** - Real-time alerts and dashboards for production reliability

✅ **Deep Debugging** - Correlated traces and structured logs for rapid issue resolution

✅ **Security Compliance** - Immutable audit trails and access pattern monitoring

Your production agent infrastructure now operates with full transparency, enabling you to maintain high performance, quickly resolve issues, and meet enterprise security requirements.

---

## What's Next?

With your agent deployed to production and fully observable across all components, you're ready for Lab 5 where you'll build a user-friendly interface that allows customers to interact naturally with your intelligent support agent!