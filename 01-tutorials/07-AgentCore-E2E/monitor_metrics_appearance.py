#!/usr/bin/env python3
"""
Monitor script to watch for AgentCore Runtime metrics to appear
Run this after invoking your runtime in Lab 4
"""

import boto3
import time
from datetime import datetime, timedelta, timezone

def monitor_runtime_metrics():
    """Monitor when runtime metrics appear in CloudWatch"""
    
    cloudwatch = boto3.client('cloudwatch')
    runtime_arn = 'arn:aws:bedrock-agentcore:us-east-1:533267284022:runtime/customer_support_agent-b0Ilb5ACG7'
    
    print("🔍 MONITORING RUNTIME METRICS APPEARANCE")
    print("=" * 50)
    print(f"Runtime: {runtime_arn}")
    print(f"Checking every 30 seconds for metrics...")
    print("Press Ctrl+C to stop\n")
    
    metrics_to_check = ['Invocations', 'Sessions', 'Latency', 'Duration']
    found_metrics = set()
    
    check_count = 0
    
    try:
        while len(found_metrics) < len(metrics_to_check):
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 Check #{check_count} at {current_time}")
            
            # Check last 3 hours for recent invocations
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=3)
            
            for metric_name in metrics_to_check:
                if metric_name in found_metrics:
                    continue
                    
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/Bedrock-AgentCore',
                        MetricName=metric_name,
                        Dimensions=[
                            {'Name': 'Resource', 'Value': runtime_arn}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=300,  # 5-minute periods
                        Statistics=['Sum', 'Average', 'Maximum']
                    )
                    
                    datapoints = response.get('Datapoints', [])
                    if datapoints:
                        found_metrics.add(metric_name)
                        latest = max(datapoints, key=lambda x: x['Timestamp'])
                        value = latest.get('Sum', latest.get('Average', latest.get('Maximum', 0)))
                        print(f"   ✅ {metric_name}: {value:.2f} (found!)")
                    else:
                        print(f"   ⏳ {metric_name}: Still waiting...")
                        
                except Exception as e:
                    print(f"   ❌ {metric_name}: Error - {e}")
            
            print(f"   📊 Found {len(found_metrics)}/{len(metrics_to_check)} metrics")
            
            if len(found_metrics) == len(metrics_to_check):
                print(f"\n🎉 SUCCESS! All metrics found!")
                print(f"✅ Lab 7 should now show metric data!")
                break
            
            print("   ⏰ Waiting 30 seconds for next check...\n")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Monitoring stopped by user")
        if found_metrics:
            print(f"📊 Found metrics: {', '.join(found_metrics)}")
        else:
            print("🔍 No metrics found yet - keep waiting")

if __name__ == "__main__":
    print("📊 AgentCore Runtime Metrics Monitor")
    print("This script monitors for metrics to appear after Lab 4 invocations")
    print()
    
    monitor_runtime_metrics()
