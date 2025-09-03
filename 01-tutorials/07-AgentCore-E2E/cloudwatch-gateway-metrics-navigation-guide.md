# CloudWatch Navigation Guide: AgentCore Gateway Metrics

## Complete Step-by-Step Console Navigation for Gateway

This guide provides detailed instructions for analyzing AgentCore Gateway metrics in the AWS CloudWatch console, with focus on tool performance and MCP operations.

---

## 🚀 Starting from AWS Console

### Step 1: Access CloudWatch

1. **Log into AWS Console**
   - Go to https://console.aws.amazon.com
   - Sign in with your AWS credentials
   - Select the correct region (e.g., `us-east-1`)

2. **Navigate to CloudWatch**
   - In the AWS services search bar, type "CloudWatch"
   - Click on "CloudWatch" service
   - Or use direct URL: `https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1`

3. **Access Metrics**
   - In the left sidebar, click **"Metrics"**
   - Click **"All metrics"** tab
   - You'll see the main metrics browser

---

## 🔍 Finding AgentCore Gateway Metrics

### Step 2: Locate the Namespace

1. **Search for AgentCore Namespace**
   - In the namespace section, look for **`AWS/Bedrock-AgentCore`**
   - Or type `Bedrock-AgentCore` in the search box
   - Click on the namespace when it appears

2. **Alternative: Browse Method**
   - Scroll through the "AWS Services" section
   - Look for **`AWS/Bedrock-AgentCore`**
   - This namespace contains all AgentCore metrics (Memory, Gateway, Runtime)

---

## 🎯 Searching with Gateway ARN

### Step 3: Filter by Your Gateway Resource

1. **Get Your Gateway ARN**
   ```
   arn:aws:bedrock-agentcore:us-east-1:533267284022:gateway/customersupport-gw-dcbgswzb5p
   ```
   *(Replace with your actual Gateway ARN from Lab 3)*

2. **Use the Search Bar**
   - Look for the search box: "Search for any metric, dimension, resource id or account id"
   - Paste your Gateway ARN or just the Gateway ID: `customersupport-gw-dcbgswzb5p`
   - Press Enter

3. **Understanding Gateway Search Results**
   - **Browse (42)** - Shows total available metric combinations for your gateway
   - You'll see dimension combinations like:
     - **"Bedrock-AgentCore > Name, Operation, Resource"** (16 metrics)
     - **"Bedrock-AgentCore > Operation, Resource"** (26 metrics)

---

## 📊 Gateway-Specific Dimension Combinations

### Step 4: Choose the Right Dimensions for Gateway Analysis

#### **Option 1: MCP Operation Analysis** ⭐ **Most Important**
- Click: **"Bedrock-AgentCore > Operation, Resource"** (26 metrics)
- Shows metrics for MCP operations like CallToolMcp, InitializeMcp
- Best for analyzing tool execution performance

#### **Option 2: Named Tool Analysis**
- Click: **"Bedrock-AgentCore > Name, Operation, Resource"** (16 metrics)
- Shows metrics with specific tool/agent names
- Best for analyzing individual tool performance

#### **Option 3: Target Type Analysis**
- Look for: **"Bedrock-AgentCore > TargetType, Resource"**
- Shows metrics for different target types (LAMBDA, OpenAPI, MCP)
- Best for comparing performance across target types

---

## 🔧 Understanding Gateway Operations

### What Each Gateway Operation Means

Gateway operations are different from Memory - they focus on **tool execution and MCP protocol**:

#### **🔄 MCP (Model Context Protocol) Operations**

| Operation | What It Does | When It Happens | Key Metrics |
|-----------|--------------|-----------------|-------------|
| **CallToolMcp** | ⭐ Executes tools through MCP protocol | Every time agent calls a tool | TargetExecutionTime, Latency, Invocations |
| **InitializeMcp** | Sets up MCP connection | Gateway startup and connection establishment | Invocations, SystemErrors |
| **InitializedNotificationMcp** | Signals MCP connection is ready | After successful MCP initialization | Invocations, Latency |
| **ListToolsMcp** | Discovers available MCP tools | Tool discovery phase during initialization | Invocations, Latency |

#### **🎯 Target Management Operations**

| Operation | What It Does | When It Happens | Key Metrics |
|-----------|--------------|-----------------|-------------|
| **InvokeTarget** | Directly calls Lambda/OpenAPI targets | When tools execute external functions | TargetExecutionTime, Invocations |
| **ListTargets** | Lists available targets for tools | Target discovery during gateway setup | Invocations, Latency |

#### **Key Differences from Memory Operations:**
- **Performance Focus**: Gateway metrics emphasize execution time and tool performance
- **Real-Time**: Gateway operations happen during active tool calls
- **Target-Centric**: Metrics track different target types (Lambda vs OpenAPI vs MCP)

---

## 📈 Adding Gateway Metrics to Graph

### Step 5: Select Metrics for Tool Performance Analysis

1. **Browse MCP Operations**
   - Click "Bedrock-AgentCore > Operation, Resource" (26 metrics)
   - You'll see metrics like:
     - `CallToolMcp Invocations` (most important for tool usage)
     - `CallToolMcp Latency` (gateway processing time)
     - `CallToolMcp TargetExecutionTime` (actual tool execution time)
     - `InitializeMcp Invocations` (MCP protocol health)

2. **Select Key Performance Metrics**
   - ✅ **CallToolMcp TargetExecutionTime** - How long tools take to execute
   - ✅ **CallToolMcp Latency** - Gateway processing overhead
   - ✅ **CallToolMcp Invocations** - Tool usage frequency
   - ✅ **SystemErrors, UserErrors** - Error tracking

3. **Understanding the Values**
   - Values show current/latest measurements
   - Look for patterns: TargetExecutionTime should typically be > Latency
   - If Latency > TargetExecutionTime, gateway has overhead issues

---

## ⚙️ Gateway-Specific Display Settings

### Step 6: Choose Statistics for Gateway Metrics

#### **For Tool Performance Analysis:**

**TargetExecutionTime** (Most Important Gateway Metric)
- **Average** ✅ **Recommended** - Shows typical tool execution time
- **Maximum** - Identifies slow tool executions
- **Example**: "Lambda functions take average 250ms to execute"

**Latency** (Gateway Processing Time)
- **Average** ✅ **Recommended** - Shows gateway overhead
- **Use for**: Comparing gateway time vs tool time
- **Example**: "Gateway adds 45ms of processing time"

**Duration** (End-to-End Time)
- **Average** ✅ **Recommended** - Shows complete request time
- **Formula**: Duration ≈ Latency + TargetExecutionTime
- **Example**: "Complete tool call takes 295ms"

#### **For Usage and Error Metrics:**

**Invocations** (Tool Usage)
- **Sum** ✅ **Recommended** - Shows total tool calls
- **Example**: "25 tool calls in the last hour"

**Errors, SystemErrors, UserErrors**
- **Sum** ✅ **Recommended** - Shows total error count
- **Use for**: Monitoring gateway reliability

#### **Gateway Metrics Quick Reference:**
```
TargetExecutionTime → Average (tool performance)
Latency → Average (gateway overhead) 
Duration → Average (total time)
Invocations → Sum (usage patterns)
Errors → Sum (reliability)
TargetType.LAMBDA → Sum (target distribution)
```

### Step 7: Set Period for Gateway Analysis

Gateway metrics have different timing patterns than Memory:

#### **Real-Time Tool Debugging (5m - 15m)**
- **Use for:** Active tool troubleshooting
- **Best when:** Tools are failing or slow right now
- **Focus on:** CallToolMcp operations
- **Example:** "Why is this Lambda function taking 10 seconds?"

#### **Session Performance Analysis (1h - 3h)**
- **Use for:** Analyzing current conversation tool usage
- **Best when:** Testing tool configurations
- **Focus on:** TargetExecutionTime trends
- **Example:** "How are tools performing during this test session?"

#### **Daily Usage Patterns (12h - 1d)**
- **Use for:** Understanding tool usage patterns
- **Best when:** Optimizing tool performance
- **Focus on:** Invocation patterns and target distribution
- **Example:** "Which tools are used most during business hours?"

#### **Capacity Planning (7 days - 30 days)**
- **Use for:** Scaling and infrastructure planning
- **Best when:** Planning Lambda provisioning
- **Focus on:** Long-term trends and error rates
- **Example:** "Do we need more Lambda concurrency?"

#### **Gateway Period Recommendations:**

| Metric Type | Recommended Period | Why |
|-------------|-------------------|-----|
| **TargetExecutionTime** | 1h for debugging, 1d for trends | Tools execute quickly, need granular view |
| **CallToolMcp Invocations** | 1h-1d | Tool calls are event-driven |
| **MCP Protocol health** (Initialize) | 1d-7d | Initialization happens infrequently |
| **Error analysis** | 15m-1h | Want immediate visibility into issues |
| **Target type comparison** | 1d-7d | Need enough data for meaningful comparison |

---

## 🎯 Practical Gateway Analysis Scenarios

### Scenario 1: Analyzing Tool Execution Performance 🔧

**Goal:** Why are my Lambda tools slow?

1. **Search:** Your Gateway ARN
2. **Select:** 
   - `CallToolMcp TargetExecutionTime` 
   - `CallToolMcp Latency`
   - `CallToolMcp Invocations`
3. **Settings:** Average for times, Sum for invocations, Period: 1h
4. **Analysis:**
   ```
   If TargetExecutionTime > 5000ms → Lambda cold start or function issues
   If Latency > TargetExecutionTime → Gateway bottleneck
   If Invocations are low → Tools not being called as expected
   ```

### Scenario 2: Monitoring MCP Protocol Health 🔄

**Goal:** Is the MCP connection working properly?

1. **Search:** Your Gateway ARN  
2. **Select:**
   - `InitializeMcp Invocations`
   - `InitializedNotificationMcp Invocations`
   - `ListToolsMcp Invocations`
   - `SystemErrors` for MCP operations
3. **Settings:** Sum for all, Period: 1d-7d
4. **Analysis:**
   ```
   InitializeMcp should occur at startup
   InitializedNotificationMcp should follow Initialize
   ListToolsMcp should happen during tool discovery
   SystemErrors = 0 for healthy MCP protocol
   ```

### Scenario 3: Comparing Target Types 🎯

**Goal:** Which target type performs best?

1. **Search:** Your Gateway ARN
2. **Select:**
   - `TargetType.LAMBDA Invocations`
   - `TargetType.OpenAPI Invocations` 
   - `TargetType.MCP Invocations`
   - `TargetExecutionTime` for each type
3. **Settings:** Sum for invocations, Average for execution time, Period: 7d
4. **Analysis:**
   ```
   Lambda: Typically fastest but cold starts possible
   OpenAPI: Network-dependent, more variable latency
   MCP: Protocol overhead, good for complex tools
   ```

### Scenario 4: Gateway vs Tool Performance Ratio 📊

**Goal:** Is the gateway adding significant overhead?

1. **Search:** Your Gateway ARN
2. **Select:**
   - `CallToolMcp TargetExecutionTime` (tool time)
   - `CallToolMcp Latency` (gateway time)
   - Create math expression: `m2/m1*100` (gateway overhead %)
3. **Settings:** Average for both, Period: 1h-1d
4. **Analysis:**
   ```
   Ideal: TargetExecutionTime >> Latency (tools do the work)
   Concern: Latency > TargetExecutionTime (gateway bottleneck)
   Target: Gateway overhead < 20% of total time
   ```

---

## 📊 Advanced Gateway Analysis

### Creating Gateway Performance Ratios

1. **Click "Add math" button**
2. **Useful Gateway expressions:**
   ```
   # Gateway overhead percentage
   (m1/(m1+m2)) * 100
   Where m1 = Latency, m2 = TargetExecutionTime
   
   # Tool success rate
   ((m1-m2)/m1) * 100
   Where m1 = Invocations, m2 = Errors
   
   # Average tools per session
   m1/m2
   Where m1 = CallToolMcp Invocations, m2 = InitializeMcp Invocations
   ```

### Gateway-Specific Queries

1. **Click "Add query" button**
2. **Example queries:**
   ```sql
   -- Tool performance by operation
   SELECT AVG(TargetExecutionTime) FROM SCHEMA("AWS/Bedrock-AgentCore", Operation, Resource) 
   WHERE Resource = 'your-gateway-arn' AND Operation = 'CallToolMcp'
   
   -- Error rate by operation  
   SELECT SUM(SystemErrors)/SUM(Invocations)*100 FROM SCHEMA("AWS/Bedrock-AgentCore", Operation, Resource)
   WHERE Resource = 'your-gateway-arn'
   ```

---

## 🔧 Gateway-Specific Troubleshooting

### Issue: "CallToolMcp metrics missing"

**Most Common Gateway Issue**

**Causes & Solutions:**
1. **Gateway not configured:** Agent isn't using the gateway
   - Check agent configuration for gateway ARN
2. **No tool calls:** Agent isn't calling any tools
   - Verify tools are available and properly configured
3. **MCP protocol issues:** Gateway can't communicate with agent
   - Check InitializeMcp and InitializedNotificationMcp metrics

### Issue: "TargetExecutionTime very high (>5 seconds)"

**Lambda Performance Issues**

**Causes & Solutions:**
1. **Cold starts:** Lambda functions starting from scratch
   - Solution: Use provisioned concurrency for frequently used functions
2. **Function timeout:** Lambda hitting timeout limits  
   - Solution: Increase timeout, optimize function code
3. **External API delays:** Lambda calling slow external services
   - Solution: Add timeouts, implement retry logic

### Issue: "Latency > TargetExecutionTime"

**Gateway Bottleneck**

**Causes & Solutions:**
1. **Large payloads:** Tool inputs/outputs are very large
   - Solution: Optimize payload size, use streaming
2. **Gateway overload:** Too many concurrent tool calls
   - Solution: Implement rate limiting, scale infrastructure
3. **Network issues:** Gateway-to-target connectivity problems
   - Solution: Check security groups, VPC configuration

### Issue: "High UserErrors (4xx)"

**Tool Configuration Problems**

**Causes & Solutions:**
1. **Invalid tool parameters:** Wrong input format or missing fields
   - Solution: Validate tool schemas and parameter types
2. **Target not found:** Lambda function doesn't exist or wrong name
   - Solution: Verify target configuration in gateway
3. **Permission denied:** Gateway can't invoke Lambda
   - Solution: Check IAM roles and policies

---

## 📚 Gateway Quick Reference

### Essential Gateway Metrics to Monitor

```
🔧 Tool Performance:
   • CallToolMcp TargetExecutionTime (most important)
   • CallToolMcp Latency (gateway overhead)
   • CallToolMcp Invocations (usage frequency)

🔄 MCP Protocol Health:
   • InitializeMcp Invocations (connection setup)
   • InitializedNotificationMcp (ready signal)
   • ListToolsMcp (tool discovery)

🎯 Target Analysis:
   • TargetType.LAMBDA (Lambda usage)
   • TargetType.OpenAPI (API usage)
   • SystemErrors, UserErrors (reliability)
```

### Optimal Settings by Gateway Use Case

```
🚨 Tool Troubleshooting:
   Statistic: Average (TargetExecutionTime, Latency)
   Period: 5m-1h
   Time range: Last 3 hours
   Focus: CallToolMcp operations

📊 Performance Optimization:
   Statistic: Average, Maximum
   Period: 1h-1d
   Time range: Last 24 hours  
   Focus: Target execution vs gateway latency

📈 Capacity Planning:
   Statistic: Sum (Invocations), Average (times)
   Period: 1d-7d
   Time range: Last 30 days
   Focus: Usage patterns and target distribution
```

### Performance Benchmarks

```
✅ Good Gateway Performance:
   • TargetExecutionTime: < 2000ms for Lambda
   • Latency: < 200ms for gateway processing
   • Gateway overhead: < 20% of total time
   • Error rate: < 5% UserErrors, 0% SystemErrors

⚠️ Performance Concerns:
   • TargetExecutionTime: > 5000ms consistently
   • Latency > TargetExecutionTime (gateway bottleneck)
   • Gateway overhead: > 50% of total time
   • Error rate: > 10% or any SystemErrors
```

### Direct CloudWatch URLs for Gateway

Replace `{REGION}` and `{GATEWAY_ID}` with your values:

```
All Gateway Metrics:
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~();query=~'*7bAWS*2fBedrock-AgentCore*2cResource*7d;search={GATEWAY_ID}

Tool Performance Analysis:
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~();query=~'*7bAWS*2fBedrock-AgentCore*2cOperation*2cResource*7d;search=CallToolMcp

MCP Protocol Health:
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~();query=~'*7bAWS*2fBedrock-AgentCore*2cOperation*2cResource*7d;search=InitializeMcp
```

---

## 🚨 Critical Gateway Alerts

### Recommended CloudWatch Alarms

1. **Tool Execution Time Alert**
   ```
   Metric: TargetExecutionTime
   Condition: Average > 10000 (10 seconds)
   Period: 5 minutes
   Action: Investigate Lambda performance
   ```

2. **Gateway Error Rate Alert**
   ```
   Metric: Math expression: (SystemErrors + UserErrors) / Invocations * 100
   Condition: > 5%
   Period: 15 minutes  
   Action: Check tool configurations and permissions
   ```

3. **MCP Connection Health Alert**
   ```
   Metric: InitializeMcp Invocations
   Condition: No datapoints for 30 minutes
   Action: Check gateway connectivity and MCP protocol
   ```

---

**💡 Gateway Pro Tips:**

1. **Monitor the Ratio**: Always compare TargetExecutionTime vs Latency
2. **Focus on CallToolMcp**: This is your most important metric for tool performance
3. **Watch Target Types**: Different target types have different performance characteristics
4. **Correlate with Memory**: Gateway tool calls often trigger memory operations
5. **Set Baseline**: Establish normal performance ranges for your specific tools

**🎯 Your gateway metrics are now fully accessible and optimized for tool performance analysis!**