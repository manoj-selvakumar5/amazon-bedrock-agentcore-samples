#!/usr/bin/env python3
"""
Truly Minimal AgentCore Memory Observability
===========================================

This is what minimal OpenTelemetry instrumentation actually looks like:
- Use existing lab-02 memory code as-is
- Just run with: opentelemetry-instrument python truly_minimal_memory_observability.py
- AgentCore Memory native spans appear automatically in CloudWatch Transaction Search

No custom classes, no wrappers, no complex setup - just the original memory code + OTEL instrument.
"""

import uuid
from strands import Agent
from strands.models import BedrockModel

# Import existing lab helpers (no changes needed)
from lab_helpers.lab1_strands_agent import (
    MODEL_ID, SYSTEM_PROMPT, get_product_info, get_return_policy
)
from lab_helpers.lab2_memory import (
    CustomerSupportMemoryHooks, memory_client, ACTOR_ID, create_or_get_memory_resource
)
from scripts.utils import get_ssm_parameter

def main():
    """Minimal memory observability demo"""
    
    # Use existing memory setup (no changes)
    memory_id = create_or_get_memory_resource()
    session_id = str(uuid.uuid4())
    
    # Use existing memory hooks (no changes)
    memory_hooks = CustomerSupportMemoryHooks(
        memory_id, memory_client, ACTOR_ID, session_id
    )
    
    # Use existing agent setup (no changes)
    model = BedrockModel(model_id=MODEL_ID, temperature=0.3)
    agent = Agent(
        model=model,
        tools=[get_product_info, get_return_policy],
        system_prompt=SYSTEM_PROMPT,
        hooks=[memory_hooks],
    )
    
    # Test the agent (same as lab-02)
    print("🤖 Testing agent with memory...")
    response = agent("What headphones would you recommend for gaming?")
    print(f"Response: {response}")
    
    print("✅ Done! Check CloudWatch Transaction Search for CreateEvent and RetrieveMemoryRecords spans")

if __name__ == "__main__":
    main()


