## 4.4 AgentCore Observability - CloudWatch Logs

CloudWatch Logs capture detailed events from your AgentCore customer support system. These structured JSON logs provide visibility into memory processing, tool execution, and agent operations for troubleshooting and performance analysis.

---

### Memory Logs - Setup and Navigation

**Enable Memory Log Delivery:**

1. **Navigate to your Memory resource** in the AWS Console:
   - Go to Amazon Bedrock AgentCore → Memory → **CustomerSupportMemory** (created in Lab 2)

2. **Configure Log Delivery:**
   - In the **Observability** section, find **Log delivery**
   - Click **Add** to create a new log delivery configuration
   - Select **Log type**: `APPLICATION_LOGS`
   - **Destination log group**: `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/CustomerSupportMemory-xxxxxxxxxxxx`
     
     *Note: The log group includes an auto-generated ID suffix unique to your Memory resource.*
   - Click **Add** to enable log delivery

   ![Memory Log Delivery Configuration](images/Configure_log_delivery_for_Memory.png)

3. **Access Memory Logs in CloudWatch:**
   - Navigate to **CloudWatch** → **Logs** → **Log groups**
   - Find the log group: `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/CustomerSupportMemory-[auto-generated-ID]`
   - Click to open: **BedrockAgentCoreMemory_ApplicationLogs**

### Understanding Memory Log Structure

Memory logs provide detailed insight into background processing operations. Each log entry contains structured JSON with the following key fields:

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

| Field | Purpose |
|-------|--------|
| `resource_arn` | Memory resource identifier |
| `event_timestamp` | When the operation occurred |
| `memory_strategy_id` | Strategy type (`CustomerPreferences`, `CustomerSupportSemantic`) |
| `namespace` | Customer/context organization (`support/customer/{id}/{type}`) |
| `actor_id` | Customer identifier |
| `session_id` | Links operations to conversations |
| `body.log` | Human-readable operation description |
| `body.requestId` | Correlation ID for request tracking |
| `body.isError` | Success/failure flag |

### Memory Processing Workflow

Memory operations follow a three-phase pipeline visible in the logs:

1. **Extraction** - Convert conversations to structured memories
   - `"Processing extraction input"` → `"Extraction completed in {time} ms"`

2. **Consolidation** - Merge with existing memories
   - `"Retrieving memories"` → `"Consolidating X facts with Y related memories"`

3. **Storage** - Update memory store
   - `"Performing UPDATE operation"` → `"Succeeded to update X records"`

**Memory Strategies:**
- `CustomerPreferences` - User preferences and settings
- `CustomerSupportSemantic` - Conversation context and technical details

### Memory Log Use Cases

- **Performance**: Track extraction/consolidation timing and success rates
- **Debugging**: Find failed operations using `isError` flag and trace record lifecycle
- **Analytics**: Monitor memory growth patterns and strategy effectiveness

---

### Gateway Logs - Setup and Navigation

**Enable Gateway Log Delivery:**

1. **Navigate to your Gateway resource** in the AWS Console:
   - Go to Amazon Bedrock AgentCore → Gateways → **customersupport-gw** (created in Lab 3)

2. **Configure Log Delivery:**
   - In the **Observability** section, find **Log delivery**
   - Click **Add** to create a new log delivery configuration
   - Select **Log type**: `APPLICATION_LOGS`
   - **Destination log group**: `/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/customersupport-gw-xxxxxxxxxxxx`
     
     *Note: The log group includes an auto-generated ID suffix unique to your Gateway resource.*
   - Click **Add** to enable log delivery

   ![Gateway Log Delivery Configuration](images/Configure_log_delivery_for_Gateway.png)

3. **Access Gateway Logs in CloudWatch:**
   - Navigate to **CloudWatch** → **Logs** → **Log groups**
   - Find the log group: `/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/customersupport-gw-[auto-generated-ID]`
   - Click to open: **BedrockAgentCoreGateway_ApplicationLogs**

### Understanding Gateway Log Structure

Gateway logs capture MCP protocol operations and tool executions:

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

| Field | Purpose |
|-------|--------|
| `resource_arn` | Gateway resource identifier |
| `event_timestamp` | Operation timing |
| `body.id` | Sequential request ID within session |
| `body.log` | Human-readable operation description |
| `body.isError` | Success/failure flag |
| `request_id` | Correlation ID for request tracking |

### Gateway MCP Protocol Workflow

Tool execution follows this sequence in the logs:

1. **Initialize**: `"Received request for initialize method"`
2. **Discover**: `"Received request for tools/list method"`
3. **Execute**: `"Executing tool LambdaUsingSDK___[tool_name] from target [ID]"`

**Tool Pattern**: `LambdaUsingSDK___check_warranty_status` or `LambdaUsingSDK___web_search`

### Gateway Performance Analysis

- **Calculate timing**: Use `event_timestamp` differences between start/completion logs
- **Track requests**: Use `request_id` for end-to-end tracing
- **Monitor patterns**: Sequential `body.id` shows operation order within sessions

### Gateway Log Use Cases

- **Performance**: Identify slow tools using timestamp analysis
- **Debugging**: Verify MCP protocol sequences and debug failures using `isError`
- **Analytics**: Track tool usage frequency and execution patterns

---


![Memory Log Delivery Configuration](images/Configure_log_delivery_for_Memory.png)