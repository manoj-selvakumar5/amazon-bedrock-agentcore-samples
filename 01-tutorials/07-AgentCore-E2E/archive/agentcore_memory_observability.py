#!/usr/bin/env python3
"""
AgentCore Memory with Observability
===================================

This module establishes AgentCore Memory with comprehensive observability using OpenTelemetry.
It combines the memory functionality from lab-02-agentcore-memory.ipynb with observability
features from Optional-lab-agentcore-observability.ipynb.

Features:
- AgentCore Memory with Short-Term and Long-Term memory strategies
- OpenTelemetry instrumentation for memory operations
- CloudWatch GenAI Observability integration
- Memory hooks for automatic context retrieval and storage
- Session tracking and correlation
"""

import argparse
import logging
import os
import time
import uuid
from typing import Dict, List, Optional, Tuple

import boto3
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from boto3.session import Session
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from opentelemetry import baggage, context, trace
from strands import Agent
from strands.hooks import (
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)
from strands.models import BedrockModel

# Import lab helpers
from lab_helpers.lab1_strands_agent import (
    MODEL_ID,
    SYSTEM_PROMPT,
    get_product_info,
    get_return_policy,
)
from scripts.utils import get_ssm_parameter, put_ssm_parameter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get tracer for OpenTelemetry
tracer = trace.get_tracer(__name__)


class ObservableMemoryClient:
    """
    Wrapper around MemoryClient that adds OpenTelemetry tracing to memory operations
    """
    
    def __init__(self, region_name: str):
        self.client = MemoryClient(region_name=region_name)
        self.region_name = region_name
    
    def create_memory_and_wait(self, **kwargs):
        """Create memory resource with tracing"""
        with tracer.start_as_current_span("memory.create_memory") as span:
            span.set_attribute("memory.name", kwargs.get("name", ""))
            span.set_attribute("memory.region", self.region_name)
            span.set_attribute("memory.strategies_count", len(kwargs.get("strategies", [])))
            
            try:
                result = self.client.create_memory_and_wait(**kwargs)
                span.set_attribute("memory.id", result["id"])
                span.set_attribute("memory.status", "created")
                logger.info(f"Memory created successfully: {result['id']}")
                return result
            except Exception as e:
                span.set_attribute("memory.status", "failed")
                span.record_exception(e)
                logger.error(f"Failed to create memory: {e}")
                raise
    
    def create_event(self, **kwargs):
        """Create memory event with tracing"""
        with tracer.start_as_current_span("memory.create_event") as span:
            span.set_attribute("memory.id", kwargs.get("memory_id", ""))
            span.set_attribute("memory.actor_id", kwargs.get("actor_id", ""))
            span.set_attribute("memory.session_id", kwargs.get("session_id", ""))
            span.set_attribute("memory.messages_count", len(kwargs.get("messages", [])))
            
            try:
                result = self.client.create_event(**kwargs)
                span.set_attribute("memory.event_status", "created")
                logger.info(f"Memory event created for session {kwargs.get('session_id')}")
                return result
            except Exception as e:
                span.set_attribute("memory.event_status", "failed")
                span.record_exception(e)
                logger.error(f"Failed to create memory event: {e}")
                raise
    
    def retrieve_memories(self, **kwargs):
        """Retrieve memories with tracing"""
        with tracer.start_as_current_span("memory.retrieve_memories") as span:
            span.set_attribute("memory.id", kwargs.get("memory_id", ""))
            span.set_attribute("memory.namespace", kwargs.get("namespace", ""))
            span.set_attribute("memory.query", kwargs.get("query", ""))
            span.set_attribute("memory.top_k", kwargs.get("top_k", 5))
            
            try:
                memories = self.client.retrieve_memories(**kwargs)
                span.set_attribute("memory.retrieved_count", len(memories))
                logger.info(f"Retrieved {len(memories)} memories from namespace {kwargs.get('namespace')}")
                return memories
            except Exception as e:
                span.set_attribute("memory.retrieval_status", "failed")
                span.record_exception(e)
                logger.error(f"Failed to retrieve memories: {e}")
                return []
    
    def get_memory_strategies(self, memory_id: str):
        """Get memory strategies with tracing"""
        with tracer.start_as_current_span("memory.get_strategies") as span:
            span.set_attribute("memory.id", memory_id)
            
            try:
                strategies = self.client.get_memory_strategies(memory_id)
                span.set_attribute("memory.strategies_count", len(strategies))
                return strategies
            except Exception as e:
                span.record_exception(e)
                logger.error(f"Failed to get memory strategies: {e}")
                raise
    
    def list_memories(self):
        """List memories with tracing"""
        with tracer.start_as_current_span("memory.list_memories"):
            try:
                memories = self.client.list_memories()
                logger.info(f"Listed {len(memories)} memories")
                return memories
            except Exception as e:
                logger.error(f"Failed to list memories: {e}")
                return []


class ObservableCustomerSupportMemoryHooks(HookProvider):
    """
    Memory hooks for customer support agent with OpenTelemetry observability
    """
    
    def __init__(
        self, 
        memory_id: str, 
        client: ObservableMemoryClient, 
        actor_id: str, 
        session_id: str
    ):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespaces = {
            i["type"]: i["namespaces"][0]
            for i in self.client.get_memory_strategies(self.memory_id)
        }
        logger.info(f"Memory hooks initialized for actor {actor_id}, session {session_id}")
    
    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve customer context before processing support query"""
        with tracer.start_as_current_span("hooks.retrieve_customer_context") as span:
            messages = event.agent.messages
            if (
                messages[-1]["role"] == "user"
                and "toolResult" not in messages[-1]["content"][0]
            ):
                user_query = messages[-1]["content"][0]["text"]
                span.set_attribute("hooks.user_query", user_query[:100])  # First 100 chars
                span.set_attribute("hooks.actor_id", self.actor_id)
                span.set_attribute("hooks.session_id", self.session_id)
                
                try:
                    all_context = []
                    
                    for context_type, namespace in self.namespaces.items():
                        # Retrieve customer context from each namespace
                        memories = self.client.retrieve_memories(
                            memory_id=self.memory_id,
                            namespace=namespace.format(actorId=self.actor_id),
                            query=user_query,
                            top_k=3,
                        )
                        
                        # Format memories into context strings
                        for memory in memories:
                            if isinstance(memory, dict):
                                content = memory.get("content", {})
                                if isinstance(content, dict):
                                    text = content.get("text", "").strip()
                                    if text:
                                        all_context.append(
                                            f"[{context_type.upper()}] {text}"
                                        )
                    
                    # Inject customer context into the query
                    if all_context:
                        context_text = "\n".join(all_context)
                        original_text = messages[-1]["content"][0]["text"]
                        messages[-1]["content"][0][
                            "text"
                        ] = f"Customer Context:\n{context_text}\n\n{original_text}"
                        
                        span.set_attribute("hooks.context_items", len(all_context))
                        logger.info(f"Retrieved {len(all_context)} customer context items")
                    else:
                        span.set_attribute("hooks.context_items", 0)
                        logger.info("No customer context found")
                
                except Exception as e:
                    span.record_exception(e)
                    logger.error(f"Failed to retrieve customer context: {e}")
    
    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save customer support interaction after agent response"""
        with tracer.start_as_current_span("hooks.save_support_interaction") as span:
            try:
                messages = event.agent.messages
                if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                    # Get last customer query and agent response
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
                        span.set_attribute("hooks.has_interaction", True)
                        span.set_attribute("hooks.query_length", len(customer_query))
                        span.set_attribute("hooks.response_length", len(agent_response))
                        
                        # Save the support interaction
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
                    else:
                        span.set_attribute("hooks.has_interaction", False)
                        logger.info("No interaction to save")
            
            except Exception as e:
                span.record_exception(e)
                logger.error(f"Failed to save support interaction: {e}")
    
    def register_hooks(self, registry: HookRegistry) -> None:
        """Register customer support memory hooks"""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
        logger.info("Customer support memory hooks registered")


class AgentCoreMemoryObservability:
    """
    Main class for establishing AgentCore Memory with Observability
    """
    
    def __init__(self, region_name: str = None):
        self.boto_session = Session()
        self.region = region_name or self.boto_session.region_name
        self.memory_client = ObservableMemoryClient(region_name=self.region)
        self.memory_name = "CustomerSupportMemory"
        self.memory_id = None
        
        # Setup AWS clients
        self.logs_client = boto3.client("logs", region_name=self.region)
        self.sts_client = boto3.client("sts", region_name=self.region)
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        
        logger.info(f"Initialized AgentCore Memory Observability in region {self.region}")
    
    def setup_observability_environment(self):
        """Setup OpenTelemetry environment for observability"""
        with tracer.start_as_current_span("setup.observability_environment") as span:
            log_group_name = "agents/customer-support-assistant-logs"
            log_stream_name = "default"
            service_name = "customer-support-assistant-memory"
            
            span.set_attribute("setup.log_group", log_group_name)
            span.set_attribute("setup.service_name", service_name)
            
            # Create log group
            try:
                self.logs_client.create_log_group(logGroupName=log_group_name)
                logger.info(f"✅ Log group '{log_group_name}' created successfully")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                    logger.info(f"ℹ️ Log group '{log_group_name}' already exists")
                else:
                    logger.error(f"❌ Error creating log group: {e}")
            
            # Create log stream
            try:
                self.logs_client.create_log_stream(
                    logGroupName=log_group_name, logStreamName=log_stream_name
                )
                logger.info(f"✅ Log stream '{log_stream_name}' created successfully")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                    logger.info(f"ℹ️ Log stream '{log_stream_name}' already exists")
                else:
                    logger.error(f"❌ Error creating log stream: {e}")
            
            # Create .env file for OpenTelemetry configuration
            env_config = {
                "AWS_REGION": self.region,
                "AWS_DEFAULT_REGION": self.region,
                "AWS_ACCOUNT_ID": self.account_id,
                "OTEL_PYTHON_DISTRO": "aws_distro",
                "OTEL_PYTHON_CONFIGURATOR": "aws_configurator",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
                "OTEL_TRACES_EXPORTER": "otlp",
                "OTEL_EXPORTER_OTLP_LOGS_HEADERS": f"x-aws-log-group={log_group_name},x-aws-log-stream={log_stream_name},x-aws-metric-namespace=agents",
                "OTEL_RESOURCE_ATTRIBUTES": f"service.name={service_name}",
                "AGENT_OBSERVABILITY_ENABLED": "true"
            }
            
            with open(".env", "w") as f:
                for key, value in env_config.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("✅ Created .env file with OpenTelemetry configuration")
            return env_config
    
    def create_or_get_memory_resource(self):
        """Create or retrieve existing memory resource"""
        with tracer.start_as_current_span("setup.memory_resource") as span:
            try:
                memory_id = get_ssm_parameter("/app/customersupport/agentcore/memory_id")
                self.memory_client.client.gmcp_client.get_memory(memoryId=memory_id)
                self.memory_id = memory_id
                span.set_attribute("memory.action", "retrieved")
                logger.info(f"Retrieved existing memory: {memory_id}")
                return memory_id
            except:
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
                    
                    logger.info("Creating AgentCore Memory resources. This will take 2-3 minutes...")
                    logger.info("Setting up managed vector databases and memory extraction pipelines...")
                    
                    response = self.memory_client.create_memory_and_wait(
                        name=self.memory_name,
                        description="Customer support agent memory with observability",
                        strategies=strategies,
                        event_expiry_days=90,
                    )
                    
                    memory_id = response["id"]
                    self.memory_id = memory_id
                    
                    try:
                        put_ssm_parameter("/app/customersupport/agentcore/memory_id", memory_id)
                    except Exception as e:
                        logger.warning(f"Failed to store memory ID in SSM: {e}")
                    
                    span.set_attribute("memory.action", "created")
                    span.set_attribute("memory.id", memory_id)
                    logger.info(f"✅ Memory created successfully: {memory_id}")
                    return memory_id
                    
                except Exception as e:
                    span.record_exception(e)
                    logger.error(f"Failed to create memory resource: {e}")
                    return None
    
    def seed_customer_history(self, actor_id: str):
        """Seed memory with sample customer interactions"""
        with tracer.start_as_current_span("setup.seed_customer_history") as span:
            span.set_attribute("seed.actor_id", actor_id)
            
            previous_interactions = [
                ("I'm having issues with my MacBook Pro overheating during video editing.", "USER"),
                ("I can help with that thermal issue. Your MacBook Pro order #MB-78432 is still under warranty.", "ASSISTANT"),
                ("What's the return policy on gaming headphones? I need low latency for competitive FPS games", "USER"),
                ("For gaming headphones, you have 30 days to return. For competitive FPS, I'd recommend checking audio latency specs.", "ASSISTANT"),
                ("I need a laptop under $1200 for programming. Prefer 16GB RAM and good Linux compatibility. I like ThinkPad models.", "USER"),
                ("Perfect! For development work, I'd suggest ThinkPad E series with excellent Linux support and 16GB RAM.", "ASSISTANT"),
            ]
            
            span.set_attribute("seed.interactions_count", len(previous_interactions))
            
            if self.memory_id:
                try:
                    self.memory_client.create_event(
                        memory_id=self.memory_id,
                        actor_id=actor_id,
                        session_id="seed_session",
                        messages=previous_interactions
                    )
                    logger.info("✅ Seeded customer history successfully")
                    return True
                except Exception as e:
                    span.record_exception(e)
                    logger.error(f"⚠️ Error seeding history: {e}")
                    return False
            return False
    
    def wait_for_memory_processing(self, actor_id: str, max_retries: int = 6):
        """Wait for Long-Term Memory processing to complete"""
        with tracer.start_as_current_span("memory.wait_for_processing") as span:
            span.set_attribute("memory.actor_id", actor_id)
            span.set_attribute("memory.max_retries", max_retries)
            
            logger.info("🔍 Checking for processed Long-Term Memories...")
            retries = 0
            
            while retries < max_retries:
                memories = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=f"support/customer/{actor_id}/preferences",
                    query="customer preferences and requirements"
                )
                
                if memories:
                    span.set_attribute("memory.processing_time", retries * 10)
                    span.set_attribute("memory.memories_found", len(memories))
                    logger.info(f"✅ Found {len(memories)} preference memories after {retries * 10} seconds!")
                    return memories
                
                retries += 1
                if retries < max_retries:
                    logger.info(f"⏳ Still processing... waiting 10 more seconds (attempt {retries}/{max_retries})")
                    time.sleep(10)
                else:
                    logger.warning("⚠️ Memory processing is taking longer than expected")
                    break
            
            return []
    
    def create_agent_with_memory_hooks(self, actor_id: str, session_id: str):
        """Create a Strands agent with memory hooks and observability"""
        with tracer.start_as_current_span("agent.create_with_memory_hooks") as span:
            span.set_attribute("agent.actor_id", actor_id)
            span.set_attribute("agent.session_id", session_id)
            
            # Initialize memory hooks
            memory_hooks = ObservableCustomerSupportMemoryHooks(
                self.memory_id, self.memory_client, actor_id, session_id
            )
            
            # Create the Bedrock model
            model = BedrockModel(
                model_id=MODEL_ID,
                temperature=0.3,
                region_name=self.region,
            )
            
            # Create the agent with memory hooks
            agent = Agent(
                model=model,
                tools=[get_product_info, get_return_policy],
                system_prompt=SYSTEM_PROMPT,
                hooks=[memory_hooks],
            )
            
            span.set_attribute("agent.model_id", MODEL_ID)
            span.set_attribute("agent.tools_count", 2)
            logger.info(f"✅ Created agent with memory hooks for actor {actor_id}")
            
            return agent
    
    def set_session_context(self, session_id: str):
        """Set the session ID in OpenTelemetry baggage for trace correlation"""
        ctx = baggage.set_baggage("session.id", session_id)
        token = context.attach(ctx)
        logger.info(f"Session ID '{session_id}' attached to telemetry context")
        return token


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AgentCore Memory with Observability")
    parser.add_argument(
        "--session-id",
        type=str,
        default=str(uuid.uuid4()),
        help="Session ID to associate with this agent run",
    )
    parser.add_argument(
        "--actor-id",
        type=str,
        default="customer_001",
        help="Actor ID for the customer",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What headphones would you recommend for gaming?",
        help="Query to test the agent with",
    )
    parser.add_argument(
        "--seed-history",
        action="store_true",
        help="Seed customer history before testing",
    )
    parser.add_argument(
        "--region",
        type=str,
        help="AWS region to use",
    )
    return parser.parse_args()


def main():
    """Main function to demonstrate AgentCore Memory with Observability"""
    args = parse_arguments()
    
    # Load environment variables
    load_dotenv()
    
    # Initialize the observability system
    memory_obs = AgentCoreMemoryObservability(region_name=args.region)
    
    # Set session context for telemetry
    context_token = memory_obs.set_session_context(args.session_id)
    
    try:
        # Setup observability environment
        logger.info("🔧 Setting up observability environment...")
        env_config = memory_obs.setup_observability_environment()
        
        # Create or get memory resource
        logger.info("🧠 Setting up AgentCore Memory...")
        memory_id = memory_obs.create_or_get_memory_resource()
        
        if not memory_id:
            logger.error("❌ Failed to create memory resource")
            return
        
        # Seed customer history if requested
        if args.seed_history:
            logger.info("📚 Seeding customer history...")
            memory_obs.seed_customer_history(args.actor_id)
            
            # Wait for memory processing
            logger.info("⏳ Waiting for Long-Term Memory processing...")
            memories = memory_obs.wait_for_memory_processing(args.actor_id)
            
            if memories:
                logger.info("🎯 Customer preferences extracted:")
                for i, memory in enumerate(memories[:3], 1):
                    if isinstance(memory, dict):
                        content = memory.get('content', {})
                        if isinstance(content, dict):
                            text = content.get('text', '')
                            logger.info(f"  {i}. {text}")
        
        # Create agent with memory hooks
        logger.info("🤖 Creating agent with memory hooks...")
        agent = memory_obs.create_agent_with_memory_hooks(args.actor_id, args.session_id)
        
        # Test the agent
        logger.info(f"💬 Testing agent with query: {args.query}")
        
        with tracer.start_as_current_span("agent.invoke") as span:
            span.set_attribute("agent.query", args.query)
            span.set_attribute("agent.actor_id", args.actor_id)
            span.set_attribute("agent.session_id", args.session_id)
            
            response = agent(args.query)
            
            span.set_attribute("agent.response_length", len(str(response)))
            logger.info("✅ Agent response generated successfully")
            
            print("\n" + "="*80)
            print("🤖 AGENT RESPONSE:")
            print("="*80)
            print(response)
            print("="*80)
        
        logger.info("✅ AgentCore Memory with Observability demo completed successfully!")
        logger.info("📊 Check CloudWatch GenAI Observability dashboard for traces and metrics")
        
    except Exception as e:
        logger.error(f"❌ Error during execution: {e}")
        raise
    finally:
        # Detach context when done
        context.detach(context_token)


if __name__ == "__main__":
    main()
