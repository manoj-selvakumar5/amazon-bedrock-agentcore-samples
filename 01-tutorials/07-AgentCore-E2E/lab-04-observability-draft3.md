### Step 4: AgentCore Observability

[**AgentCore Observability**](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) delivers powerful monitoring, tracing, and debugging capabilities for AI agents. It automatically emits telemetry in the standardized **OpenTelemetry (OTEL)** format, enabling seamless integration with existing observability tools. Through **Amazon CloudWatch** dashboards, teams gain real-time visibility into agent workflows with filtering, metadata tagging, and step-by-step visualizations of execution paths and intermediate outputs—making it easier to detect and resolve performance bottlenecks or failures. 

All telemetry data such as metrics, logs, and spans are centrally stored in CloudWatch, including a dedicated **Generative AI observability dashboard** that provides trace visualizations, custom span graphs, and error breakdowns. In addition, **AWS CloudTrail** captures and records all API-level interactions across AgentCore components, creating a complete audit trail that supports troubleshooting, security, and compliance.

This foundation establishes multiple layers of production-grade observability:

1. **Generative AI Observability Dashboard** – A CloudWatch console view purpose-built for AI agents, offering real-time metrics, session analytics, trace visualizations, and error breakdowns for rapid diagnosis and optimization.
2. **CloudWatch Metrics** – Automatically published indicators such as invocations, latency, duration, sessions, and error rates for Runtime, Memory, and Gateway, powering dashboards, alerts, and trend analysis.
3. **CloudWatch Logs** – Structured, time-stamped logs (including span and event records) that support detailed troubleshooting and forensic analysis.
4. **AWS CloudTrail** – An immutable record of control-plane and data-plane API activity—capturing who did what, when, and from where—to enhance security monitoring and compliance.

Now that your agent is deployed to the **AgentCore Runtime** and integrated with **Memory** and **Gateway**, let’s explore each observability layer in detail.

## 4.1 AgentCore's Built-in Observability Dashboard
The CloudWatch GenAI Observability dashboard is the primary view for day-to-day monitoring, offering immediate insights into agent activity, sessions, and traces without requiring additional setup.

By default, AgentCore forwards agent traces to **CloudWatch GenAI Observability**. To view them, open CloudWatch → GenAI Observability → Bedrock AgentCore. From here you can review agent activity, drill into sessions, and open traces for detailed analysis.

### Agents view

![Agents Overview on CloudWatch](images/observability_agents.png)

The **Agents view** gives a high-level snapshot of all deployed agents. It’s the first stop when you want to understand how your agents are behaving in production.

- **Summary metrics**: total sessions, traces, errors, and throttles across agents.
- **Runtime metrics**: aggregate KPIs for all agents, including session counts, invocations, errors, throttles, and latency trends, displayed with time-series graphs to highlight spikes or anomalies.
- **Per-agent breakdown**: a detailed table showing sessions, traces, errors, throttles, and P95 span latency for each agent, enabling comparisons across multi-agent deployments.

Together, these views let you track **traffic patterns, error trends, and performance at both the account and individual agent level**, making the Agents view the starting point for monitoring overall agent health.


### Sessions

The Sessions view shows the list of all the sessions associated with all agents in your account, with filters and drill‑downs that make it easy to investigate behavior for a specific session.

![Sessions Overview](images/sessions_lab5_observability.png)

* **Session listing**: Displays all agent conversation sessions with sortable columns for session ID, trace count, errors, throttles, and P95 latency.
* **Session detail navigation**: Click any session ID to open a dedicated dashboard that shows per-session metrics (latency, errors, span count)
* **Trace a conversation end‑to‑end** by jumping from the session to its associated traces and spans
* **Session comparison**: Easily spot anomalies by comparing sessions—such as high latency, repeated tool failures, or unusually long conversations.

In this view, you gain insights into the full **lifecycle and outcome** of each session, **engagement patterns**, **context usage** (e.g., memory interactions like `RetrieveMemoryRecords`), and **tool utilization** (which Gateway tools were invoked). It serves as your workspace for diagnosing conversation-specific performance and behavior.


### Traces view

The **Traces view** offers a focused lens into the internal execution path of each request processed by your agents. It’s the go-to place for understanding how individual requests unfold operationally.


![Traces Overview](images/traces_lab4_observability.png)

* **Trace listing**: Displays all recorded agent traces for your account, with sortable columns for trace ID, span count, errors, and latency—letting you quickly identify slow or failing requests. 
* **Filtering & sorting**: Easily narrow down traces using filters (e.g., latency, status, attributes) or sort by columns to prioritize analysis.
* **Drill-in analytics**: Use the **Actions** menu to open **Logs Insights** for contextual logs.
* **Execution detail**: Each trace reveals the full execution flow—spans representing discrete operations, tool invocations, and internal decision points—helping visualize the end-to-end request journey. 

These features enable you to **trace every step of an agent’s request**, pinpoint latency bottlenecks, uncover error patterns, and gain a granular understanding of runtime behavior.




## 4.2 AgentCore Observability Metrics

AgentCore automatically publishes **built-in observability metrics** for all primitives Runtime, Memory, and Gateway to **Amazon CloudWatch** under the namespace `AWS/Bedrock-AgentCore`. These metrics give you real-time visibility into request activity, latency, error rates, session usage, and performance. You can use them to build dashboards, configure alarms, and analyze trends for production operations.


### Navigating to AgentCore Metrics in CloudWatch

1. **Open CloudWatch Console**
   - Navigate to the **CloudWatch** service in the AWS Console.
   - Select **Metrics** from the left navigation panel.
   - Click **All metrics**.

2. **Locate AgentCore Metrics**
   - In the metrics browser, select the namespace **AWS/Bedrock-AgentCore**.
   - Explore the available dimension combinations for each resource type.

3. **Filter by Resource**
   - Use the search bar to enter the ARN or name of your resource.
   - Examples: `customer_support_agent`, `CustomerSupportMemory`, or `customersupport-gw`.

### Runtime Metrics

Runtime metrics capture how your agent handles requests in production and how users experience responsiveness.

**Key Metrics to Monitor**
- **Invocations** – Total requests received by the agent, showing usage and peak load periods.
- **Latency** – End-to-end response time (request to final token), including model inference, memory lookups, and tool execution.
- **Sessions** – Number of active agent sessions, useful for capacity planning and engagement analysis.
- **User Errors** – Invalid requests (400), missing resources (404), or permission errors (403).
- **System Errors** – Internal service errors (500) that may indicate infrastructure issues.
- **Throttles** – Requests rejected due to TPS or quota limits (429).

**[placeholder for screenshot]**

### Memory Metrics

Memory metrics measure how efficiently the agent stores and retrieves conversation context, and how background processing maintains long-term memory quality over time.

**Key Metrics to Monitor**
- **Latency** – End-to-end processing time for memory operations.  
- **Invocations** – Total number of API requests to the Memory service.  
- **System Errors** – Memory API calls that failed with AWS server-side errors (5xx).  
- **User Errors** – Memory API calls that failed with client-side errors (4xx).  
- **Errors** – Total errors across control-plane and data-plane operations, including ingestion failures.  
- **Throttles** – Requests throttled (429), not counted as invocations or errors.  
- **Creation Count** – Number of new memory events and records created.  

**[placeholder for screenshot]**


### Gateway Metrics

Gateway metrics provide visibility into tool execution, MCP operations, and request distribution across targets.

**Key Metrics to Monitor**
- **Invocations** – Total requests made to Gateway data plane APIs.   
- **Latency** – Time from receiving a request until the first response token is sent.  
- **Duration** – Full end-to-end request time until the final response token is sent.  
- **TargetExecutionTime** – Time taken by the target (Lambda, API) to execute, excluding Gateway overhead.  
- **TargetType** – Distribution of requests served by target type (MCP, Lambda, OpenAPI).  
- **System Errors (5xx)** – Requests that failed due to server-side issues.  
- **User Errors (4xx)** – Requests that failed due to client errors (excluding throttles). 
- **Throttles (429)** – Requests throttled due to exceeded limits.  

**[placeholder for screenshot]**

### Best Practices for Metrics
- **Dashboards** – Combine Runtime, Memory, and Gateway metrics in a single CloudWatch dashboard.  
- **Alarms** – Configure CloudWatch Alarms for high latency, error rates, or throttling.  
- **Trends** – Monitor growth in `CreationCount` and Sessions to anticipate scaling needs.  
- **Correlation** – Combine metrics with spans and logs for deep troubleshooting.  

With these metrics in CloudWatch, you have baseline observability across AgentCore resources, enabling real-time monitoring and proactive alerting.

## 4.4 AgentCore Observability Logs

CloudWatch Logs capture detailed, time‑stamped events across AgentCore components. These structured JSON logs provide visibility into agent operations, background processing, and system behavior for deep troubleshooting and performance analysis.

Now that you have built a customer support agent system across Labs 1-4 with local tools (Lab 1), enhancing it with persistent memory for conversation context and personalization (Lab 2), integrating with AgentCore Gateway to centrally manage shared tools and secure authentication (Lab 3), and deploying to AgentCore Runtime for production-ready auto-scaling with observability (Lab 4)—let's explore the detailed logs each component generates to help you monitor and debug your production agent system.

### Memory Logs - Setup and Navigation

Memory logs capture the background processing operations that occur when your customer support agent (from Lab 1) stores and retrieves conversation context using the Memory resource you created in Lab 2. These logs provide deep insight into how AgentCore extracts, consolidates, and persists customer preferences and conversation context.

**Enable Memory Log Delivery:**

1. **Navigate to your Memory resource** from Lab 2:
   - Go to Amazon Bedrock AgentCore → Memory → **CustomerSupportMemory**

2. **Configure Log Delivery:**
   - In the **Observability** section, find **Log delivery**
   - Click **Add** → Select **Log type**: `APPLICATION_LOGS`
   - **Destination log group**: `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/CustomerSupportMemory-xxxxxxxxxxxx`
   
   > The log group name includes an automatically generated ID suffix (like `CustomerSupportMemory-WcEhTTFp10`) unique to your Memory resource.

3. **Access Memory Logs in CloudWatch:**
   - Navigate to **CloudWatch** → **Logs** → **Log groups**
   - Find: `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/CustomerSupportMemory-[auto-generated-ID]`
   - Click to open: **BedrockAgentCoreMemory_ApplicationLogs**

### Understanding Memory Processing

When customers interact with your agent, AgentCore Memory processes conversations through a **three-phase pipeline**:

**1. Extraction** → Convert conversation events to structured memories  
**2. Consolidation** → Merge new memories with existing ones to avoid duplication  
**3. Storage** → Persist consolidated memories to the memory store

Each phase generates detailed logs that help you monitor performance, debug issues, and understand memory behavior.

### Memory Log Structure and Analysis

**Sample Memory Log Entry:**
```json
{
  "resource_arn": "arn:aws:bedrock-agentcore:<region>:<account-id>:memory/CustomerSupportMemory-ID",
  "event_timestamp": 1756957336547,
  "memory_strategy_id": "CustomerPreferences-EH93NK8WlQ", 
  "namespace": "support/customer/customer_001/preferences",
  "actor_id": "customer_001",
  "session_id": "7e68e007-8675-464d-864b-db6c97b2a078",
  "body": {
    "log": "Processing extraction input",
    "requestId": "58bc9c8c-4e84-40b6-bcf3-1161866443bb",
    "isError": false
  }
}
```

**Key Fields Explained:**

| Field               | Description                                                                                   |
|---------------------|-----------------------------------------------------------------------------------------------|
| **resource_arn**    | ARN of the Memory resource—useful for filtering and distinguishing events across multiple memory resources. |
| **event_timestamp** | Timestamp (in milliseconds) indicating when the memory operation occurred.              |
| **memory_strategy_id** | Identifier of the memory strategy (e.g., `CustomerPreferences`, `CustomerSupportSemantic`)—lets you distinguish processing logic. |
| **namespace**       | Logical path (such as support/customer/{customer_id}/{type}) that organizes and separates memory data for each context, user, session, or memory type. |
| **actor_id**        | Identifier of the user or agent actor (e.g., `customer_001`) that helps attribute operations to individuals or systems.    |
| **session_id**      | Identifier linking memory operations to a specific conversation session, enabling end-to-end traceability. |
| **body.log**        | Human-readable log message describing the current operation step—useful during extraction or consolidation. |
| **body.requestId**  | Unique identifier correlating related memory operations—useful for tracing a single memory workflow. |
| **body.isError**    | Boolean flag (`true` or `false`) indicating whether the operation encountered an error.         |



### Complete Memory Processing Example

Let's trace a real memory processing workflow. When `customer_001` interacts with your agent about laptop preferences, you'll see this complete sequence in CloudWatch Logs:

```json
{"log": "Processing extraction input"}
{"log": "Starting to process Preference strategies."}
{"log": "Extraction completed in 1674 ms"}
{"log": "Extracted 1 memories"}
{"log": "Processing consolidation input"}
{"log": "Retrieving memories."}
{"log": "Succeeded to retrieve 2 records."}
{"log": "1 memories require consolidation."}
{"log": "Consolidating 2 facts with 3 related memories"}
{"log": "Succeeded to upsert 1 records."}
{"log": "Succeeded operation for record id mem-af46dbb9..."}
```

**What This Sequence Reveals:**

1. **Extraction Timing**
   - The log shows `Extraction completed in 1674 ms`.
   - That's ~1.6s latency for converting the raw conversation into structured memory.
   - If you consistently saw higher numbers here (e.g., >3000 ms), you'd flag this as a potential bottleneck.

2. **New Memory Created**
   - `Extracted 1 memories` confirms only one new record was generated for this interaction.
   - This tells you the preference strategy was triggered correctly and produced new data.

3. **Consolidation Behavior**
   - Logs show `Succeeded to retrieve 2 records.` and `1 memories require consolidation.`
   - This means the system correctly pulled existing records and determined overlap, then merged facts (`Consolidating 2 facts with 3 related memories`).
   - This is critical for **avoiding duplication** and ensuring the agent doesn't keep multiple conflicting memories for the same customer.

4. **Successful Storage**
   - `Succeeded to upsert 1 records.` followed by a record ID confirms the memory store was updated.
   - That's the final confirmation the lifecycle completed successfully.

**What This Observation Tells You**

- **Performance:** Extraction + consolidation pipeline took ~1.6s, which is reasonable but worth monitoring under load.
- **Correctness:** Strategies (`CustomerPreferences`) are firing as expected, producing new memory records.
- **Data Integrity:** Consolidation ensures that the memory store stays consistent and avoids bloat.
- **Traceability:** Because you have the `session_id` and `requestId`, you can trace this specific customer's memory lifecycle end-to-end.




### Gateway Logs - Setup and Navigation

Gateway logs capture the MCP (Model Context Protocol) operations that occur when your customer support agent (from Lab 1) uses the centralized tools you configured in Lab 3. These logs provide detailed insight into how AgentCore Gateway manages tool discovery, execution, and performance for the `check_warranty_status`, `web_search`, and `get_product_info` tools.

**Enable Gateway Log Delivery:**

1. **Navigate to your Gateway resource** from Lab 3:
   - Go to Amazon Bedrock AgentCore → Gateways → **customersupport-gw**

2. **Configure Log Delivery:**
   - In the **Observability** section, find **Log delivery**
   - Click **Add** → Select **Log type**: `APPLICATION_LOGS`
   - **Destination log group**: `/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/customersupport-gw-xxxxxxxxxxxx`
   
   > The log group name includes an automatically generated ID suffix (like `customersupport-gw-dcbgswzb5p`) unique to your Gateway resource.

3. **Access Gateway Logs in CloudWatch:**
   - Navigate to **CloudWatch** → **Logs** → **Log groups**
   - Find: `/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/customersupport-gw-[auto-generated-ID]`
   - Click to open: **BedrockAgentCoreGateway_ApplicationLogs**

### Understanding Gateway Processing

When customers interact with your agent, AgentCore Gateway processes tool requests through a **four-phase MCP protocol**:

**1. Initialization** → Establish MCP connection with the gateway  
**2. Discovery** → Enumerate available tools for the agent  
**3. Execution** → Invoke specific tools (warranty check, web search, etc.)  
**4. Correlation** → Track multiple tool calls within the same session

Each phase generates detailed logs that help you monitor tool performance, debug MCP issues, and understand tool usage patterns.

### Gateway Log Structure and Analysis

**Sample Gateway Log Entry:**
```json
{
  "resource_arn": "arn:aws:bedrock-agentcore:<region>:<account-id>:gateway/customersupport-gw-ID",
  "event_timestamp": 1756958992250,
  "body": {
    "id": "2",
    "log": "Received request for tools/call method",
    "isError": false
  },
  "account_id": "<account-id>",
  "request_id": "b2474cdc-b5dd-44b0-876d-8de900414ee3"
}
```

**Key Fields Explained:**

| Field               | Description                                                                                   |
|---------------------|-----------------------------------------------------------------------------------------------|
| **resource_arn**    | ARN of the Gateway resource—useful for filtering logs across multiple gateway instances. |
| **event_timestamp** | Timestamp (in milliseconds) indicating when the gateway operation occurred.              |
| **body.id**         | Sequential request identifier within the gateway session for tracking operation order. |
| **body.log**        | Human-readable operation description detailing MCP protocol interactions. |
| **body.isError**    | Boolean flag (`true` or `false`) indicating whether the operation encountered an error. |
| **account_id**      | AWS account identifier for multi-account deployments. |
| **request_id**      | Unique correlation ID linking gateway operations to agent requests—enables end-to-end tracing. |


### Complete Gateway Processing Example

Let's trace a real tool execution workflow. When a customer asks your agent "Can you check the warranty on my laptop?", you'll see this complete MCP sequence in CloudWatch Logs:

```json
{"log": "Started processing request with requestId: 0"}
{"log": "Received request for initialize method"}
{"log": "Successfully processed request with requestId: 0"}
{"log": "Started processing request with requestId: 1"}
{"log": "Received request for tools/list method"}
{"log": "Successfully processed request with requestId: 1"}
{"log": "Started processing request with requestId: 2"}
{"log": "Received request for tools/call method"}
{"log": "Executing tool LambdaUsingSDK___check_warranty_status from target ME2UI4BINR"}
{"log": "Successfully processed request with requestId: 2"}
```

**What This Sequence Reveals:**

1. **MCP Initialization**
   - `Received request for initialize method` confirms proper gateway connection
   - Request ID 0 shows this is the first operation in the session
   - Successful completion enables subsequent tool operations

2. **Tool Discovery**
   - `Received request for tools/list method` shows agent querying available tools
   - Gateway provides the list of Lab 3 tools: `check_warranty_status`, `web_search`, `get_product_info`
   - Request ID 1 maintains proper sequencing

3. **Tool Execution**
   - `Received request for tools/call method` indicates specific tool invocation
   - `Executing tool LambdaUsingSDK___check_warranty_status` shows which Lab 3 tool is running
   - `from target ME2UI4BINR` identifies the specific Lambda function you deployed

4. **Performance Tracking**
   - Request IDs (0→1→2) show proper sequential processing
   - Timestamp analysis reveals tool execution latency
   - `Successfully processed` confirms no errors in the MCP protocol

**What This Observation Tells You**

- **Protocol Validation:** MCP initialization and discovery working correctly for your Lab 3 setup
- **Tool Availability:** All workshop tools are properly registered and discoverable
- **Execution Success:** Customer warranty requests are successfully routed to your Lambda function


