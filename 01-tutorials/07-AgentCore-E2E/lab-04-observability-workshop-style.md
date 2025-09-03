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

### 4.1 Monitor Runtime Performance

Your agent publishes performance metrics to CloudWatch. Let's see how busy your customer support agent is and how well it's performing.

**Use Case**: *"How many customers are using my agent today? Are they getting fast responses?"*

#### Finding Your Agent Metrics

1. **Navigate to CloudWatch**
   - Open AWS Console → CloudWatch → Metrics → All metrics
   - Find namespace: **AWS/Bedrock-AgentCore**

*[Screenshot placeholder: CloudWatch metrics browser showing AWS/Bedrock-AgentCore namespace]*

2. **Search for Your Agent**
   - Use the search bar to find your Runtime ARN from Step 3
   - Or search: `customer_support_agent`

*[Screenshot placeholder: Search results showing your agent metrics]*

#### Key Metrics Dashboard

Create a simple dashboard to track your agent's health:

**Invocations** - *"How busy is my agent?"*
- Shows total customer queries
- Helps identify peak usage times

**Latency** - *"How fast are my responses?"*
- Average response time from question to answer
- Target: Keep under 10 seconds for good customer experience

**UserErrors** - *"What's going wrong?"*
- Failed requests due to invalid input or permissions
- High numbers indicate user interface or authentication issues

*[Screenshot placeholder: Simple 3-widget dashboard showing Invocations, Latency, and UserErrors]*

---

### 4.2 Analyze Memory Operations

Your agent uses memory to remember customer context. Let's monitor how well memory retrieval is performing.

**Use Case**: *"Why is my agent slow to remember what customers said earlier?"*

#### Key Memory Metric

**RetrieveMemoryRecords** - *"How long does context lookup take?"*
- Measures time to find relevant conversation history
- Slow retrieval = slower agent responses
- Target: Keep under 2 seconds

#### Quick Setup

1. In CloudWatch Metrics, search for your Memory ARN
2. Select: **RetrieveMemoryRecords Latency**
3. Set Statistic to **Average**
4. Add to your dashboard

*[Screenshot placeholder: RetrieveMemoryRecords metric graph showing latency over time]*

---

### 4.3 Track Tool Execution

Your agent calls tools through the Gateway. Let's see which tools are performing well and which need optimization.

**Use Case**: *"My agent calls tools to help customers, but some seem slow. Which ones need fixing?"*

#### Key Gateway Metrics

**TargetExecutionTime** - *"How long do my tools take to run?"*
- Actual execution time for Lambda functions or APIs
- Compare different tools to find bottlenecks

**CallToolMcp Invocations** - *"Which tools are used most?"*
- Shows tool popularity and usage patterns

#### Performance Comparison

1. Search for your Gateway ARN in CloudWatch Metrics
2. Add **TargetExecutionTime** with **Average** statistic
3. Compare different tools by filtering Operation dimension

*[Screenshot placeholder: Bar chart comparing execution times across different tools]*

---

### 4.4 Debug with Logs

When customers report issues, use CloudWatch Logs to investigate what happened during their conversation.

**Scenario 1**: *"Customer says agent response was very slow"*

1. **Navigate to Logs**
   - CloudWatch → Logs → Log groups
   - Find: `/aws/bedrock-agentcore/runtimes/{your-runtime-id}-DEFAULT`

*[Screenshot placeholder: CloudWatch Logs groups list showing Runtime logs]*

2. **Search for Slow Responses**
   - Go to Logs Insights
   - Query logs during the customer's session time
   - Look for high latency entries

*[Screenshot placeholder: Logs Insights query showing slow response entries]*

**Scenario 2**: *"Agent gave wrong answer to customer question"*

1. **Find Customer Session**
   - Use session ID or timestamp from customer complaint
   - Follow complete conversation flow in logs

2. **Analyze Agent Reasoning**
   - Check which tools were called
   - Verify memory retrieval results
   - Review model response generation

*[Screenshot placeholder: Log entries showing agent reasoning flow for a specific session]*

---

### 4.5 Security Auditing

Track who's using your agent and ensure secure access with CloudTrail.

**Use Case**: *"I need to show compliance officers who accessed the agent and when"*

#### Viewing Agent Access

1. **Open CloudTrail Console**
   - AWS Console → CloudTrail → Event history

*[Screenshot placeholder: CloudTrail console event history view]*

2. **Filter for Your Agent**
   - Search for event name: **InvokeAgentRuntime**
   - Filter by your Runtime ARN
   - View user identity and access times

*[Screenshot placeholder: CloudTrail events filtered for agent invocations]*

#### Key Information Available

**Who**: User identity from authentication tokens
**When**: Precise timestamps of each interaction  
**What**: API calls made (create, invoke, update, delete)
**Result**: Success or failure status

*[Screenshot placeholder: CloudTrail event detail showing user identity and action details]*

---

### Key Takeaways - Production Monitoring

✅ **Real-time Visibility**: CloudWatch metrics show agent performance and usage

✅ **Deep Debugging**: CloudWatch Logs help solve customer-specific issues

✅ **Memory Optimization**: Track context retrieval performance

✅ **Tool Performance**: Monitor which tools need optimization

✅ **Security Compliance**: Complete audit trail of agent access

Your agent now has comprehensive monitoring to ensure great customer experience and meet compliance requirements!

---

### What's Next?

Your production agent is fully monitored and observable. In Lab 5, you'll build a beautiful web interface so customers can easily chat with your intelligent support agent!