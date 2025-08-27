#!/usr/bin/env python3
"""
Script to invoke the AgentCore Runtime to generate metrics
This will create the data points needed for the lab-07 dashboard
"""

import boto3
import json
import time
import uuid
from datetime import datetime

def invoke_agentcore_runtime():
    """Invoke the AgentCore Runtime to generate metrics"""
    
    print("🚀 INVOKING AGENTCORE RUNTIME TO GENERATE METRICS")
    print("=" * 60)
    
    # Initialize the AgentCore Runtime client
    try:
        runtime_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        print("✅ AgentCore Runtime client initialized")
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        return
    
    # Runtime configuration
    runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:533267284022:runtime/customer_support_agent-b0Ilb5ACG7"
    
    # Test queries to generate different types of metrics
    test_queries = [
        "What's your return policy?",
        "I need help with a MacBook Pro issue",
        "Can you recommend gaming headphones?",
        "What laptop would you suggest for programming?",
        "Tell me about warranty options"
    ]
    
    print(f"🎯 Runtime ARN: {runtime_arn}")
    print(f"📝 Will send {len(test_queries)} test queries to generate metrics")
    print()
    
    success_count = 0
    error_count = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"📤 Query {i}/{len(test_queries)}: {query}")
        
        try:
            # Create a unique session for each query
            session_id = f"metrics-test-{uuid.uuid4()}"
            
            # Invoke the runtime using the correct method
            response = runtime_client.invoke_agent(
                agentId=runtime_arn,  # Use agentId parameter
                agentAliasId='TSTALIASID',  # Default test alias
                sessionId=session_id,
                inputText=query
            )
            
            # Process the streaming response
            output_text = ""
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        output_text += chunk['bytes'].decode('utf-8')
            
            print(f"   ✅ Success! Response length: {len(output_text)} chars")
            print(f"   📊 Session ID: {session_id}")
            success_count += 1
            
            # Small delay between requests
            time.sleep(2)
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            error_count += 1
            
            # If it's a throttling error, wait longer
            if "Throttled" in str(e):
                print("   ⏳ Throttled - waiting 10 seconds...")
                time.sleep(10)
            else:
                time.sleep(2)
    
    print()
    print("📊 INVOCATION SUMMARY:")
    print(f"   ✅ Successful invocations: {success_count}")
    print(f"   ❌ Failed invocations: {error_count}")
    print(f"   📈 Metrics should appear in 5-10 minutes")
    
    if success_count > 0:
        print(f"\n🎉 SUCCESS! Generated runtime metrics:")
        print(f"   • Invocations: {success_count}")
        print(f"   • Sessions: {success_count}")
        print(f"   • Latency: Response times for each call")
        print(f"   • Duration: Processing time for each call")
        
        print(f"\n⏳ Next steps:")
        print(f"   1. Wait 5-10 minutes for metrics to appear in CloudWatch")
        print(f"   2. Re-run the lab-07 notebook cells")
        print(f"   3. Check your CloudWatch dashboard")
        print(f"   4. Metrics will show in AWS/Bedrock-AgentCore namespace")
    else:
        print(f"\n⚠️ No successful invocations - check your runtime configuration")

def test_runtime_connection():
    """Test if we can connect to the runtime"""
    
    print("🔍 TESTING RUNTIME CONNECTION")
    print("-" * 40)
    
    try:
        runtime_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        
        # Try to get runtime details (this will validate the ARN)
        runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:533267284022:runtime/customer_support_agent-b0Ilb5ACG7"
        
        print(f"📋 Testing connection to: {runtime_arn}")
        
        # Try a simple invoke to test connectivity
        session_id = f"connection-test-{uuid.uuid4()}"
        
        response = runtime_client.invoke_agent(
            agentId=runtime_arn,
            agentAliasId='TSTALIASID',
            sessionId=session_id,
            inputText="Hello, are you working?"
        )
        
        # Just check if we get a response
        response_received = False
        for event in response['completion']:
            if 'chunk' in event:
                response_received = True
                break
        
        if response_received:
            print("   ✅ Runtime is accessible and responding")
            return True
        else:
            print("   ⚠️ Runtime accessible but no response received")
            return False
            
    except Exception as e:
        print(f"   ❌ Runtime connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🎯 AgentCore Runtime Metrics Generator")
    print("This script will invoke your runtime to generate CloudWatch metrics")
    print()
    
    # Test connection first
    if test_runtime_connection():
        print()
        # Proceed with metric generation
        invoke_agentcore_runtime()
    else:
        print("\n❌ Cannot connect to runtime - check your Lab 4 deployment")
        print("💡 Make sure your runtime is deployed and accessible")
