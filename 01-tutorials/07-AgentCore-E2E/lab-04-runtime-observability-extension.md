# Lab 4 Extension: Runtime Observability - Metrics, Logs, and CloudTrail

## Overview

This extension builds upon Lab 4 to provide comprehensive production monitoring and observability for your AgentCore Runtime deployment. You'll learn to monitor performance, debug issues, and maintain security compliance using AWS's native observability tools.

---

## Step 6: Monitor Your Production Agent with CloudWatch Metrics

Now that your agent is running in production with AgentCore Runtime, let's explore the comprehensive monitoring capabilities that are automatically enabled. AgentCore Runtime provides built-in observability to help you understand how your agent performs in production.

### Understanding Runtime Metrics

When you deploy an agent to AgentCore Runtime, Amazon automatically collects and publishes metrics to CloudWatch under the namespace `AWS/Bedrock-AgentCore`. These metrics give you visibility into:

- **Agent activity levels** - How many requests your agent is handling
- **Processing performance** - How quickly your agent responds to users
- **Reliability indicators** - Error rates and throttling events
- **Session management** - Number of concurrent customer sessions

*[Screenshot placeholder: CloudWatch Metrics homepage showing AWS/Bedrock-AgentCore namespace]*

### Navigating to Your Runtime Metrics

Let's find the metrics for your deployed customer support agent:

1. **Open CloudWatch Console**
   - Navigate to the AWS CloudWatch service in your AWS Console
   - Select **Metrics** from the left navigation panel
   - Click on **All metrics**

2. **Locate AgentCore Metrics**
   - In the metrics browser, find the namespace **AWS/Bedrock-AgentCore**
   - You'll see various dimension combinations available

3. **Filter by Your Runtime**
   - Use the search bar to enter your Runtime ARN from Step 3
   - Or search by your agent name: `customer_support_agent`

*[Screenshot placeholder: CloudWatch Metrics search showing Runtime ARN filter]*

### Key Runtime Metrics to Monitor

AgentCore Runtime provides these essential metrics for production monitoring:

**Invocations**
- Shows the total number of requests made to your agent's Data Plane API
- Each customer query counts as one invocation, regardless of request size or response status
- Helps you understand usage patterns and identify peak traffic times

**Latency** 
- Measures the total time elapsed between receiving a request and sending the final response token
- Represents complete end-to-end processing time including model inference, tool execution, and memory retrieval
- Critical for understanding and optimizing customer experience

**Sessions**
- Tracks the total number of agent sessions
- Useful for monitoring overall platform usage and capacity planning
- Helps understand user engagement patterns throughout the day

**Error Metrics**
- **User Errors**: Client-side errors from invalid requests (400), missing resources (404), or insufficient permissions (403)
- **System Errors**: Internal server errors (500) that may indicate infrastructure issues requiring investigation
- **Throttles**: Requests rejected due to exceeding allowed TPS or quota limits (429)

*[Screenshot placeholder: CloudWatch Metrics graph showing Invocations and Latency over time]*

### Creating Your First Runtime Dashboard

Let's create a dashboard to monitor your customer support agent:

1. In CloudWatch, navigate to **Dashboards** → **Create dashboard**
2. Name it: `CustomerSupportAgent-Runtime-Monitoring`
3. Add widgets for:
   - Invocations over time (line graph)
   - Average latency (number widget)
   - Error rate percentage (gauge)
   - Active sessions (bar chart)

*[Screenshot placeholder: Custom CloudWatch dashboard with Runtime metrics]*

---

## Step 7: Analyze Agent Behavior with CloudWatch Logs

Beyond metrics, AgentCore Runtime automatically sends detailed logs to CloudWatch Logs. These logs provide invaluable insights for debugging, optimization, and understanding agent behavior.

### Understanding Runtime Log Structure

When you deploy an agent to AgentCore Runtime, it automatically creates organized log groups:

**Application Logs**
- Location: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT`
- Contains: Your agent's application-level events, conversation flow, tool invocations, and responses
- Use for: Debugging agent logic, analyzing conversation patterns, and optimizing responses

**System Logs**
- Location: `/aws/bedrock-agentcore/runtimes/{runtime-id}-DEFAULT/runtime-logs`  
- Contains: Infrastructure-level events, container lifecycle events, and runtime system messages
- Use for: Troubleshooting deployment issues, monitoring resource utilization, and system health

*[Screenshot placeholder: CloudWatch Logs showing Runtime log groups]*

### Navigating to Your Agent Logs

1. **Access CloudWatch Logs**
   - In CloudWatch Console, select **Logs** → **Log groups**
   - Search for your runtime ID or agent name

2. **View Log Streams**
   - Click on your log group
   - You'll see multiple log streams, one for each container instance
   - Recent events appear at the top

*[Screenshot placeholder: CloudWatch Logs stream showing agent conversation logs]*

### Using CloudWatch Logs Insights

CloudWatch Logs Insights provides a powerful query language to analyze your logs at scale:

1. **Navigate to Logs Insights**
   - In CloudWatch, select **Logs** → **Logs Insights**
   - Select your Runtime log group

2. **Essential Queries for Runtime Analysis**

**Finding Slow Responses:**
- Identify requests that exceed your performance SLA
- Analyze patterns in slow responses
- Correlate with specific tools or memory operations

**Tracking Customer Sessions:**
- Follow a complete conversation from start to finish
- Understand context switching and memory usage
- Debug session-specific issues

**Error Investigation:**
- Quickly locate and analyze error messages
- Identify error patterns and root causes
- Track error frequency over time

*[Screenshot placeholder: Logs Insights query results showing slow responses]*

### Correlating Logs with Traces

Your Runtime logs include trace identifiers that connect to the GenAI Observability traces we explored in Step 5:

- Each request generates a unique `traceId` for end-to-end tracking
- Session IDs link multiple requests within a conversation
- Request IDs enable correlation across distributed components
- These identifiers create a complete observability story across metrics, logs, and traces

*[Screenshot placeholder: Log entry showing traceId and sessionId fields]*

---

## Step 8: Enable Security Auditing with CloudTrail

AWS CloudTrail provides comprehensive auditing of all API calls made to your AgentCore Runtime. This creates an immutable audit trail essential for security, compliance, and operational excellence.

### Understanding CloudTrail for AgentCore

CloudTrail automatically records every API interaction with your AgentCore resources, capturing:

- **Identity** - The user, role, or service that made the request
- **Action** - The specific API operation performed
- **Timestamp** - Precise time when the action occurred
- **Source** - IP address and user agent information
- **Result** - Success or failure status with error details

*[Screenshot placeholder: CloudTrail console showing AgentCore events]*

### Key AgentCore Runtime Events in CloudTrail

CloudTrail captures these critical Runtime API events:

**Deployment and Management Events:**
- `CreateRuntime` - Records when your agent is initially deployed
- `UpdateRuntime` - Tracks all configuration changes to your agent
- `DeleteRuntime` - Documents agent removal for compliance
- `GetRuntime` - Monitors who retrieves agent configuration

**Invocation Events:**
- `InvokeAgentRuntime` - Captures every customer interaction with your agent
- Includes session identifiers, user identity, and request metadata
- Enables usage analytics and billing reconciliation

**Security Events:**
- Authentication attempts (successful and failed)
- Authorization decisions and denials
- JWT token validation events from your Cognito integration

*[Screenshot placeholder: CloudTrail event detail for InvokeAgentRuntime]*

### Setting Up CloudTrail for Your Agent

If CloudTrail isn't already enabled in your account:

1. **Create a Trail**
   - Navigate to AWS CloudTrail Console
   - Click **Create trail**
   - Name: `AgentCore-Audit-Trail`
   - Choose to log both management and data events

2. **Configure Event Selectors**
   - Add AgentCore as a data event source
   - Select both read and write events
   - Choose your S3 bucket for secure log storage

*[Screenshot placeholder: CloudTrail configuration for AgentCore]*

### Analyzing Agent Usage with CloudTrail

CloudTrail Event History enables powerful analytics:

**Usage Pattern Analysis:**
- Identify your most active users and their interaction patterns
- Discover peak usage times for capacity planning
- Understand geographic distribution of your user base

**Security Monitoring:**
- Detect failed authentication attempts that may indicate attacks
- Monitor for unauthorized access patterns
- Track privilege escalation attempts

**Compliance Auditing:**
- Maintain complete audit trail for regulatory requirements
- Demonstrate proper access controls and data handling
- Generate user activity reports for compliance officers

*[Screenshot placeholder: CloudTrail Event History filtered for AgentCore]*

### Creating Security Alerts

Proactive security requires automated alerting:

1. **Unauthorized Access Alert**
   - Triggers when authentication failures exceed normal threshold
   - Immediately notifies security team for investigation

2. **Unusual Activity Detection**
   - Identifies abnormal invocation patterns or volumes
   - Flags potential security incidents or abuse

3. **Configuration Change Notification**
   - Alerts when Runtime configuration is modified
   - Ensures proper change management procedures

*[Screenshot placeholder: CloudWatch alarm for unauthorized access attempts]*

---

## Step 9: Bringing It All Together - Unified Observability

Now let's combine metrics, logs, and CloudTrail data to create a complete observability solution for your production agent.

### Creating a Comprehensive Monitoring Strategy

Your three pillars of observability work together:

**Performance Monitoring (Metrics)**
- Real-time visibility into invocation rates and latency trends
- Proactive monitoring of error rates and throttling events
- Capacity planning through session analysis

**Operational Insights (Logs)**
- Deep debugging of specific customer issues
- Pattern analysis across conversations
- Performance optimization opportunities

**Security and Compliance (CloudTrail)**
- Complete audit trail of all API activity
- Access pattern monitoring and anomaly detection
- Regulatory compliance documentation

*[Screenshot placeholder: Unified dashboard combining metrics, logs, and CloudTrail widgets]*

### Practical Troubleshooting Workflow

Let's walk through a real scenario - investigating a customer complaint about slow responses:

1. **Start with Metrics**
   - Review the Latency metric for the reported time period
   - Identify any spikes or anomalies in response times
   - Note exact timestamps for detailed investigation

2. **Dive into Logs**
   - Query Logs Insights for the identified time window
   - Locate the specific slow requests
   - Analyze the root cause (tool timeouts, memory retrieval delays, model latency)

3. **Verify with CloudTrail**
   - Confirm the identity of users experiencing issues
   - Check for any permission or authentication problems
   - Validate proper token usage and session management

4. **Cross-reference with Traces**
   - Use the trace ID from logs to access GenAI Observability
   - View the complete request flow across all components
   - Identify specific bottlenecks in your agent pipeline

*[Screenshot placeholder: Multi-panel view showing metrics, logs, and traces for troubleshooting]*

### Best Practices for Production Monitoring

**Set Meaningful Alerts:**
- Latency exceeding SLA thresholds
- Error rates above acceptable levels
- Unusual traffic patterns or volumes

**Create Actionable Dashboards:**
- Business metrics (requests per customer, session duration)
- Technical metrics (p50/p90/p99 latencies, error distributions)
- Security metrics (authentication failures, API usage by user)

**Establish Runbooks:**
- Document common issues and resolutions
- Create step-by-step troubleshooting guides
- Define escalation procedures

---

## Key Takeaways

After completing these observability steps, you now have:

✅ **Real-time Performance Monitoring** - CloudWatch metrics continuously track your agent's health and performance

✅ **Detailed Debugging Capability** - CloudWatch Logs provide deep insights into every aspect of agent behavior

✅ **Complete Security Audit Trail** - CloudTrail ensures all API activity is recorded for security and compliance

✅ **Unified Observability Platform** - Integrated view across metrics, logs, and traces enables rapid issue resolution

Your production agent now operates with full transparency, enabling you to maintain high performance, quickly resolve issues, and meet security compliance requirements.

---

## What's Next?

With your agent successfully deployed to production with comprehensive observability, you're ready for Lab 5 where you'll build a user-friendly interface that allows customers to interact naturally with your intelligent support agent!