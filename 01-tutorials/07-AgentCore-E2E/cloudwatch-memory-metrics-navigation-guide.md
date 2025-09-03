# CloudWatch Navigation Guide: AgentCore Memory Metrics

## Complete Step-by-Step Console Navigation

This guide provides detailed instructions for analyzing AgentCore Memory metrics in the AWS CloudWatch console, starting from scratch.

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

## 🔍 Finding AgentCore Memory Metrics

### Step 2: Locate the Namespace

1. **Search for AgentCore Namespace**
   - In the namespace section, look for **`AWS/Bedrock-AgentCore`**
   - Or type `Bedrock-AgentCore` in the search box
   - Click on the namespace when it appears

2. **Alternative: Browse Method**
   - Scroll through the "AWS Services" section
   - Look for **`AWS/Bedrock-AgentCore`**
   - This namespace contains all AgentCore metrics

---

## 🎯 Searching with Memory ARN

### Step 3: Filter by Your Memory Resource

1. **Get Your Memory ARN**
   ```
   arn:aws:bedrock-agentcore:us-east-1:533267284022:memory/CustomerSupportMemory-WcEhTTFp1O
   ```
   *(Replace with your actual Memory ARN from Lab 2)*

2. **Use the Search Bar**
   - Look for the search box at the top: "Search for any metric, dimension, resource id or account id"
   - Paste your Memory ARN or just the Memory ID: `CustomerSupportMemory-WcEhTTFp1O`
   - Press Enter

3. **Understanding Search Results**
   - You'll see dimension combinations like:
     - **"Bedrock-AgentCore > Operation, Resource, StrategyId, StrategyType"** (8 metrics)
     - **"Bedrock-AgentCore > ItemType, Resource"** (2 metrics) 
     - **"Bedrock-AgentCore > Operation, Resource"** (8 metrics)

---

## 📊 Selecting Dimension Combinations

### Step 4: Choose the Right Dimensions

Click on dimension combinations to see available metrics:

#### **Option 1: Operation-Based Metrics**
- Click: **"Bedrock-AgentCore > Operation, Resource"**
- Shows metrics for specific memory operations
- Best for analyzing individual operation performance

#### **Option 2: Item Type Metrics**
- Click: **"Bedrock-AgentCore > ItemType, Resource"**
- Shows metrics for different memory item types
- Best for understanding what's being created

#### **Option 3: Strategy-Based Metrics**
- Click: **"Bedrock-AgentCore > Operation, Resource, StrategyId, StrategyType"**
- Shows metrics with memory strategy details
- Best for advanced memory strategy analysis

---

## 🔧 Understanding Memory Operations

### What Each Operation Means

When you see these operations in CloudWatch, here's what they represent:

#### **🔄 Background Processing Operations**

| Operation | What It Does | When It Happens | Key Metrics |
|-----------|--------------|-----------------|-------------|
| **Consolidation** | Merges extracted memories with existing ones to create unified knowledge | Background process after conversations | Latency, Invocations |
| **Extraction** | Analyzes conversations to extract key information for long-term memory | Background process after user interactions | CreationCount, Latency |

#### **🎯 Active Memory Operations**

| Operation | What It Does | When It Happens | Key Metrics |
|-----------|--------------|-----------------|-------------|
| **CreateEvent** | Records new conversation events (user messages, assistant responses) | During every conversation | Invocations, Latency |
| **RetrieveMemoryRecords** | Searches memory for relevant information to include in responses | When agent needs context for responses | Latency, Invocations |
| **GetMemory** | Retrieves existing memory entries | When accessing stored memories | Latency, Invocations |
| **CreateMemory** | Initializes new memory instances | Memory system startup | Invocations, SystemErrors |

---

## 📈 Adding Metrics to Graph

### Step 5: Select Metrics for Analysis

1. **Browse Available Metrics**
   - Each dimension combination shows checkboxes next to metrics
   - You'll see metrics like:
     - `CreateEvent Latency` (59.8ms)
     - `CreateEvent Invocations` (1)
     - `RetrieveMemoryRecords Latency` (186ms)
     - `RetrieveMemoryRecords Invocations` (1)

2. **Select Metrics**
   - ✅ Check the boxes next to metrics you want to analyze
   - Selected metrics appear in the **"Graphed metrics"** tab
   - You'll see something like "Graphed metrics (10/16)"

3. **Understanding the Display**
   - Large numbers show current/latest values
   - Colors match the legend below
   - Hover for detailed information

---

## ⚙️ Configuring Display Settings

### Step 6: Choose the Right Statistic

The **Statistic** determines how data points are aggregated:

#### **For Latency and Performance Metrics:**
- **Average** ✅ **Recommended**
  - Shows typical response times
  - Best for: `Latency`, `Duration`
  - Example: "Average latency is 59.8ms"

- **Maximum**
  - Shows worst-case performance
  - Use for: Identifying performance spikes
  - Example: "Max latency was 500ms"

#### **For Count and Usage Metrics:**
- **Sum** ✅ **Recommended**
  - Shows total operations
  - Best for: `Invocations`, `CreationCount`
  - Example: "5 total invocations in this period"

- **SampleCount**
  - Shows number of data points
  - Use for: Understanding data density

#### **Quick Reference:**
```
Latency, Duration → Average
Invocations, CreationCount → Sum
Errors, SystemErrors → Sum
Throttles → Sum
```

### Step 7: Set Appropriate Period

The **Period** determines the time granularity of data points:

#### **Real-Time Analysis (5m - 15m)**
- **Use for:** Active debugging and troubleshooting
- **Best when:** Something is broken right now
- **Example:** "Memory operations are failing in the last 15 minutes"

#### **Recent Activity Analysis (1h - 3h)**
- **Use for:** Understanding current session performance
- **Best when:** Analyzing recent conversation patterns
- **Example:** "How did memory perform during today's testing?"

#### **Daily Pattern Analysis (12h - 1d)**
- **Use for:** Understanding daily usage patterns
- **Best when:** Looking for trends and optimization opportunities
- **Example:** "When are memory operations heaviest during the day?"

#### **Long-Term Trends (7 days)**
- **Use for:** Capacity planning and historical analysis
- **Best when:** Planning infrastructure or identifying long-term issues
- **Example:** "How has memory usage grown over the past week?"

#### **Period Recommendations by Metric:**

| Metric Type | Recommended Period | Why |
|-------------|-------------------|-----|
| **Latency** | 1h for debugging, 1d for trends | Shows response time patterns |
| **Invocations** | 1d or 7d | Need longer periods for meaningful counts |
| **CreationCount** | 1d or 7d | Memory creation happens over time |
| **Errors** | 1h | Want to quickly spot and fix issues |
| **Background ops** (Consolidation) | 1d or 7d | These run on slower schedules |

---

## 🎯 Practical Analysis Scenarios

### Scenario 1: Analyzing Memory Retrieval Performance

**Goal:** Understand why memory lookups are slow

1. **Search:** Use your Memory ARN
2. **Select:** `RetrieveMemoryRecords Latency` and `RetrieveMemoryRecords Invocations`
3. **Statistic:** Average for Latency, Sum for Invocations
4. **Period:** 1h for recent analysis, 1d for patterns
5. **Analysis:**
   - If Latency > 200ms consistently → Memory store is large, consider optimization
   - If Invocations are low → Agent isn't using memory effectively
   - If Invocations spike with Latency → Correlate with conversation complexity

### Scenario 2: Monitoring Background Memory Processing

**Goal:** Track how memory consolidation affects performance

1. **Search:** Your Memory ARN
2. **Select:** `Consolidation Latency`, `Consolidation Invocations`, `Extraction CreationCount`
3. **Statistic:** Average for Latency, Sum for others
4. **Period:** 1d or 7d (background processes are slower)
5. **Analysis:**
   - Consolidation should happen after conversations
   - High Consolidation Latency → Memory store growth
   - CreationCount shows how much new information is being extracted

### Scenario 3: Tracking Memory Creation Patterns

**Goal:** Understand how memory grows over time

1. **Search:** Your Memory ARN
2. **Select:** `CreateEvent Invocations`, `CreationCount` by ItemType
3. **Statistic:** Sum for both
4. **Period:** 7 days for growth trends
5. **Analysis:**
   - CreateEvent Invocations = conversation activity
   - CreationCount = actual memory items created
   - Ratio shows efficiency of memory creation

---

## 📊 Advanced CloudWatch Features

### Creating Custom Math Expressions

1. **Click "Add math" button**
2. **Common expressions for memory:**
   ```
   # Memory efficiency ratio
   m1/m2 * 100
   Where m1 = CreationCount, m2 = CreateEvent Invocations
   
   # Error rate percentage
   (m1/(m1+m2)) * 100
   Where m1 = Errors, m2 = Invocations
   
   # Background processing ratio
   m1/m2
   Where m1 = Consolidation Latency, m2 = CreateEvent Latency
   ```

### Creating Queries

1. **Click "Add query" button**
2. **Example queries:**
   ```sql
   -- All memory operations
   SELECT AVG(Latency) FROM SCHEMA("AWS/Bedrock-AgentCore", Operation, Resource) 
   WHERE Resource = 'your-memory-arn'
   
   -- Error rates
   SELECT SUM(Errors)/SUM(Invocations)*100 FROM SCHEMA("AWS/Bedrock-AgentCore", Resource)
   WHERE Resource = 'your-memory-arn'
   ```

### Saving as Dashboard

1. **Select metrics you want to monitor regularly**
2. **Click "Add to dashboard"**
3. **Choose "Create new dashboard"**
4. **Name it:** `AgentCore-Memory-{MemoryID}`
5. **Customize widgets:** Line, Bar, Number, etc.

---

## 🔧 Troubleshooting Common Issues

### Issue: "No data available"

**Causes & Solutions:**
1. **Memory not active:** Generate some conversations to create metrics
2. **Wrong ARN:** Verify your Memory ARN from AgentCore console
3. **Time range:** Expand time range to 7 days
4. **Region:** Ensure you're in the correct AWS region

### Issue: "Metrics appear in console but not in my queries"

**Solutions:**
1. **Check dimensions:** Use Resource + Operation combination
2. **Verify ARN format:** Should match exactly what's shown in CloudWatch
3. **Check operation names:** Use exact names (case-sensitive)

### Issue: "Values seem too high/low"

**Check your settings:**
1. **Statistic:** Average vs Sum makes a big difference
2. **Period:** Longer periods smooth out spikes
3. **Time range:** Ensure you're looking at relevant time period

---

## 📚 Quick Reference

### Essential Memory Operations to Monitor

```
🔄 Background Processing:
   • Consolidation (memory merging)
   • Extraction (information extraction)

🎯 Active Operations:
   • RetrieveMemoryRecords (memory search) ← Most important for performance
   • CreateEvent (conversation recording)
   • GetMemory (memory access)
   • CreateMemory (initialization)
```

### Optimal Settings by Use Case

```
🚨 Troubleshooting:
   Statistic: Average (latency), Sum (counts)
   Period: 5m-1h
   Time range: Last 3 hours

📊 Performance Analysis:
   Statistic: Average, Maximum
   Period: 1h-1d  
   Time range: Last 24 hours

📈 Capacity Planning:
   Statistic: Sum, Average
   Period: 1d-7d
   Time range: Last 30 days
```

### Direct CloudWatch URLs

Replace `{REGION}` and `{MEMORY_ID}` with your values:

```
All Memory Metrics:
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~();query=~'*7bAWS*2fBedrock-AgentCore*2cResource*7d;search={MEMORY_ID}

RetrieveMemoryRecords Only:
https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#metricsV2:graph=~();query=~'*7bAWS*2fBedrock-AgentCore*2cResource*2cOperation*7d;search=RetrieveMemoryRecords
```

---

**💡 Pro Tip:** Bookmark your Memory-specific CloudWatch URL for quick access during development and troubleshooting!