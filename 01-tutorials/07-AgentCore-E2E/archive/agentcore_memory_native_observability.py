#!/usr/bin/env python3
"""
AgentCore Memory with Native Observability
==========================================

This implementation uses AgentCore Memory's BUILT-IN observability features instead of 
manually implementing OpenTelemetry tracing. AgentCore Memory provides native spans, 
logs, and metrics that appear automatically in CloudWatch GenAI Observability.

Key Difference:
- BEFORE: Manual OpenTelemetry wrapper around MemoryClient
- AFTER: Use native AgentCore Memory observability with simple configuration

Native AgentCore Memory provides:
- Memory operation spans (CreateEvent, RetrieveMemoryRecords, etc.)
- Extraction/consolidation logs  
- CloudWatch metrics (AWS/Bedrock/AgentCore/Memory namespace)
- Automatic correlation with runtime traces when used together
"""

import argparse
import logging
import time
import uuid
from typing import Dict, List, Optional

import boto3
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from boto3.session import Session
from botocore.exceptions import ClientError
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


class AgentCoreMemoryWithNativeObservability:
    """
    AgentCore Memory using NATIVE observability features
    
    Instead of wrapping MemoryClient with custom tracing, this leverages
    the built-in AgentCore Memory observability capabilities.
    """
    
    def __init__(self, region_name: str = None, enable_observability: bool = True):
        self.boto_session = Session()
        self.region = region_name or self.boto_session.region_name
        
        # Use standard MemoryClient - native observability is built-in
        self.memory_client = MemoryClient(region_name=self.region)
        self.memory_name = "CustomerSupportMemoryWithObservability"
        self.memory_id = None
        
        # Setup AWS clients for log group creation (optional)
        self.logs_client = boto3.client("logs", region_name=self.region)
        self.sts_client = boto3.client("sts", region_name=self.region)
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        
        self.enable_observability = enable_observability
        logger.info(f"Initialized AgentCore Memory with native observability in region {self.region}")
    
    def setup_memory_observability_logs(self):
        """
        Setup CloudWatch log groups for AgentCore Memory native logging
        
        AgentCore Memory automatically logs to these groups when enabled:
        - /aws/vendedlogs/bedrock-agentcore/memory/extraction
        - /aws/vendedlogs/bedrock-agentcore/memory/consolidation
        """
        if not self.enable_observability:
            logger.info("Observability disabled, skipping log group setup")
            return
        
        log_groups = [
            "/aws/vendedlogs/bedrock-agentcore/memory/extraction",
            "/aws/vendedlogs/bedrock-agentcore/memory/consolidation",
            "/aws/bedrock-agentcore/memory/operations"  # Custom for our operations
        ]
        
        for log_group_name in log_groups:
            try:
                self.logs_client.create_log_group(logGroupName=log_group_name)
                logger.info(f"✅ Created log group: {log_group_name}")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                    logger.info(f"ℹ️ Log group already exists: {log_group_name}")
                else:
                    logger.warning(f"⚠️ Could not create log group {log_group_name}: {e}")
    
    def create_memory_with_observability(self):
        """
        Create AgentCore Memory resource with native observability enabled
        
        The native observability features include:
        - Automatic spans for all memory operations
        - Extraction and consolidation logs
        - CloudWatch metrics in AWS/Bedrock/AgentCore/Memory namespace
        """
        try:
            memory_id = get_ssm_parameter("/app/customersupport/agentcore/memory_id")
            self.memory_client.gmcp_client.get_memory(memoryId=memory_id)
            self.memory_id = memory_id
            logger.info(f"Retrieved existing memory with native observability: {memory_id}")
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
                
                logger.info("Creating AgentCore Memory with NATIVE observability features...")
                logger.info("• Native spans will be automatically generated for all operations")
                logger.info("• Extraction/consolidation logs will be available in CloudWatch")
                logger.info("• Memory metrics will appear in AWS/Bedrock/AgentCore/Memory namespace")
                
                # Create memory resource - observability is automatically enabled
                response = self.memory_client.create_memory_and_wait(
                    name=self.memory_name,
                    description="Customer support memory with native AgentCore observability",
                    strategies=strategies,
                    event_expiry_days=90,
                )
                
                memory_id = response["id"]
                self.memory_id = memory_id
                
                try:
                    put_ssm_parameter("/app/customersupport/agentcore/memory_id", memory_id)
                except Exception as e:
                    logger.warning(f"Failed to store memory ID in SSM: {e}")
                
                logger.info(f"✅ Memory created with native observability: {memory_id}")
                logger.info("📊 Native observability features now active:")
                logger.info("   • Memory operation spans in CloudWatch GenAI Observability")
                logger.info("   • Extraction logs in /aws/vendedlogs/bedrock-agentcore/memory/")
                logger.info("   • Metrics in CloudWatch namespace: AWS/Bedrock/AgentCore/Memory")
                
                return memory_id
                
            except Exception as e:
                logger.error(f"Failed to create memory resource: {e}")
                return None
    
    def seed_customer_history(self, actor_id: str):
        """
        Seed memory with sample customer interactions
        
        Note: All memory operations (create_event, retrieve_memories) will 
        automatically generate native AgentCore spans and logs.
        """
        previous_interactions = [
            ("I'm having issues with my MacBook Pro overheating during video editing.", "USER"),
            ("I can help with that thermal issue. Your MacBook Pro order #MB-78432 is still under warranty.", "ASSISTANT"),
            ("What's the return policy on gaming headphones? I need low latency for competitive FPS games", "USER"),
            ("For gaming headphones, you have 30 days to return. For competitive FPS, check audio latency specs.", "ASSISTANT"),
            ("I need a laptop under $1200 for programming. Prefer 16GB RAM and Linux compatibility. I like ThinkPad models.", "USER"),
            ("Perfect! For development work, I'd suggest ThinkPad E series with excellent Linux support.", "ASSISTANT"),
        ]
        
        if self.memory_id:
            try:
                # This create_event call will automatically generate:
                # - CreateEvent span with memory.id, session.id, actor.id attributes
                # - Logs in the extraction log group
                # - CloudWatch metrics for memory operations
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=actor_id,
                    session_id="seed_session",
                    messages=previous_interactions
                )
                logger.info("✅ Seeded customer history with native observability")
                logger.info("📊 Check CloudWatch for:")
                logger.info("   • CreateEvent spans in GenAI Observability")
                logger.info("   • Memory extraction logs")
                logger.info("   • Memory operation metrics")
                return True
            except Exception as e:
                logger.error(f"⚠️ Error seeding history: {e}")
                return False
        return False
    
    def wait_for_memory_processing(self, actor_id: str, max_retries: int = 6):
        """
        Wait for Long-Term Memory processing to complete
        
        Native observability will show:
        - Memory consolidation logs as processing happens
        - Extraction completion events
        - Processing duration metrics
        """
        logger.info("🔍 Waiting for native memory processing...")
        logger.info("📊 Monitor extraction progress in CloudWatch logs:")
        logger.info("   • /aws/vendedlogs/bedrock-agentcore/memory/extraction")
        logger.info("   • /aws/vendedlogs/bedrock-agentcore/memory/consolidation")
        
        retries = 0
        while retries < max_retries:
            # This retrieve_memories call will automatically generate:
            # - RetrieveMemoryRecords span with namespace and query attributes
            # - Metrics for retrieval latency and success rate
            memories = self.memory_client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=f"support/customer/{actor_id}/preferences",
                query="customer preferences and requirements"
            )
            
            if memories:
                logger.info(f"✅ Found {len(memories)} memories after {retries * 10} seconds!")
                logger.info("📊 Native observability captured:")
                logger.info("   • RetrieveMemoryRecords spans")
                logger.info("   • Memory retrieval metrics")
                logger.info("   • Processing completion logs")
                return memories
            
            retries += 1
            if retries < max_retries:
                logger.info(f"⏳ Still processing... (attempt {retries}/{max_retries})")
                time.sleep(10)
            else:
                logger.warning("⚠️ Memory processing taking longer than expected")
                break
        
        return []


class NativeMemoryHooks(HookProvider):
    """
    Simple memory hooks that rely on AgentCore Memory's native observability
    
    No custom tracing needed - all operations automatically generate spans and metrics
    """
    
    def __init__(self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespaces = {
            i["type"]: i["namespaces"][0]
            for i in self.client.get_memory_strategies(self.memory_id)
        }
        logger.info(f"Memory hooks initialized with native observability for {actor_id}")
    
    def retrieve_customer_context(self, event: MessageAddedEvent):
        """
        Retrieve customer context - native observability tracks all operations
        """
        messages = event.agent.messages
        if (
            messages[-1]["role"] == "user"
            and "toolResult" not in messages[-1]["content"][0]
        ):
            user_query = messages[-1]["content"][0]["text"]
            
            try:
                all_context = []
                
                for context_type, namespace in self.namespaces.items():
                    # Native observability automatically creates:
                    # - RetrieveMemoryRecords span
                    # - Retrieval latency metrics
                    # - Memory access logs
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
                    context_text = "\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    messages[-1]["content"][0]["text"] = f"Customer Context:\n{context_text}\n\n{original_text}"
                    logger.info(f"Retrieved {len(all_context)} context items (native observability active)")
                
            except Exception as e:
                logger.error(f"Failed to retrieve customer context: {e}")
    
    def save_support_interaction(self, event: AfterInvocationEvent):
        """
        Save customer support interaction - native observability tracks storage
        """
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
                    # Native observability automatically creates:
                    # - CreateEvent span with full context
                    # - Memory storage metrics
                    # - Event creation logs
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[
                            (customer_query, "USER"),
                            (agent_response, "ASSISTANT"),
                        ],
                    )
                    logger.info("Saved interaction with native observability")
        
        except Exception as e:
            logger.error(f"Failed to save support interaction: {e}")
    
    def register_hooks(self, registry: HookRegistry) -> None:
        """Register memory hooks with native observability"""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
        logger.info("Memory hooks registered with native AgentCore observability")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AgentCore Memory with Native Observability")
    parser.add_argument(
        "--session-id",
        type=str,
        default=str(uuid.uuid4()),
        help="Session ID for correlation",
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
        "--disable-observability",
        action="store_true",
        help="Disable observability features",
    )
    return parser.parse_args()


def main():
    """Main function demonstrating AgentCore Memory with native observability"""
    args = parse_arguments()
    
    # Initialize with native observability
    enable_obs = not args.disable_observability
    memory_system = AgentCoreMemoryWithNativeObservability(enable_observability=enable_obs)
    
    try:
        logger.info("🔧 Setting up AgentCore Memory with NATIVE observability...")
        
        # Setup native observability log groups (optional)
        memory_system.setup_memory_observability_logs()
        
        # Create memory resource with native observability
        memory_id = memory_system.create_memory_with_observability()
        
        if not memory_id:
            logger.error("❌ Failed to create memory resource")
            return
        
        # Seed customer history if requested
        if args.seed_history:
            logger.info("📚 Seeding customer history with native observability...")
            memory_system.seed_customer_history(args.actor_id)
            
            # Wait for processing (native logs will show progress)
            memories = memory_system.wait_for_memory_processing(args.actor_id)
            
            if memories:
                logger.info("🎯 Customer preferences extracted (visible in native observability):")
                for i, memory in enumerate(memories[:3], 1):
                    if isinstance(memory, dict):
                        content = memory.get('content', {})
                        if isinstance(content, dict):
                            text = content.get('text', '')
                            logger.info(f"  {i}. {text}")
        
        # Create agent with native memory hooks
        logger.info("🤖 Creating agent with native memory observability...")
        
        memory_hooks = NativeMemoryHooks(
            memory_id, memory_system.memory_client, args.actor_id, args.session_id
        )
        
        model = BedrockModel(
            model_id=MODEL_ID,
            temperature=0.3,
            region_name=memory_system.region,
        )
        
        agent = Agent(
            model=model,
            tools=[get_product_info, get_return_policy],
            system_prompt=SYSTEM_PROMPT,
            hooks=[memory_hooks],
        )
        
        # Test the agent (native observability will track everything)
        logger.info(f"💬 Testing agent with query: {args.query}")
        logger.info("📊 Native observability will automatically capture:")
        logger.info("   • Memory retrieval operations")
        logger.info("   • Agent processing spans")
        logger.info("   • Memory storage operations")
        
        response = agent(args.query)
        
        print("\n" + "="*80)
        print("🤖 AGENT RESPONSE:")
        print("="*80)
        print(response)
        print("="*80)
        
        logger.info("✅ Native AgentCore Memory observability demo completed!")
        logger.info("")
        logger.info("📊 View native observability data in:")
        logger.info("   • CloudWatch GenAI Observability → Bedrock AgentCore")
        logger.info("   • CloudWatch Metrics → AWS/Bedrock/AgentCore/Memory")
        logger.info("   • CloudWatch Logs → /aws/vendedlogs/bedrock-agentcore/memory/")
        logger.info("")
        logger.info("🎯 Key spans to look for:")
        logger.info("   • CreateEvent (memory storage)")
        logger.info("   • RetrieveMemoryRecords (context retrieval)")
        logger.info("   • Memory extraction/consolidation logs")
        
    except Exception as e:
        logger.error(f"❌ Error during execution: {e}")
        raise


if __name__ == "__main__":
    main()
