# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Workshop Development](#workshop-development)
4. [Important Notes](#important-notes)

## Project Overview

This is the SRE Agent - a multi-agent system built on Amazon Bedrock AgentCore for Site Reliability Engineering tasks. The system uses Strands Agents to orchestrate specialized agents (Kubernetes, Logs, Metrics, Runbooks) coordinated by a Supervisor Agent that manages memory integration and user personalization.

## Architecture Overview

### Multi-Agent System (LangGraph)
- **Supervisor Agent**: Central coordinator with exclusive memory access, handles user personalization and investigation planning
- **Specialist Agents**: Domain-specific agents (Kubernetes, Logs, Metrics, Runbooks) with filtered tool access
- **Agent State**: Shared state management via `AgentState` class for investigation tracking

### Core Components
- **AgentCore Memory**: Persistent user preferences and infrastructure knowledge via `sre_agent/memory/`
- **AgentCore Gateway**: MCP protocol bridge to backend APIs via `gateway/`  
- **AgentCore Runtime**: Production deployment environment via `deployment/`

### Tool System
Tools are filtered per agent via `sre_agent/config/agent_config.yaml`:
- Kubernetes tools (5): Pod status, deployments, events, resources, nodes  
- Logs tools (5): Search, error extraction, patterns, recent logs, statistics
- Metrics tools (5): Performance, error rates, resources, availability, trends
- Runbooks tools (5): Search procedures, playbooks, guides, escalation, resolutions

### Memory Integration
- **User Preferences**: Stored via `USER_ID` environment variable, personalized in reports
- **Investigation Summaries**: Auto-generated and stored for cross-session learning  
- **Infrastructure Knowledge**: Pattern extraction from agent responses
- Memory managed through `scripts/manage_memories.py` and `sre_agent/memory/client.py`


## Workshop Development

### Progressive Complexity Workshop Series
A comprehensive workshop series in `workshops/sre-agent/` following AWS workshop best practices with progressive complexity building:

**Workshop Philosophy:**
- **Self-contained notebooks** - no external utils or config dependencies
- **Progressive complexity** - one concept layer added per notebook
- **Immediate value** - each notebook delivers working functionality
- **AWS workshop standards** - clear objectives, professional structure, minimal setup

**Workshop Modules:**

**Available Notebooks:**

0. **00-single-tool-agent.ipynb** (15 min) - Foundation
   - Single Strands Agent with Claude 3.7 Sonnet model with inference profile
   - One @tool decorator (get_pod_status)
   - FastAPI backend with realistic Kubernetes data
   - Proves core SRE infrastructure troubleshooting concept
   - 95% faster incident response vs manual investigation

0a. **00-single-tool-agent-improved.ipynb** (15 min) - Enhanced Foundation
   - Improved version following AWS documentation standards established in `prompt.md`
   - Enhanced function docstrings with comprehensive Args, Returns, Raises, and Note sections
   - Detailed inline comments explaining Strands Agent concepts and AgentCore integration
   - Proper emoji usage (✅ and ❌ only) following CLAUDE.md requirements
   - Architecture diagram formatted in proper markdown code blocks
   - Technical accuracy improvements (model consistency, port accuracy, service name precision)
   - Terminology standardization (Strands Agent vs AI Agent throughout)
   - Reference implementation for AWS documentation standards

1. **01-multiple-tools-agent.ipynb** (30 min) - Tool Expansion
   - Same Strands Agent, 3 Kubernetes tools
   - Complex tool orchestration and decision-making
   
2. **02-gateway-integration.ipynb** (45 min) - Security Layer
   - AgentCore Gateway with MCP protocol
   - OAuth authentication, production security

### Planned Progressive Series (Future Development)
3. **03-multi-domain-agent.ipynb** (60 min) - Cross-System Analysis
   - 4 backend APIs (K8s, Logs, Metrics, Runbooks)
   - Single super-agent with 8-12 tools
   
4. **04-multi-agent-system.ipynb** (75 min) - Specialist Architecture
   - 4 Strands Agents with GraphBuilder orchestration
   - Domain specialization and agent coordination
   
5. **05-memory-personalization.ipynb** (60 min) - Persistent Learning
   - AgentCore Memory integration
   - Cross-session knowledge and user preferences
   
6. **06-production-deployment.ipynb** (45 min) - Enterprise Scale
   - BedrockAgentCoreApp runtime deployment
   - Streaming, monitoring, enterprise features

### Workshop Design Principles
- **FastAPI backends** - professional async patterns from actual SRE codebase
- **Strands framework** - @tool decorators, BedrockModel
- **Real scenarios** - authentic infrastructure failures (memory leaks, pod crashes)
- **Minimal emoji usage** - only ✅ and ❌ for status indicators
- **Error handling** - comprehensive troubleshooting guidance
- **AWS integration** - Bedrock, AgentCore Gateway, Runtime deployment

### Documentation Standards (Implemented in Improved Notebooks)
Following AWS workshop best practices and established in `prompt.md`:

- **Emoji Standards**: Strict usage of only ✅ and ❌ for status indicators throughout
- **Architecture Diagrams**: Formatted in proper markdown code blocks for consistency
- **Function Documentation**: Comprehensive docstrings with Args, Returns, Raises, and Note sections
- **Inline Comments**: Educational comments explaining Strands Agent concepts and AgentCore integration
- **Technical Accuracy**: Model consistency, port accuracy, and precise service name references
- **Terminology Precision**: Consistent use of "Strands Agent" and "SRE Agent" instead of "AI Agent"
- **Educational Clarity**: Code comments that help users understand complex concepts and integration patterns
- **AWS Compliance**: Following AWS documentation standards for professional workshop experience

### Workshop Commands

```bash
# Navigate to workshop directory
cd workshops/sre-agent/

# Install required dependencies
pip install fastapi uvicorn[standard] strands-agents requests boto3 pydantic

# Available notebooks (start with foundation)
jupyter notebook notebooks/00-single-tool-agent.ipynb           # Original foundation (15 min)
jupyter notebook notebooks/00-single-tool-agent-improved.ipynb  # Enhanced foundation (15 min) - RECOMMENDED

# Progress through implemented workshops
jupyter notebook notebooks/01-multiple-tools-agent.ipynb        # Tool expansion (30 min)
jupyter notebook notebooks/02-gateway-integration.ipynb         # Security layer (45 min)

# Planned future notebooks (in development)
# jupyter notebook notebooks/03-multi-domain-agent.ipynb        # Cross-system analysis
# jupyter notebook notebooks/04-multi-agent-system.ipynb        # Specialist architecture  
# jupyter notebook notebooks/05-memory-personalization.ipynb    # Persistent learning
# jupyter notebook notebooks/06-production-deployment.ipynb     # Enterprise deployment
```

### Key Development Insights
**What Led to This Workshop Design:**

1. **Complexity Problem Solved**: Original approach jumped from 0 → 20 tools + 4 agents + LangGraph + Memory, overwhelming users
2. **Progressive Learning**: Each notebook adds ONE complexity dimension while reinforcing previous concepts  
3. **Self-Contained Design**: No workshop_utils imports - everything inline for reliability and clarity
4. **FastAPI Choice**: More professional than Flask, matches actual SRE codebase patterns, better for async operations
5. **Strands Framework**: Simpler than LangGraph for learning, @tool decorators are intuitive, direct path to AgentCore Runtime
6. **AWS Workshop Standards**: Clear objectives, estimated times, minimal setup, immediate value delivery
7. **Real Data Structures**: Uses authentic pod/container/event structures from actual backend/data/ files

**Technical Decision Points:**
- **Single tool first** → Multiple tools → Multi-domain → Multi-agent → Memory → Production
- **FastAPI over Flask** → Better async support, professional patterns, matches codebase
- **Strands over LangGraph** → Simpler learning curve, @tool decorators intuitive, production path clear  
- **Self-contained over utils** → No external dependencies, notebooks work independently
- **Emoji minimalism** → Only ✅/❌ status indicators, professional tone throughout
- **Immediate value** → Each notebook delivers working Strands Agent, builds confidence progressively

### SRE Scenarios Covered
Progressive scenario complexity across notebooks:
- **Notebook 0**: Single pod crash (OutOfMemoryError) - Foundation concept
- **Notebook 1**: Multi-pod investigation with resource analysis - Tool orchestration  
- **Notebook 2**: Same scenarios through secure gateway - Production readiness
- **Notebook 3**: Cross-system correlation (pods + logs + metrics) - Complex analysis
- **Notebook 4**: Specialist agent collaboration - Enterprise architecture
- **Notebook 5**: Learning from past incidents - Intelligent automation

## Important Notes

- SSL/HTTPS required for all AgentCore Gateway endpoints
- Memory system takes 10-12 minutes to initialize after creation
- Demo data is synthetic - replace with real implementations for production
- User preferences are preconfigured in `scripts/user_config.yaml` (Alice: technical, Carol: executive)
- Workshop follows AWS standards with progressive learning and hands-on validation

## Recent Updates and Maintenance

### Latest Changes (2024)
- **Documentation Standards Implementation**: Created `00-single-tool-agent-improved.ipynb` as reference implementation
- **AWS Compliance Updates**: Implemented comprehensive documentation standards following AWS workshop best practices
- **Terminology Standardization**: Consistent use of "Strands Agent" and "SRE Agent" throughout all materials
- **Technical Accuracy Improvements**: Enhanced model consistency, port accuracy, and service name precision
- **Workshop Status Clarification**: Clear distinction between available notebooks and planned future development
- **Enhanced Installation Instructions**: Updated dependencies and commands to reflect current requirements

### Maintenance Notes
- This document serves as the primary reference for SRE Agent project architecture and workshop development
- The `prompt.md` file contains detailed standards for notebook improvements and updates
- All notebook updates should follow the standards demonstrated in the improved notebook version
- Future notebook development should maintain consistency with established documentation and coding standards