#!/usr/bin/env python3
"""
Test script to properly discover and query AgentCore metrics
This fixes the issues in lab-07-metrics-dashboards-final-fixed.ipynb
"""

import boto3
import json
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

def test_agentcore_metrics():
    """Test AgentCore metrics discovery with CORRECT namespace"""
    
    print("🔍 TESTING AGENTCORE METRICS - WORKING VERSION")
    print("=" * 60)
    
    # Initialize AWS clients
    try:
        session = boto3.Session()
        region = session.region_name
        account_id = boto3.client('sts').get_caller_identity()['Account']
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        print(f"✅ Connected to AWS Account: {account_id} in {region}")
    except Exception as e:
        print(f"❌ AWS client initialization failed: {e}")
        return
    
    # Test CORRECT namespace - AWS/Bedrock-AgentCore
    namespace = "AWS/Bedrock-AgentCore"
    print(f"\n🔍 Testing namespace: {namespace}")
    
    try:
        response = cloudwatch.list_metrics(Namespace=namespace)
        metrics = response.get('Metrics', [])
        
        if metrics:
            print(f"✅ SUCCESS! Found {len(metrics)} metrics in {namespace}")
            
            # Analyze metrics
            metric_names = set()
            resource_metrics = {}
            
            for metric in metrics:
                metric_name = metric['MetricName']
                metric_names.add(metric_name)
                
                # Extract resource info
                for dimension in metric.get('Dimensions', []):
                    if dimension['Name'] == 'Resource':
                        resource = dimension['Value']
                        if resource not in resource_metrics:
                            resource_metrics[resource] = set()
                        resource_metrics[resource].add(metric_name)
            
            print(f"\n📊 Available Metric Types:")
            for name in sorted(metric_names):
                print(f"   • {name}")
            
            print(f"\n🔗 Resources with Metrics:")
            for resource, metrics_set in resource_metrics.items():
                resource_type = "Unknown"
                if "runtime" in resource.lower():
                    resource_type = "Runtime"
                elif "gateway" in resource.lower():
                    resource_type = "Gateway"
                elif "memory" in resource.lower():
                    resource_type = "Memory"
                
                print(f"\n   📈 {resource_type}:")
                print(f"      Resource: {resource}")
                print(f"      Metrics: {', '.join(sorted(metrics_set))}")
                
                # Test querying a metric for this resource
                test_metric_query(cloudwatch, namespace, resource, list(metrics_set)[0])
        else:
            print(f"⚠️ No metrics found in {namespace}")
            print(f"\n💡 This means:")
            print(f"   • AgentCore resources haven't been used yet")
            print(f"   • OR observability is not enabled")
            print(f"   • OR metrics haven't appeared yet (can take 5-10 minutes)")
            
    except Exception as e:
        print(f"❌ Error querying metrics: {e}")

def test_metric_query(cloudwatch, namespace, resource_arn, metric_name):
    """Test querying a specific metric"""
    
    print(f"\n      🔍 Testing query for {metric_name}...")
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=[
                {'Name': 'Resource', 'Value': resource_arn}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour periods
            Statistics=['Sum', 'Average']
        )
        
        datapoints = response.get('Datapoints', [])
        if datapoints:
            latest = max(datapoints, key=lambda x: x['Timestamp'])
            value = latest.get('Sum', latest.get('Average', 0))
            print(f"         ✅ Latest value: {value:.2f} ({len(datapoints)} datapoints)")
        else:
            print(f"         ⏳ No recent data (normal if resource not used recently)")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"         ⚠️ Query error: {error_code}")
    except Exception as e:
        print(f"         ❌ Unexpected error: {e}")

def get_lab_resources():
    """Get resources from previous labs"""
    
    print(f"\n🔍 Getting Lab Resources from SSM Parameters...")
    
    try:
        ssm = boto3.client('ssm')
        
        resources = {}
        params = [
            ('/app/customersupport/agentcore/runtime_arn', 'Runtime (Lab 4)'),
            ('/app/customersupport/agentcore/gateway_arn', 'Gateway (Lab 3)'),
            ('/app/customersupport/agentcore/memory_id', 'Memory (Lab 2)')
        ]
        
        for param_name, resource_type in params:
            try:
                response = ssm.get_parameter(Name=param_name)
                value = response['Parameter']['Value']
                resources[param_name] = value
                print(f"   ✅ Found {resource_type}: {value}")
            except ssm.exceptions.ParameterNotFound:
                print(f"   ❌ {resource_type} not found")
            except Exception as e:
                print(f"   ⚠️ {resource_type} error: {e}")
        
        return resources
        
    except Exception as e:
        print(f"❌ Error accessing SSM: {e}")
        return {}

def create_working_dashboard():
    """Create a working CloudWatch dashboard with correct namespace"""
    
    print(f"\n📊 Creating Working CloudWatch Dashboard...")
    
    try:
        cloudwatch = boto3.client('cloudwatch')
        session = boto3.Session()
        region = session.region_name
        
        # Get lab resources
        resources = get_lab_resources()
        
        widgets = []
        
        if '/app/customersupport/agentcore/runtime_arn' in resources:
            runtime_arn = resources['/app/customersupport/agentcore/runtime_arn']
            
            # Runtime performance widget
            widget = {
                "type": "metric",
                "x": 0, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/Bedrock-AgentCore", "Invocations", "Resource", runtime_arn, {"stat": "Sum", "label": "Runtime Invocations"}],
                        [".", "Latency", ".", ".", {"stat": "Average", "label": "Runtime Latency (ms)"}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": region,
                    "title": "🤖 Runtime Performance (FIXED)",
                    "yAxis": {"left": {"min": 0}}
                }
            }
            widgets.append(widget)
        
        if widgets:
            dashboard_name = "AgentCore-CustomerSupport-FIXED"
            dashboard_body = {"widgets": widgets}
            
            response = cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            dashboard_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}"
            print(f"   ✅ Created dashboard: {dashboard_name}")
            print(f"   🔗 View it here: {dashboard_url}")
            print(f"   🔧 Using CORRECT namespace: AWS/Bedrock-AgentCore")
        else:
            print(f"   ⚠️ No resources available for dashboard")
            
    except Exception as e:
        print(f"❌ Error creating dashboard: {e}")

if __name__ == "__main__":
    print("🚀 AgentCore Metrics Test Script")
    print("This script tests the CORRECT way to access AgentCore metrics")
    print("Run this to validate your metrics setup before using the notebook")
    print()
    
    # Test metrics discovery
    test_agentcore_metrics()
    
    # Get lab resources
    get_lab_resources()
    
    # Create working dashboard
    create_working_dashboard()
    
    print(f"\n🎉 Test complete!")
    print(f"💡 If metrics were found, your AgentCore observability is working!")
    print(f"📝 Use this script's approach to fix the lab-07 notebook")
