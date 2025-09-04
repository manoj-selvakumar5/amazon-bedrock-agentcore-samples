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

- **Protocol Health:** MCP initialization and discovery working correctly for your Lab 3 setup
- **Tool Availability:** All workshop tools are properly registered and discoverable
- **Execution Success:** Customer warranty requests are successfully routed to your Lambda function
- **Traceability:** Complete request correlation from agent query to tool execution

### Practical Gateway Log Use Cases

**1. Tool Performance Monitoring**
```
Target: Identify slow-executing tools in your workshop deployment
Monitor: Tool execution timing, Lambda cold starts, timeout patterns
Alert: When tools consistently >2000ms or show increasing latency trends
```

**2. MCP Protocol Debugging**  
```
Target: Verify Lab 3 gateway configuration is working correctly
Monitor: Initialization success, tool discovery completion, execution patterns
Debug: Failed tool calls, missing tools, or protocol errors
```

**3. Workshop Tool Usage Analytics**
```
Target: Understand which Lab 3 tools customers use most frequently  
Monitor: check_warranty_status vs web_search vs get_product_info usage
Optimize: Tool caching strategies and Lambda concurrency settings
```

