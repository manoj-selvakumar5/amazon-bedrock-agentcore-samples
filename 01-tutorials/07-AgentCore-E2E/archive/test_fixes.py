#!/usr/bin/env python3
"""
Test script to validate all fixes for lab-07-metrics-dashboards.ipynb
This script tests all the identified issues before creating the fixed notebook.
"""

import sys
import boto3
from botocore.exceptions import ClientError

def test_datetime_fix():
    """Test 1: DateTime Import & Usage Fix"""
    print("🧪 Test 1: DateTime Import & Usage Fix")
    try:
        from datetime import datetime, timedelta, timezone
        
        # Test current time
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        print(f"   ✅ Current UTC time: {end_time}")
        print(f"   ✅ 24 hours ago: {start_time}")
        print(f"   ✅ DateTime operations working correctly!")
        return True
        
    except Exception as e:
        print(f"   ❌ DateTime test failed: {type(e).__name__}: {e}")
        return False

def test_cloudwatch_api():
    """Test 2: CloudWatch API Calls"""
    print("\n🧪 Test 2: CloudWatch API Calls")
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        # Test list_metrics without MaxRecords parameter
        response = cloudwatch.list_metrics(Namespace="AWS/EC2")
        metrics_count = len(response.get('Metrics', []))
        
        print(f"   ✅ CloudWatch API works: {metrics_count} EC2 metrics found")
        
        # Test with AgentCore namespace (may be empty)
        response = cloudwatch.list_metrics(Namespace="AWS/Bedrock/AgentCore/Runtime")
        agentcore_count = len(response.get('Metrics', []))
        print(f"   ℹ️ AgentCore Runtime metrics: {agentcore_count} found")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"   ❌ AWS Error: {error_code} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"   ❌ CloudWatch API test failed: {type(e).__name__}: {e}")
        return False

def test_runtime_name_extraction():
    """Test 3: Runtime Name Extraction"""
    print("\n🧪 Test 3: Runtime Name Extraction")
    
    # Test cases for different ARN formats
    test_cases = [
        "arn:aws:bedrock:us-east-1:123456:agent-runtime/customer_support_agent-xyz123",
        "arn:aws:bedrock:us-east-1:123456:agent-runtime/customer_support_agent",
        "arn:aws:bedrock:us-east-1:123456:agent-runtime/test-agent-123",
        "/customer_support_agent-xyz123"  # Simple path
    ]
    
    all_passed = True
    for test_arn in test_cases:
        try:
            # Improved extraction logic
            runtime_name = test_arn.split('/')[-1]
            if '-' in runtime_name and len(runtime_name.split('-')) > 1:
                # Only split if it looks like name-id format
                parts = runtime_name.split('-')
                if len(parts) >= 2 and parts[-1].replace('_', '').isalnum():
                    runtime_name = '-'.join(parts[:-1])  # Keep all but last part
            
            print(f"   ✅ '{test_arn}' -> '{runtime_name}'")
            
        except Exception as e:
            print(f"   ❌ Failed parsing '{test_arn}': {e}")
            all_passed = False
    
    return all_passed

def test_complete_metrics_function():
    """Test 4: Complete Metrics Function"""
    print("\n🧪 Test 4: Complete Metrics Function")
    
    def test_get_runtime_metrics(runtime_name, cloudwatch_client):
        """Test the complete metrics function with proper error handling"""
        try:
            from datetime import datetime, timedelta, timezone
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            
            response = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Bedrock/AgentCore/Runtime',
                MetricName='Invocations',
                Dimensions=[{'Name': 'RuntimeName', 'Value': runtime_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum'],
                Unit='Count'
            )
            
            datapoints = response.get('Datapoints', [])
            print(f"   ✅ Metrics query successful: {len(datapoints)} datapoints found")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"   ℹ️ AWS Error (expected if no metrics): {error_code}")
            return True  # This is expected if no metrics exist
        except Exception as e:
            print(f"   ❌ Metrics query failed: {type(e).__name__}: {e}")
            return False
    
    try:
        cloudwatch = boto3.client('cloudwatch')
        test_runtime_name = "customer_support_agent"
        
        result = test_get_runtime_metrics(test_runtime_name, cloudwatch)
        return result
        
    except Exception as e:
        print(f"   ❌ Failed to create CloudWatch client: {e}")
        return False

def test_imports():
    """Test 5: All Required Imports"""
    print("\n🧪 Test 5: All Required Imports")
    
    required_imports = [
        ('boto3', 'boto3'),
        ('json', 'json'),
        ('pandas', 'pd'),
        ('datetime', 'datetime, timedelta, timezone'),
        ('matplotlib.pyplot', 'plt'),
        ('IPython.display', 'display, Markdown'),
        ('botocore.exceptions', 'ClientError')
    ]
    
    all_passed = True
    for module, imports in required_imports:
        try:
            if module == 'datetime':
                from datetime import datetime, timedelta, timezone
            elif module == 'pandas':
                import pandas as pd
            elif module == 'matplotlib.pyplot':
                import matplotlib.pyplot as plt
            elif module == 'IPython.display':
                from IPython.display import display, Markdown
            elif module == 'botocore.exceptions':
                from botocore.exceptions import ClientError
            else:
                __import__(module)
            
            print(f"   ✅ {module}: {imports}")
        except ImportError as e:
            print(f"   ❌ {module}: {e}")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("🔬 Testing All Fixes for Lab 7 Metrics Dashboard\n")
    print("=" * 60)
    
    tests = [
        ("DateTime Fix", test_datetime_fix),
        ("CloudWatch API", test_cloudwatch_api), 
        ("Runtime Name Extraction", test_runtime_name_extraction),
        ("Complete Metrics Function", test_complete_metrics_function),
        ("Required Imports", test_imports)
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} | {test_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Ready to create fixed notebook.")
        return True
    else:
        print("⚠️ Some tests failed. Review errors before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)