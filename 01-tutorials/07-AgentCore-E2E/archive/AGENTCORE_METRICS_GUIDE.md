# AgentCore and Bedrock Metrics Complete Guide

## Overview

This guide documents the correct way to query CloudWatch metrics for AWS Bedrock AgentCore components (Runtime, Memory, Gateway) and Bedrock model invocations. Based on empirical testing and actual metric discovery.

## Key Findings

### 1. Namespace Differences
- **AgentCore Components**: `AWS/Bedrock-AgentCore`
- **Bedrock Model Invocations**: `AWS/Bedrock`

### 2. Dimension Complexity
Unlike simple resource-based metrics, AgentCore metrics use multiple dimension combinations:
- **Resource**: The ARN of the component
- **Operation**: Specific operations (e.g., `InvokeAgentRuntime`, `ListMemory`, `CreateEvent`)
- **Name**: Agent or component name
- **ItemType**: Type of item being processed
- **TargetType**: For Gateway, the target type (e.g., `LAMBDA`)

## Bedrock Model Metrics

### Namespace: `AWS/Bedrock`

### Available Metrics
```python
metrics_config = [
    ('Invocations', 'Sum', 'Number of successful model invocations'),
    ('InvocationLatency', 'Average', 'Average latency in milliseconds'),
    ('InvocationClientErrors', 'Sum', 'Count of client-side errors'),
    ('InvocationServerErrors', 'Sum', 'Count of server-side errors'),
    ('InvocationThrottles', 'Sum', 'Number of throttled requests'),
    ('InputTokenCount', 'Sum', 'Total number of input tokens'),
    ('OutputTokenCount', 'Sum', 'Total number of output tokens'),
    ('LegacyModelInvocations', 'Sum', 'Number of legacy model invocations')
]
```

### Query Function
```python
def query_bedrock_model_metrics(model_id: str, hours_back: int = 24) -> Dict:
    """Query Bedrock model invocation metrics from CloudWatch"""
    
    if not model_id:
        print("⚠️ No Model ID provided.")
        return {}
    
    print(f"\n📊 Querying Bedrock Model Metrics")
    print(f"🔗 Model ID: {model_id}")
    print("-" * 50)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    metrics_config = [
        ('Invocations', 'Sum', 'Number of successful model invocations'),
        ('InvocationLatency', 'Average', 'Average latency in milliseconds'),
        ('InvocationClientErrors', 'Sum', 'Count of client-side errors'),
        ('InvocationServerErrors', 'Sum', 'Count of server-side errors'),
        ('InvocationThrottles', 'Sum', 'Number of throttled requests'),
        ('InputTokenCount', 'Sum', 'Total number of input tokens'),
        ('OutputTokenCount', 'Sum', 'Total number of output tokens'),
        ('LegacyModelInvocations', 'Sum', 'Number of legacy model invocations')
    ]
    
    metrics_data = {}
    
    for metric_name, statistic, description in metrics_config:
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Bedrock',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'ModelId', 'Value': model_id}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=[statistic]
            )
            
            datapoints = response.get('Datapoints', [])
            if datapoints:
                sorted_points = sorted(datapoints, key=lambda x: x['Timestamp'])
                metrics_data[metric_name] = sorted_points
                latest = sorted_points[-1][statistic]
                print(f"✅ {metric_name}: {latest:.2f}")
                print(f"   {description}")
                print(f"   Data points: {len(datapoints)}")
            else:
                print(f"ℹ️ {metric_name}: No data available")
                print(f"   {description}")
        except Exception as e:
            print(f"❌ Error fetching {metric_name}: {str(e)}")
    
    return metrics_data
```

### Example Model IDs
- `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- `anthropic.claude-v2`
- `amazon.titan-text-express-v1`

## AgentCore Metrics

### Namespace: `AWS/Bedrock-AgentCore`

### Important Discovery
AgentCore metrics are not available with just the `Resource` dimension. They require specific operation-based dimension combinations.

### Actual Metrics Found
From empirical testing, these metrics exist with various dimension combinations:
- **Invocations**: 60 dimension combinations found
- **Latency**: 59 dimension combinations found
- **Duration**: 11 dimension combinations found
- **Errors**: 4 dimension combinations found
- **SystemErrors**: 11 dimension combinations found

### Common Operations Discovered
- `ListMemory`
- `CreateEvent`
- `InvokeAgentRuntime`
- `CreateSession`
- `GetEvent`

## Working Query Functions

### 1. Discovery Function for Any Resource
```python
def discover_all_metrics_for_resource(resource_arn: str, resource_type: str = "Unknown") -> Dict:
    """Discover ALL available metrics and dimensions for any AgentCore resource"""
    
    print(f"\n🔍 Discovering all metrics for {resource_type}")
    print(f"🔗 Resource: {resource_arn}")
    print("-" * 50)
    
    discovered = {
        'metrics': {},
        'operations': set(),
        'dimensions': set()
    }
    
    try:
        response = cloudwatch.list_metrics(
            Namespace='AWS/Bedrock-AgentCore',
            Dimensions=[
                {'Name': 'Resource', 'Value': resource_arn}
            ]
        )
        
        print(f"✅ Found {len(response['Metrics'])} metric combinations\n")
        
        for metric in response['Metrics']:
            metric_name = metric['MetricName']
            
            if metric_name not in discovered['metrics']:
                discovered['metrics'][metric_name] = []
            
            dim_combo = {}
            for dim in metric['Dimensions']:
                dim_combo[dim['Name']] = dim['Value']
                discovered['dimensions'].add(dim['Name'])
                
                if dim['Name'] == 'Operation':
                    discovered['operations'].add(dim['Value'])
            
            discovered['metrics'][metric_name].append(dim_combo)
        
        print(f"📈 Unique Metrics: {', '.join(discovered['metrics'].keys())}")
        print(f"📐 Dimensions Used: {', '.join(discovered['dimensions'])}")
        
        if discovered['operations']:
            print(f"\n⚙️ Operations Found:")
            for op in sorted(discovered['operations']):
                print(f"   • {op}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    return discovered
```

### 2. Query by Metric Name (Dimension Agnostic)
```python
def query_agentcore_by_metric_name(metric_name: str, hours_back: int = 24) -> None:
    """Query a specific metric regardless of dimensions"""
    
    print(f"\n📊 Querying Metric: {metric_name}")
    print("-" * 50)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    try:
        response = cloudwatch.list_metrics(
            Namespace='AWS/Bedrock-AgentCore',
            MetricName=metric_name
        )
        
        if not response['Metrics']:
            print(f"❌ No data found for metric: {metric_name}")
            return
        
        print(f"✅ Found {len(response['Metrics'])} dimension combinations for {metric_name}\n")
        
        for metric_config in response['Metrics'][:5]:
            dimensions = metric_config['Dimensions']
            dim_str = ', '.join([f"{d['Name']}={d['Value']}" for d in dimensions])
            
            try:
                stats = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock-AgentCore',
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum', 'Average', 'Maximum']
                )
                
                if stats['Datapoints']:
                    latest = sorted(stats['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                    print(f"📍 {dim_str}")
                    if 'Sum' in latest:
                        print(f"   Sum: {latest['Sum']:.2f}")
                    if 'Average' in latest:
                        print(f"   Avg: {latest['Average']:.2f}")
                    if 'Maximum' in latest:
                        print(f"   Max: {latest['Maximum']:.2f}")
                    print()
                    
            except Exception as e:
                print(f"   Error: {str(e)}")
                
    except Exception as e:
        print(f"❌ Error querying metric: {str(e)}")
```

### 3. Enhanced Runtime Query Function
```python
def query_runtime_metrics_v2(runtime_arn: str, hours_back: int = 24) -> Dict:
    """Query Runtime metrics with proper dimension combinations"""
    
    if not runtime_arn:
        print("⚠️ No Runtime ARN available.")
        return {}
    
    print(f"\n📊 Querying Runtime Metrics (Enhanced)")
    print(f"🔗 Resource: {runtime_arn}")
    print("-" * 50)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    metrics_data = {}
    
    # Try different dimension combinations
    dimension_sets = [
        [{'Name': 'Resource', 'Value': runtime_arn}],
        [
            {'Name': 'Resource', 'Value': runtime_arn},
            {'Name': 'Operation', 'Value': 'InvokeAgentRuntime'}
        ],
        [
            {'Name': 'Resource', 'Value': runtime_arn},
            {'Name': 'Operation', 'Value': 'InvokeAgentRuntime'},
            {'Name': 'Name', 'Value': 'customer_support_agent::DEFAULT'}
        ]
    ]
    
    metrics_to_query = [
        ('Invocations', 'Sum', 'Total invocations'),
        ('Latency', 'Average', 'Average latency (ms)'),
        ('Errors', 'Sum', 'Total errors'),
        ('SystemErrors', 'Sum', 'System errors'),
        ('Duration', 'Average', 'Average duration')
    ]
    
    for dimensions in dimension_sets:
        dim_str = ', '.join([f"{d['Name']}={d['Value'].split('/')[-1] if '/' in d['Value'] else d['Value']}" for d in dimensions])
        print(f"\n🔍 Trying dimensions: {dim_str}")
        
        found_any = False
        for metric_name, statistic, description in metrics_to_query:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock-AgentCore',
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=[statistic]
                )
                
                datapoints = response.get('Datapoints', [])
                if datapoints:
                    sorted_points = sorted(datapoints, key=lambda x: x['Timestamp'])
                    latest = sorted_points[-1][statistic]
                    print(f"   ✅ {metric_name}: {latest:.2f} - {description}")
                    
                    if metric_name not in metrics_data:
                        metrics_data[metric_name] = {
                            'dimensions': dimensions,
                            'datapoints': sorted_points,
                            'latest_value': latest
                        }
                    found_any = True
                    
            except Exception as e:
                pass
        
        if not found_any:
            print(f"   ℹ️ No data with these dimensions")
    
    return metrics_data
```

## List All Available Metrics
```python
def list_all_agentcore_metrics(hours_back: int = 24) -> None:
    """List all available metrics in the AWS/Bedrock-AgentCore namespace"""
    
    print(f"\n📊 Listing All AgentCore Metrics")
    print("-" * 50)
    
    try:
        paginator = cloudwatch.get_paginator('list_metrics')
        page_iterator = paginator.paginate(
            Namespace='AWS/Bedrock-AgentCore'
        )
        
        metrics_found = {}
        
        for page in page_iterator:
            for metric in page['Metrics']:
                metric_name = metric['MetricName']
                dimensions = metric['Dimensions']
                
                dim_str = ', '.join([f"{d['Name']}={d['Value']}" for d in dimensions])
                
                if metric_name not in metrics_found:
                    metrics_found[metric_name] = []
                
                metrics_found[metric_name].append(dim_str)
        
        if metrics_found:
            print(f"✅ Found {len(metrics_found)} unique metrics:\n")
            
            for metric_name, dimensions_list in sorted(metrics_found.items()):
                print(f"📈 {metric_name}")
                for dim in dimensions_list[:3]:
                    print(f"   • {dim}")
                if len(dimensions_list) > 3:
                    print(f"   ... and {len(dimensions_list) - 3} more dimension combinations")
                print()
        else:
            print("❌ No metrics found in AWS/Bedrock-AgentCore namespace")
            
    except Exception as e:
        print(f"❌ Error listing metrics: {str(e)}")
```

## Troubleshooting

### No Metrics Appearing

1. **Check Observability is Enabled**
   - Verify in AgentCore console that observability is enabled for each resource

2. **Generate Activity**
   - Invoke your agent/runtime to generate metrics
   - Use memory operations to generate memory metrics
   - Call gateway targets to generate gateway metrics

3. **Wait for Propagation**
   - Metrics can take 2-5 minutes to appear in CloudWatch

4. **Use Discovery Functions**
   - Run `list_all_agentcore_metrics()` to see what's available
   - Use `discover_all_metrics_for_resource()` for specific resources

5. **Check Dimensions**
   - AgentCore metrics often require Operation dimension
   - Not all metrics are available with just Resource dimension

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| No data with Resource dimension only | Add Operation dimension (e.g., `InvokeAgentRuntime`) |
| Metrics exist but query returns empty | Check dimension combinations with discovery functions |
| Different metric counts in console | Console shows all dimension combinations, not unique metrics |
| Memory/Gateway metrics missing | These components may not emit metrics until used |

## Example Usage

```python
# For Bedrock models
model_metrics = query_bedrock_model_metrics("us.anthropic.claude-3-7-sonnet-20250219-v1:0")

# For AgentCore Runtime
runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789:runtime/agent-abc123"
runtime_metrics = query_runtime_metrics_v2(runtime_arn)

# Discover what's available
discovered = discover_all_metrics_for_resource(runtime_arn, "Runtime")

# Query specific metric regardless of dimensions
query_agentcore_by_metric_name("Invocations")
```

## Key Takeaways

1. **Bedrock model metrics** use `AWS/Bedrock` namespace with `ModelId` dimension
2. **AgentCore metrics** use `AWS/Bedrock-AgentCore` namespace with complex dimension combinations
3. **Discovery is essential** - Use discovery functions to find available metrics and dimensions
4. **Operations matter** - Many metrics require the Operation dimension to query successfully
5. **Patience required** - Metrics take time to appear after resource creation and usage

## References

- [AWS Bedrock Runtime Metrics Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html)
- [CloudWatch Model Invocations](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/model-invocations.html)
- CloudWatch Console: Browse > Metrics > AWS/Bedrock-AgentCore