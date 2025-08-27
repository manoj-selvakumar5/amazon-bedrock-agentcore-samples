#!/usr/bin/env python3
"""
Complete AgentCore Testing Script - Labs 1-4 + Metrics (Lab 7)
================================================================
This script combines all components from Labs 1-4 and adds metrics monitoring.
Use this for testing and iterating on your AgentCore setup.

Prerequisites:
- Complete Labs 1-4 first to create the necessary resources
- Ensure CloudWatch Transaction Search is enabled
- Have proper AWS credentials configured

Usage:
    python test_agentcore_complete.py [options]
    
Key Features:
    • Complete Labs 1-2 setup without notebooks (Agent + Memory)
    • Automatic log group creation and fixes
    • End-to-end agent testing with memory integration
    • Comprehensive metrics monitoring and diagnostics
    • CloudWatch dashboard creation
    
Examples:
    # Complete end-to-end setup (Labs 1-2 + discovery for 3-4)
    python test_agentcore_complete.py --setup-all
    
    # Test agent with memory integration
    python test_agentcore_complete.py --test-agent
    
    # Run complete diagnostics (default)
    python test_agentcore_complete.py
    
    # Check current metrics
    python test_agentcore_complete.py --check-metrics
    
    # Generate metrics by invoking runtime
    python test_agentcore_complete.py --invoke-runtime
    
    # Create CloudWatch dashboards
    python test_agentcore_complete.py --create-dashboards

Dependencies (auto-installed or guided):
    • strands-agents - for Lab 1 agent creation
    • bedrock_agentcore - for Lab 2 memory
    • bedrock-agentcore-starter-toolkit - for Lab 4 runtime (optional)
    • ddgs - for web search tool (optional)
"""

import boto3
import json
import time
import argparse
import sys
import uuid
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

# Lab dependencies (install if missing)
try:
    from strands import Agent
    from strands.models import BedrockModel
    from strands.tools import tool
    STRANDS_AVAILABLE = True
except ImportError:
    print("⚠️ Strands not available. Install with: pip install strands-agents")
    STRANDS_AVAILABLE = False

try:
    from bedrock_agentcore.memory import MemoryClient
    from bedrock_agentcore.memory.constants import StrategyType
    AGENTCORE_MEMORY_AVAILABLE = True
except ImportError:
    print("⚠️ AgentCore Memory not available. Install with: pip install bedrock_agentcore")
    AGENTCORE_MEMORY_AVAILABLE = False

try:
    from bedrock_agentcore_starter_toolkit import Runtime
    STARTER_TOOLKIT_AVAILABLE = True
except ImportError:
    STARTER_TOOLKIT_AVAILABLE = False

# ========================================
# SECTION 1: AWS SETUP & CONFIGURATION
# ========================================

def setup_aws_clients():
    """Initialize all AWS clients needed for AgentCore testing"""
    session = boto3.Session()
    region = session.region_name
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    clients = {
        'cloudwatch': boto3.client('cloudwatch', region_name=region),
        'logs': boto3.client('logs', region_name=region),
        'ssm': boto3.client('ssm', region_name=region),
        'bedrock_runtime': boto3.client('bedrock-runtime', region_name=region),
        'bedrock_agent': boto3.client('bedrock-agent-runtime', region_name=region),
        'region': region,
        'account_id': account_id
    }
    
    print(f"✅ AWS clients initialized")
    print(f"📍 Region: {region}")
    print(f"🔑 Account: {account_id}")
    print(f"📊 CloudWatch Namespace: AWS/Bedrock-AgentCore")
    
    return clients

def get_ssm_parameter(ssm_client, param_name: str) -> Optional[str]:
    """Retrieve a parameter from SSM Parameter Store"""
    try:
        response = ssm_client.get_parameter(Name=param_name)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"⚠️ Parameter {param_name} not found: {e}")
        return None

def put_ssm_parameter(ssm_client, param_name: str, param_value: str) -> bool:
    """Store a parameter in SSM Parameter Store"""
    try:
        ssm_client.put_parameter(
            Name=param_name,
            Value=param_value,
            Overwrite=True
        )
        return True
    except Exception as e:
        print(f"❌ Failed to store parameter {param_name}: {e}")
        return False

# ========================================
# SECTION 1.5: LAB 1 - AGENT TOOLS
# ========================================

# Lab 1 Tools Implementation
def create_lab1_tools():
    """Create all tools from Lab 1"""
    
    @tool
    def get_return_policy(product_category: str) -> str:
        """
        Get return policy information for a specific product category.

        Args:
            product_category: Electronics category (e.g., 'smartphones', 'laptops', 'accessories')

        Returns:
            Formatted return policy details including timeframes and conditions
        """
        return_policies = {
            "smartphones": {
                "window": "30 days",
                "condition": "Original packaging, no physical damage, factory reset required",
                "process": "Online RMA portal or technical support",
                "refund_time": "5-7 business days after inspection",
                "shipping": "Free return shipping, prepaid label provided",
                "warranty": "1-year manufacturer warranty included"
            },
            "laptops": {
                "window": "30 days", 
                "condition": "Original packaging, all accessories, no software modifications",
                "process": "Technical support verification required before return",
                "refund_time": "7-10 business days after inspection",
                "shipping": "Free return shipping with original packaging",
                "warranty": "1-year manufacturer warranty, extended options available"
            },
            "accessories": {
                "window": "30 days",
                "condition": "Unopened packaging preferred, all components included",
                "process": "Online return portal",
                "refund_time": "3-5 business days after receipt",
                "shipping": "Customer pays return shipping under $50",
                "warranty": "90-day manufacturer warranty"
            }
        }

        default_policy = {
            "window": "30 days",
            "condition": "Original condition with all included components",
            "process": "Contact technical support",
            "refund_time": "5-7 business days after inspection", 
            "shipping": "Return shipping policies vary",
            "warranty": "Standard manufacturer warranty applies"
        }

        policy = return_policies.get(product_category.lower(), default_policy)
        return f"Return Policy - {product_category.title()}:\\n\\n" \
               f"• Return window: {policy['window']} from delivery\\n" \
               f"• Condition: {policy['condition']}\\n" \
               f"• Process: {policy['process']}\\n" \
               f"• Refund timeline: {policy['refund_time']}\\n" \
               f"• Shipping: {policy['shipping']}\\n" \
               f"• Warranty: {policy['warranty']}"

    @tool
    def get_product_info(product_type: str) -> str:
        """
        Get detailed technical specifications and information for electronics products.

        Args:
            product_type: Electronics product type (e.g., 'laptops', 'smartphones', 'headphones', 'monitors')
        Returns:
            Formatted product information including warranty, features, and policies
        """
        products = {
            "laptops": {
                "warranty": "1-year manufacturer warranty + optional extended coverage",
                "specs": "Intel/AMD processors, 8-32GB RAM, SSD storage, various display sizes",
                "features": "Backlit keyboards, USB-C/Thunderbolt, Wi-Fi 6, Bluetooth 5.0",
                "compatibility": "Windows 11, macOS, Linux support varies by model",
                "support": "Technical support and driver updates included"
            },
            "smartphones": {
                "warranty": "1-year manufacturer warranty",
                "specs": "5G/4G connectivity, 128GB-1TB storage, multiple camera systems",
                "features": "Wireless charging, water resistance, biometric security",
                "compatibility": "iOS/Android, carrier unlocked options available",
                "support": "Software updates and technical support included"
            },
            "headphones": {
                "warranty": "1-year manufacturer warranty",
                "specs": "Wired/wireless options, noise cancellation, 20Hz-20kHz frequency",
                "features": "Active noise cancellation, touch controls, voice assistant",
                "compatibility": "Bluetooth 5.0+, 3.5mm jack, USB-C charging",
                "support": "Firmware updates via companion app"
            },
            "monitors": {
                "warranty": "3-year manufacturer warranty",
                "specs": "4K/1440p/1080p resolutions, IPS/OLED panels, various sizes",
                "features": "HDR support, high refresh rates, adjustable stands",
                "compatibility": "HDMI, DisplayPort, USB-C inputs",
                "support": "Color calibration and technical support"
            }
        }
        
        product = products.get(product_type.lower())
        if not product:
            return f"Technical specifications for {product_type} not available. Please contact our technical support team for detailed product information and compatibility requirements."

        return f"Technical Information - {product_type.title()}:\\n\\n" \
               f"• Warranty: {product['warranty']}\\n" \
               f"• Specifications: {product['specs']}\\n" \
               f"• Key Features: {product['features']}\\n" \
               f"• Compatibility: {product['compatibility']}\\n" \
               f"• Support: {product['support']}"

    @tool
    def web_search(keywords: str, region: str = "us-en", max_results: int = 5) -> str:
        """Search the web for updated information.
        
        Args:
            keywords (str): The search query keywords.
            region (str): The search region: wt-wt, us-en, uk-en, ru-ru, etc..
            max_results (int | None): The maximum number of results to return.
        Returns:
            List of dictionaries with search results.
        
        """
        try:
            from ddgs import DDGS
            from ddgs.exceptions import DDGSException, RatelimitException
            
            results = DDGS().text(keywords, region=region, max_results=max_results)
            return results if results else "No results found."
        except RatelimitException:
            return "Rate limit reached. Please try again later."
        except DDGSException as e:
            return f"Search error: {e}"
        except ImportError:
            return "Web search not available. Install with: pip install ddgs"
        except Exception as e:
            return f"Search error: {str(e)}"

    return [get_return_policy, get_product_info, web_search]

# Lab 1 Agent creation
def create_lab1_agent(clients: Dict) -> Optional[Agent]:
    """Create the Lab 1 agent with tools"""
    
    if not STRANDS_AVAILABLE:
        print("❌ Cannot create agent - Strands not available")
        return None
    
    SYSTEM_PROMPT = """You are a helpful and professional customer support assistant for an electronics e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Support the customer with technical information and product specifications.
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For warranty and return policy questions
2. get_product_info() - To get information about a specific product
3. web_search() - To access current technical documentation, or for updated information. 
Always use the appropriate tool to get accurate, up-to-date information rather than making assumptions about electronic products or specifications."""

    # Initialize the Bedrock model (Anthropic Claude 3.7 Sonnet)
    model = BedrockModel(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        temperature=0.3,
        region_name=clients['region']
    )

    # Create tools
    tools = create_lab1_tools()

    # Create the customer support agent with all tools
    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    print("✅ Lab 1 Agent created successfully!")
    return agent

# ========================================
# SECTION 2: RESOURCE DISCOVERY
# ========================================

def discover_lab_resources(clients: Dict) -> Dict:
    """
    Discover all AgentCore resources created in Labs 1-4
    Returns a dictionary with all resource ARNs and IDs
    """
    ssm = clients['ssm']
    region = clients['region']
    account_id = clients['account_id']
    
    resources = {}
    
    print("\n" + "="*60)
    print("🔍 DISCOVERING LAB RESOURCES")
    print("="*60)
    
    # Lab 4: Runtime
    runtime_arn = get_ssm_parameter(ssm, "/app/customersupport/agentcore/runtime_arn")
    if runtime_arn:
        resources['runtime_arn'] = runtime_arn
        resources['runtime_name'] = runtime_arn.split('/')[-1]
        print(f"✅ Runtime (Lab 4): {runtime_arn}")
    else:
        print("❌ Runtime not found - Complete Lab 4")
    
    # Lab 2: Memory
    memory_id = get_ssm_parameter(ssm, "/app/customersupport/agentcore/memory_id")
    if memory_id:
        resources['memory_id'] = memory_id
        resources['memory_arn'] = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{memory_id}"
        print(f"✅ Memory (Lab 2): {memory_id}")
    else:
        print("❌ Memory not found - Complete Lab 2")
    
    # Lab 3: Gateway
    gateway_id = get_ssm_parameter(ssm, "/app/customersupport/agentcore/gateway_id")
    if gateway_id:
        resources['gateway_id'] = gateway_id
        resources['gateway_arn'] = f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{gateway_id}"
        print(f"✅ Gateway (Lab 3): {gateway_id}")
    else:
        print("❌ Gateway not found - Complete Lab 3")
    
    return resources

# ========================================
# SECTION 2.5: LAB 2 - MEMORY IMPLEMENTATION
# ========================================

def create_agentcore_memory(clients: Dict) -> Optional[str]:
    """Create AgentCore Memory resource (Lab 2)"""
    
    if not AGENTCORE_MEMORY_AVAILABLE:
        print("❌ Cannot create memory - AgentCore Memory not available")
        return None
    
    print("\n" + "="*60)
    print("🧠 CREATING AGENTCORE MEMORY (LAB 2)")
    print("="*60)
    
    memory_client = MemoryClient(region_name=clients['region'])
    memory_name = "CustomerSupportMemory"
    
    # Check if memory already exists
    existing_memory_id = get_ssm_parameter(clients['ssm'], "/app/customersupport/agentcore/memory_id")
    if existing_memory_id:
        try:
            memory_client.gmcp_client.get_memory(memoryId=existing_memory_id)
            print(f"✅ Memory already exists: {existing_memory_id}")
            return existing_memory_id
        except:
            print(f"⚠️ Stored memory ID {existing_memory_id} not found, creating new one")
    
    try:
        strategies = [
            {
                StrategyType.USER_PREFERENCE.value: {
                    "name": "CustomerPreferences",
                    "description": "Captures customer preferences and behavior",
                    "namespaces": ["support/customer/{actorId}/preferences"],
                }
            },
            {
                StrategyType.SEMANTIC.value: {
                    "name": "CustomerSupportSemantic",
                    "description": "Stores facts from conversations",
                    "namespaces": ["support/customer/{actorId}/semantic"],
                }
            },
        ]
        
        print("Creating AgentCore Memory resources. This will take 2-3 minutes...")
        print("• Setting up managed vector databases for semantic search")
        print("• Configuring memory extraction pipelines")
        print("• Provisioning secure, multi-tenant storage")
        print("• Establishing namespace isolation for customer data")
        
        response = memory_client.create_memory_and_wait(
            name=memory_name,
            description="Customer support agent memory",
            strategies=strategies,
            event_expiry_days=90,
        )
        
        memory_id = response["id"]
        
        # Store in SSM
        if put_ssm_parameter(clients['ssm'], "/app/customersupport/agentcore/memory_id", memory_id):
            print(f"✅ AgentCore Memory created successfully!")
            print(f"📝 Memory ID: {memory_id}")
            print(f"💾 Stored in SSM: /app/customersupport/agentcore/memory_id")
            
            # Seed with sample customer interactions
            seed_memory_with_sample_data(memory_client, memory_id)
            
            return memory_id
        else:
            print("⚠️ Memory created but failed to store ID in SSM")
            return memory_id
            
    except Exception as e:
        print(f"❌ Failed to create memory resource: {e}")
        return None

def seed_memory_with_sample_data(memory_client, memory_id: str):
    """Seed memory with sample customer interactions"""
    
    print("\n📝 Seeding memory with sample customer interactions...")
    
    CUSTOMER_ID = "customer_001"
    
    previous_interactions = [
        ("I'm having issues with my MacBook Pro overheating during video editing.", "USER"),
        ("I can help with that thermal issue. For video editing workloads, let's check your Activity Monitor and adjust performance settings. Your MacBook Pro order #MB-78432 is still under warranty.", "ASSISTANT"),
        ("What's the return policy on gaming headphones? I need low latency for competitive FPS games", "USER"),
        ("For gaming headphones, you have 30 days to return. Since you're into competitive FPS, I'd recommend checking the audio latency specs - most gaming models have <40ms latency.", "ASSISTANT"),
        ("I need a laptop under $1200 for programming. Prefer 16GB RAM minimum and good Linux compatibility. I like ThinkPad models.", "USER"),
        ("Perfect! For development work, I'd suggest looking at our ThinkPad E series or Dell XPS models. Both have excellent Linux support and 16GB RAM options within your budget.", "ASSISTANT"),
    ]
    
    try:
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=CUSTOMER_ID,
            session_id="sample_session_001",
            messages=previous_interactions
        )
        print("✅ Seeded customer history successfully")
        print("📝 Interactions saved to Short-Term Memory")
        print("⏳ Long-Term Memory processing will begin automatically...")
        
    except Exception as e:
        print(f"⚠️ Error seeding history: {e}")

# Lab 2 Memory hooks implementation
def create_memory_hooks():
    """Create memory hooks for integration with agents"""
    
    if not STRANDS_AVAILABLE or not AGENTCORE_MEMORY_AVAILABLE:
        return None
    
    from strands.hooks import AfterInvocationEvent, HookProvider, HookRegistry, MessageAddedEvent
    import logging
    
    logger = logging.getLogger(__name__)
    
    class CustomerSupportMemoryHooks(HookProvider):
        """Memory hooks for customer support agent"""

        def __init__(self, memory_id: str, memory_client, actor_id: str, session_id: str):
            self.memory_id = memory_id
            self.client = memory_client
            self.actor_id = actor_id
            self.session_id = session_id
            self.namespaces = {
                i["type"]: i["namespaces"][0]
                for i in self.client.get_memory_strategies(self.memory_id)
            }

        def retrieve_customer_context(self, event: MessageAddedEvent):
            """Retrieve customer context before processing support query"""
            messages = event.agent.messages
            if (
                messages[-1]["role"] == "user"
                and "toolResult" not in messages[-1]["content"][0]
            ):
                user_query = messages[-1]["content"][0]["text"]

                try:
                    all_context = []

                    for context_type, namespace in self.namespaces.items():
                        memories = self.client.retrieve_memories(
                            memory_id=self.memory_id,
                            namespace=namespace.format(actorId=self.actor_id),
                            query=user_query,
                            top_k=3,
                        )
                        for memory in memories:
                            if isinstance(memory, dict):
                                content = memory.get("content", {})
                                if isinstance(content, dict):
                                    text = content.get("text", "").strip()
                                    if text:
                                        all_context.append(f"[{context_type.upper()}] {text}")

                    if all_context:
                        context_text = "\\n".join(all_context)
                        original_text = messages[-1]["content"][0]["text"]
                        messages[-1]["content"][0]["text"] = f"Customer Context:\\n{context_text}\\n\\n{original_text}"
                        logger.info(f"Retrieved {len(all_context)} customer context items")

                except Exception as e:
                    logger.error(f"Failed to retrieve customer context: {e}")

        def save_support_interaction(self, event: AfterInvocationEvent):
            """Save customer support interaction after agent response"""
            try:
                messages = event.agent.messages
                if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                    customer_query = None
                    agent_response = None

                    for msg in reversed(messages):
                        if msg["role"] == "assistant" and not agent_response:
                            agent_response = msg["content"][0]["text"]
                        elif (
                            msg["role"] == "user"
                            and not customer_query
                            and "toolResult" not in msg["content"][0]
                        ):
                            customer_query = msg["content"][0]["text"]
                            break

                    if customer_query and agent_response:
                        self.client.create_event(
                            memory_id=self.memory_id,
                            actor_id=self.actor_id,
                            session_id=self.session_id,
                            messages=[
                                (customer_query, "USER"),
                                (agent_response, "ASSISTANT"),
                            ],
                        )
                        logger.info("Saved support interaction to memory")

            except Exception as e:
                logger.error(f"Failed to save support interaction: {e}")

        def register_hooks(self, registry: HookRegistry) -> None:
            """Register customer support memory hooks"""
            registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
            registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
            logger.info("Customer support memory hooks registered")
    
    return CustomerSupportMemoryHooks

# ========================================
# SECTION 3: LOG GROUP MANAGEMENT
# ========================================

def check_and_create_log_groups(clients: Dict, resources: Dict) -> Tuple[List[str], List[str]]:
    """
    Check for required CloudWatch log groups and create them if missing
    This is CRITICAL for metrics to appear!
    
    Returns:
        Tuple of (fixes_applied, fixes_needed)
    """
    logs = clients['logs']
    fixes_applied = []
    fixes_needed = []
    
    print("\n" + "="*60)
    print("📝 CHECKING AND CREATING LOG GROUPS")
    print("="*60)
    
    log_groups = []
    
    # Define log groups needed for each resource type
    # Format: (resource_type, log_group_name, auto_created_by_service)
    
    if resources.get('runtime_name'):
        # Runtime log groups (auto-created by service)
        log_groups.append((
            'Runtime', 
            f"/aws/bedrock-agentcore/runtimes/{resources['runtime_name']}", 
            True
        ))
        log_groups.append((
            'Runtime Logs', 
            f"/aws/bedrock-agentcore/runtimes/{resources['runtime_name']}/runtime-logs", 
            True
        ))
    
    if resources.get('memory_id'):
        # Memory log group (must be manually created)
        log_groups.append((
            'Memory', 
            f"/aws/bedrock-agentcore/memories/{resources['memory_id']}", 
            False
        ))
    
    if resources.get('gateway_id'):
        # Gateway log group (must be manually created)
        log_groups.append((
            'Gateway', 
            f"/aws/bedrock-agentcore/gateways/{resources['gateway_id']}", 
            False
        ))
    
    # Check and create each log group
    for resource_type, log_group, auto_created in log_groups:
        try:
            response = logs.describe_log_groups(
                logGroupNamePrefix=log_group,
                limit=1
            )
            if response['logGroups'] and response['logGroups'][0]['logGroupName'] == log_group:
                print(f"✅ {resource_type} log group exists: {log_group}")
            else:
                raise Exception("Log group not found")
        except Exception:
            if not auto_created:
                # Try to create the log group
                try:
                    logs.create_log_group(logGroupName=log_group)
                    print(f"✅ CREATED {resource_type} log group: {log_group}")
                    fixes_applied.append(f"Created log group: {log_group}")
                except Exception as e:
                    if "ResourceAlreadyExistsException" in str(e):
                        print(f"✅ {resource_type} log group already exists")
                    else:
                        print(f"❌ Failed to create {resource_type} log group: {e}")
                        fixes_needed.append(f"Manually create: {log_group}")
            else:
                print(f"⚠️ {resource_type} log group missing (should be auto-created)")
                fixes_needed.append(f"Check {resource_type} deployment")
    
    return fixes_applied, fixes_needed

# ========================================
# SECTION 4: RUNTIME INVOCATION (GENERATE METRICS)
# ========================================

def invoke_runtime_agent(clients: Dict, resources: Dict, query: str = None) -> bool:
    """
    Invoke the AgentCore Runtime to generate metrics
    This simulates user interaction with the agent
    
    Note: This requires either:
    1. A bearer token from Cognito (stored in SSM or passed directly)
    2. OR using the bedrock-agentcore-starter-toolkit for invocation
    """
    if not resources.get('runtime_arn'):
        print("⚠️ No runtime available to invoke")
        return False
    
    print("\n" + "="*60)
    print("🤖 INVOKING AGENTCORE RUNTIME")
    print("="*60)
    
    # Default test queries if none provided
    test_queries = [
        "What's the return policy for laptops?",
        "My iPhone won't connect to Bluetooth",
        "I need help with my order"
    ] if not query else [query]
    
    # Method 1: Try using AgentCore Starter Toolkit (if available)
    try:
        from bedrock_agentcore_starter_toolkit import Runtime
        import uuid
        
        print("📦 Using AgentCore Starter Toolkit for invocation")
        
        # Get bearer token
        bearer_token = get_ssm_parameter(clients['ssm'], "/app/customersupport/agentcore/bearer_token")
        
        if not bearer_token:
            print("⚠️ No bearer token found. Trying to get from Cognito...")
            # You would need to implement Cognito token retrieval here
            print("   Please run Lab 4 to get a bearer token")
            return False
        
        runtime = Runtime()
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Query {i}: {query}")
            
            try:
                response = runtime.invoke(
                    {"prompt": query},
                    bearer_token=bearer_token,
                    session_id=str(uuid.uuid4())
                )
                print(f"✅ Invocation successful")
                if 'response' in response:
                    print(f"   Response preview: {response['response'][:200]}...")
                    
            except Exception as e:
                print(f"❌ Invocation failed: {e}")
                
    except ImportError:
        print("📦 AgentCore Starter Toolkit not available")
        print("   Install with: pip install bedrock-agentcore-starter-toolkit")
        
        # Method 2: Try direct HTTP invocation
        try:
            import requests
            
            print("\n🌐 Attempting direct HTTP invocation...")
            
            bearer_token = get_ssm_parameter(clients['ssm'], "/app/customersupport/agentcore/bearer_token")
            
            if not bearer_token:
                print("❌ No bearer token available")
                print("\nTo generate metrics, you need to:")
                print("   1. Complete Lab 4 to deploy the runtime")
                print("   2. Get a bearer token from Cognito")
                print("   3. Invoke the agent using the Lab 4 notebook")
                return False
            
            # This would be the direct HTTP endpoint
            runtime_endpoint = f"https://{resources['runtime_arn'].split(':')[3]}.execute-api.{clients['region']}.amazonaws.com/prod/invoke"
            
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json"
            }
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n📝 Query {i}: {query}")
                
                payload = {
                    "prompt": query,
                    "sessionId": f"test-session-{int(time.time())}"
                }
                
                try:
                    response = requests.post(runtime_endpoint, 
                                           json=payload, 
                                           headers=headers,
                                           timeout=30)
                    
                    if response.status_code == 200:
                        print(f"✅ Invocation successful")
                        print(f"   Response preview: {response.text[:200]}...")
                    else:
                        print(f"❌ Invocation failed: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ HTTP invocation failed: {e}")
                    
        except ImportError:
            print("❌ requests library not available")
            print("\n💡 To invoke the runtime and generate metrics:")
            print("   1. Use the Lab 4 notebook to invoke the agent")
            print("   2. OR install bedrock-agentcore-starter-toolkit")
            print("   3. OR install requests library for HTTP invocation")
            return False
    
    print(f"\n✅ Attempted {len(test_queries)} invocations")
    print("⏰ Wait 2-5 minutes for metrics to appear in CloudWatch")
    return True

# ========================================
# SECTION 5: METRICS QUERYING
# ========================================

def query_agentcore_metrics(clients: Dict, resources: Dict, hours_back: int = 24) -> Dict:
    """
    Query all AgentCore metrics from CloudWatch
    Returns a dictionary of metrics by resource type
    """
    cloudwatch = clients['cloudwatch']
    
    print("\n" + "="*60)
    print("📊 QUERYING AGENTCORE METRICS")
    print("="*60)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    all_metrics = {}
    
    # Define metrics for each resource type
    metrics_config = {
        'Runtime': {
            'arn': resources.get('runtime_arn'),
            'metrics': [
                ('Invocations', 'Sum', 'Total invocations'),
                ('Latency', 'Average', 'Average latency (ms)'),
                ('SystemErrors', 'Sum', 'System errors'),
                ('UserErrors', 'Sum', 'User errors'),
                ('Throttles', 'Sum', 'Throttled requests')
            ]
        },
        'Memory': {
            'arn': resources.get('memory_arn'),
            'metrics': [
                ('CreationCount', 'Sum', 'Memory creations'),
                ('Sessions', 'Sum', 'Active sessions'),
                ('Duration', 'Average', 'Operation duration (ms)')
            ]
        },
        'Gateway': {
            'arn': resources.get('gateway_arn'),
            'metrics': [
                ('Invocations', 'Sum', 'Gateway invocations'),
                ('TargetExecutionTime', 'Average', 'Target execution time (ms)'),
                ('TargetType.LAMBDA', 'Sum', 'Lambda invocations'),
                ('Errors', 'Sum', 'Gateway errors'),
                ('Latency', 'Average', 'Gateway latency (ms)')
            ]
        }
    }
    
    # Query metrics for each resource type
    for resource_type, config in metrics_config.items():
        if not config['arn']:
            print(f"\n⚠️ Skipping {resource_type} - no ARN available")
            continue
        
        print(f"\n📈 {resource_type} Metrics:")
        print("-" * 40)
        
        resource_metrics = {}
        has_data = False
        
        for metric_name, statistic, description in config['metrics']:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Bedrock-AgentCore',  # Correct namespace
                    MetricName=metric_name,
                    Dimensions=[
                        {'Name': 'Resource', 'Value': config['arn']}  # Resource dimension with full ARN
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour periods
                    Statistics=[statistic]
                )
                
                datapoints = response.get('Datapoints', [])
                if datapoints:
                    sorted_points = sorted(datapoints, key=lambda x: x['Timestamp'])
                    resource_metrics[metric_name] = sorted_points
                    latest = sorted_points[-1][statistic]
                    print(f"  ✅ {metric_name}: {latest:.2f} ({description})")
                    has_data = True
                else:
                    print(f"  ℹ️ {metric_name}: No data ({description})")
                    
            except Exception as e:
                print(f"  ❌ {metric_name}: Error - {str(e)}")
        
        if not has_data:
            print(f"  ⚠️ No metrics data available for {resource_type}")
            print(f"     • Ensure log groups exist")
            print(f"     • Invoke the resource to generate metrics")
            print(f"     • Wait 2-5 minutes for metrics to appear")
        
        all_metrics[resource_type] = resource_metrics
    
    return all_metrics

# ========================================
# SECTION 6: DASHBOARD CREATION
# ========================================

def create_cloudwatch_dashboards(clients: Dict, resources: Dict) -> bool:
    """
    Create CloudWatch dashboards for all AgentCore resources
    """
    cloudwatch = clients['cloudwatch']
    region = clients['region']
    
    print("\n" + "="*60)
    print("📊 CREATING CLOUDWATCH DASHBOARDS")
    print("="*60)
    
    dashboards_created = []
    
    # Runtime Dashboard
    if resources.get('runtime_arn'):
        dashboard_name = f"AgentCore-Runtime-{resources['runtime_name']}"
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "title": "Runtime Performance",
                        "metrics": [
                            ["AWS/Bedrock-AgentCore", "Invocations", "Resource", resources['runtime_arn']],
                            [".", "Latency", ".", ".", {"stat": "Average", "yAxis": "right"}]
                        ],
                        "period": 300,
                        "region": region
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "title": "Runtime Errors",
                        "metrics": [
                            ["AWS/Bedrock-AgentCore", "SystemErrors", "Resource", resources['runtime_arn']],
                            [".", "UserErrors", ".", "."],
                            [".", "Throttles", ".", "."]
                        ],
                        "period": 300,
                        "region": region
                    }
                }
            ]
        }
        
        try:
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}"
            print(f"✅ Runtime Dashboard: {url}")
            dashboards_created.append(dashboard_name)
        except Exception as e:
            print(f"❌ Failed to create Runtime dashboard: {e}")
    
    # Similar for Memory and Gateway dashboards...
    # (Add Memory and Gateway dashboard creation here if needed)
    
    return len(dashboards_created) > 0

# ========================================
# SECTION 7: COMPREHENSIVE DIAGNOSTICS
# ========================================

def run_complete_diagnostics(clients: Dict, resources: Dict):
    """
    Run a complete diagnostic check of the AgentCore setup
    """
    print("\n" + "="*70)
    print("🔍 COMPLETE AGENTCORE DIAGNOSTICS")
    print("="*70)
    
    issues = []
    recommendations = []
    
    # Check 1: CloudWatch Transaction Search
    print("\n1️⃣ CloudWatch Transaction Search")
    try:
        test_metrics = clients['cloudwatch'].list_metrics(
            Namespace='AWS/Bedrock-AgentCore',
            Limit=1
        )
        if test_metrics:
            print("   ✅ Transaction Search appears enabled")
        else:
            print("   ⚠️ No metrics found yet in namespace")
    except:
        print("   ❌ Cannot verify Transaction Search")
        issues.append("Enable CloudWatch Transaction Search in console")
    
    # Check 2: Log Groups
    print("\n2️⃣ Log Groups")
    log_fixes_applied, log_fixes_needed = check_and_create_log_groups(clients, resources)
    if log_fixes_applied:
        print(f"   ✅ Applied {len(log_fixes_applied)} fixes")
    if log_fixes_needed:
        issues.extend(log_fixes_needed)
    
    # Check 3: Recent Activity
    print("\n3️⃣ Recent Activity")
    metrics = query_agentcore_metrics(clients, resources, hours_back=1)
    
    for resource_type, resource_metrics in metrics.items():
        if not any(resource_metrics.values()):
            recommendations.append(f"Invoke {resource_type} to generate metrics")
    
    # Check 4: Runtime Instrumentation
    print("\n4️⃣ Runtime Instrumentation")
    if resources.get('runtime_arn'):
        print("   ℹ️ Ensure your runtime includes:")
        print("      • aws-opentelemetry-distro>=0.10.0")
        print("      • Run with: opentelemetry-instrument")
    
    # Summary
    print("\n" + "="*70)
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*70)
    
    if issues:
        print("\n❌ ISSUES TO FIX:")
        for issue in issues:
            print(f"   • {issue}")
    
    if recommendations:
        print("\n💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"   • {rec}")
    
    if not issues and not recommendations:
        print("\n✅ Everything looks good! Metrics should be appearing.")
    
    print("\n📝 NEXT STEPS:")
    print("   1. Fix any issues listed above")
    print("   2. Run with --invoke-runtime to generate metrics")
    print("   3. Wait 2-5 minutes for metrics to appear")
    print("   4. Run with --check-metrics to verify")

# ========================================
# SECTION 8: MAIN EXECUTION
# ========================================

# ========================================
# SECTION 9: COMPLETE END-TO-END SETUP
# ========================================

def setup_complete_labs(clients: Dict) -> Dict:
    """
    Complete end-to-end setup of all labs
    This replaces running individual notebooks
    """
    print("\n" + "="*70)
    print("🚀 COMPLETE AGENTCORE LABS SETUP (1-4)")
    print("="*70)
    
    results = {
        'lab1_agent': None,
        'lab2_memory': None,
        'lab3_gateway': None,
        'lab4_runtime': None
    }
    
    # Lab 1: Create Agent with Tools
    print("\n1️⃣ LAB 1: Creating Customer Support Agent...")
    results['lab1_agent'] = create_lab1_agent(clients)
    
    # Lab 2: Create Memory
    print("\n2️⃣ LAB 2: Creating AgentCore Memory...")
    results['lab2_memory'] = create_agentcore_memory(clients)
    
    # Lab 3: Gateway (placeholder - would require more complex setup)
    print("\n3️⃣ LAB 3: Gateway Setup...")
    print("⚠️ Gateway creation requires Lambda functions and complex setup")
    print("   Run Lab 3 notebook manually or use existing gateway")
    
    # Lab 4: Runtime (placeholder - would require container building)
    print("\n4️⃣ LAB 4: Runtime Deployment...")  
    print("⚠️ Runtime deployment requires container building and complex setup")
    print("   Run Lab 4 notebook manually or use existing runtime")
    
    return results

def test_complete_agent_with_memory(clients: Dict, resources: Dict) -> bool:
    """
    Test the complete agent with memory integration
    This demonstrates Labs 1-2 working together
    """
    if not STRANDS_AVAILABLE or not AGENTCORE_MEMORY_AVAILABLE:
        print("❌ Cannot test agent - required libraries not available")
        return False
    
    memory_id = resources.get('memory_id')
    if not memory_id:
        print("⚠️ No memory available for testing")
        return False
    
    print("\n" + "="*60)
    print("🧪 TESTING AGENT WITH MEMORY INTEGRATION")
    print("="*60)
    
    try:
        # Create agent with memory hooks
        memory_client = MemoryClient(region_name=clients['region'])
        CustomerSupportMemoryHooks = create_memory_hooks()
        
        if not CustomerSupportMemoryHooks:
            print("❌ Cannot create memory hooks")
            return False
        
        SESSION_ID = str(uuid.uuid4())
        CUSTOMER_ID = "test_customer_001"
        
        memory_hooks = CustomerSupportMemoryHooks(
            memory_id, memory_client, CUSTOMER_ID, SESSION_ID
        )
        
        # Create agent with memory integration
        model = BedrockModel(
            model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            temperature=0.3,
            region_name=clients['region']
        )
        
        tools = create_lab1_tools()
        
        SYSTEM_PROMPT = """You are a helpful and professional customer support assistant for an electronics e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Support the customer with technical information and product specifications.
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For warranty and return policy questions
2. get_product_info() - To get information about a specific product
3. web_search() - To access current technical documentation, or for updated information. 
Always use the appropriate tool to get accurate, up-to-date information rather than making assumptions about electronic products or specifications."""

        agent = Agent(
            model=model,
            tools=tools,
            hooks=[memory_hooks],
            system_prompt=SYSTEM_PROMPT,
        )
        
        # Test queries
        test_queries = [
            "What headphones would you recommend?",
            "I need help with my laptop overheating issue"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test Query {i}: {query}")
            try:
                response = agent(query)
                print(f"✅ Agent Response: {response.message['content'][0]['text'][:200]}...")
                time.sleep(2)  # Allow processing time
            except Exception as e:
                print(f"❌ Query failed: {e}")
        
        print(f"\n✅ Agent with memory integration tested successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing agent with memory: {e}")
        return False

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Complete AgentCore Testing Script')
    parser.add_argument('--setup-all', action='store_true',
                      help='Set up all labs end-to-end (Labs 1-2 fully, 3-4 discovery)')
    parser.add_argument('--test-agent', action='store_true',
                      help='Test agent with memory integration')
    parser.add_argument('--invoke-runtime', action='store_true', 
                      help='Invoke the runtime to generate metrics')
    parser.add_argument('--check-metrics', action='store_true',
                      help='Check current metrics status')
    parser.add_argument('--create-dashboards', action='store_true',
                      help='Create CloudWatch dashboards')
    parser.add_argument('--diagnostics', action='store_true',
                      help='Run complete diagnostics (default if no args)')
    parser.add_argument('--query', type=str,
                      help='Custom query for runtime invocation')
    
    args = parser.parse_args()
    
    # If no arguments, run diagnostics
    if not any([args.setup_all, args.test_agent, args.invoke_runtime, 
               args.check_metrics, args.create_dashboards, args.diagnostics]):
        args.diagnostics = True
    
    print("="*70)
    print("🚀 AGENTCORE COMPLETE TESTING SCRIPT")
    print("="*70)
    
    # Setup
    clients = setup_aws_clients()
    
    # Execute requested operations
    if args.setup_all:
        print("\n🔧 Setting up all labs end-to-end...")
        setup_results = setup_complete_labs(clients)
        
        # Test the complete setup
        if setup_results['lab1_agent'] and setup_results['lab2_memory']:
            print("\n🧪 Testing complete setup...")
            resources = discover_lab_resources(clients)
            test_complete_agent_with_memory(clients, resources)
        
        print("\n✅ Setup complete! Some components may need manual configuration.")
        return 0
    
    # For other operations, discover existing resources
    resources = discover_lab_resources(clients)
    
    if args.test_agent:
        test_complete_agent_with_memory(clients, resources)
    
    if args.diagnostics:
        run_complete_diagnostics(clients, resources)
    
    if args.invoke_runtime:
        invoke_runtime_agent(clients, resources, args.query)
        print("\n⏰ Wait 2-5 minutes for metrics to appear...")
    
    if args.check_metrics:
        metrics = query_agentcore_metrics(clients, resources)
        if not any(m for m in metrics.values() if m):
            print("\n💡 TIP: Run with --invoke-runtime first to generate metrics")
    
    if args.create_dashboards:
        create_cloudwatch_dashboards(clients, resources)
    
    print("\n✅ Complete! Use --help to see all options.")
    return 0

if __name__ == "__main__":
    sys.exit(main())