# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the SRE Agent - a multi-agent system built on Amazon Bedrock AgentCore for Site Reliability Engineering tasks. The system uses LangGraph to orchestrate specialized agents (Kubernetes, Logs, Metrics, Runbooks) coordinated by a Supervisor Agent that manages memory integration and user personalization.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
uv venv --python 3.12
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
uv sync --dev  # Include development dependencies
```

### Code Quality (Use Makefile for standardized commands)
```bash
make quality        # Run all quality checks
make format         # Format code with black
make lint           # Lint with ruff  
make lint-fix       # Auto-fix linting issues
make typecheck      # Type check with mypy
make security       # Security scan with bandit
make test           # Run pytest tests
make clean          # Clean build artifacts
```

### Agent Execution
```bash
# Local CLI usage
sre-agent --prompt "Why are payment-service pods crash looping?" --provider bedrock
sre-agent --interactive  # Interactive mode

# With environment variables
USER_ID=Alice sre-agent --prompt "API response times degraded" --provider bedrock
```

### Gateway and Backend Management
```bash
# Configure gateway and restart backend services (must run every 24h due to token expiry)
./scripts/configure_gateway.sh

# Start demo backend servers
cd backend && ./scripts/start_demo_backend.sh --host $PRIVATE_IP --ssl-keyfile /opt/ssl/privkey.pem --ssl-certfile /opt/ssl/fullchain.pem

# Memory management
uv run python scripts/manage_memories.py update  # Initialize user preferences
uv run python scripts/manage_memories.py list   # Check memory status
```

### Container and Deployment
```bash
# Local container build for testing
LOCAL_BUILD=true ./deployment/build_and_deploy.sh

# Production deployment to AgentCore Runtime
./deployment/build_and_deploy.sh [ECR_REPO_NAME]

# Invoke deployed agent
uv run python deployment/invoke_agent_runtime.py
```

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

## Configuration Files

### Environment Variables
Copy `sre_agent/.env.example` to `sre_agent/.env` and configure:
- `ANTHROPIC_API_KEY`: Required for Anthropic models
- `GATEWAY_ACCESS_TOKEN`: Gateway authentication (updated by configure_gateway.sh)
- `USER_ID`: For memory personalization (Alice/Carol preconfigured)
- `LLM_PROVIDER`: bedrock or anthropic

### Agent Configuration
`sre_agent/config/agent_config.yaml`: Maps agents to tools and sets gateway URI

### Memory Configuration  
`sre_agent/memory/config.py`: Retention policies and feature flags

## Key Code Patterns

### Agent Creation
Agents inherit from `BaseAgentNode` in `sre_agent/agent_nodes.py` with tool filtering and LLM provider abstraction.

### Memory Hooks
Memory system uses hooks in `sre_agent/memory/hooks.py` to automatically capture user preferences and investigation patterns.

### Investigation Flow
1. Supervisor analyzes query and retrieves memories
2. Creates investigation plan via `InvestigationPlan` model
3. Routes to specialist agents in parallel/sequence  
4. Aggregates results with personalization
5. Generates markdown reports in `backend/data/reports/`

### Error Handling
LLM creation uses `create_llm_with_error_handling` in `sre_agent/llm_utils.py` for provider fallbacks.

## Testing

### Unit Tests
```bash
# Run all tests
uv run pytest

# Specific test files
uv run pytest tests/unit/memory/test_strategies.py
uv run pytest tests/integration/test_memory_integration.py
```

### Manual Testing
Use demo environment with synthetic data in `backend/data/` for safe testing without production impact.

## Deployment Stages

1. **Local Development**: CLI with AgentCore Gateway via MCP
2. **Container Testing**: Docker build with same gateway connection  
3. **Production**: AgentCore Runtime with full Memory integration

Gateway tokens expire every 24 hours - run `./scripts/configure_gateway.sh` to refresh.

## Workshop Development

### Workshop Structure
A comprehensive workshop is available in `workshops/sre-agent/` with progressive Jupyter notebooks:

**Quick Start Demo:**
0. **00-sre-agent-demo.ipynb**: 30-minute Strands Agent SRE demo with Amazon Bedrock (no AWS setup required)

**Full Workshop Series:**
1. **01-sre-agent-foundations.ipynb**: Environment setup, architecture overview, demo backend
2. **02-gateway-and-mcp-tools.ipynb**: AgentCore Gateway integration with MCP tools  
3. **03-multi-agent-system.ipynb**: LangGraph multi-agent orchestration
4. **04-memory-and-personalization.ipynb**: AgentCore Memory integration
5. **05-production-deployment.ipynb**: AgentCore Runtime deployment

### Workshop Commands
```bash
# Quick Strands Agent demo (30 minutes, no AWS setup)
cd workshops/sre-agent/
pip install strands strands-tools
jupyter notebook notebooks/00-sre-agent-demo.ipynb

# Full workshop (4+ hours, AWS integration)
jupyter notebook notebooks/01-sre-agent-foundations.ipynb

# Workshop utilities and validation
python helpers/workshop_utils.py     # AWS resource management
python helpers/validation_helpers.py # Progress validation
python helpers/sre_scenarios.py      # Test scenarios
```

### Workshop Helper Modules
- `workshops/sre-agent/helpers/workshop_utils.py`: AWS resource creation, Cognito setup, cleanup
- `workshops/sre-agent/helpers/sre_scenarios.py`: 8 realistic SRE incident scenarios
- `workshops/sre-agent/helpers/validation_helpers.py`: Comprehensive validation functions
- `workshops/sre-agent/configs/workshop_config.yaml`: Centralized workshop configuration

### SRE Test Scenarios
Pre-built scenarios for testing with varying complexity:
- **pod-crash-loop**: Kubernetes container failures (beginner)
- **api-response-degradation**: Multi-service performance issues (intermediate) 
- **database-connection-errors**: Connection pool exhaustion (intermediate)
- **memory-leak-investigation**: Long-term resource analysis (advanced)
- **service-mesh-failure**: Distributed system communication (advanced)

## Important Notes

- SSL/HTTPS required for all AgentCore Gateway endpoints
- Memory system takes 10-12 minutes to initialize after creation
- Demo data is synthetic - replace with real implementations for production
- User preferences are preconfigured in `scripts/user_config.yaml` (Alice: technical, Carol: executive)
- Workshop follows AWS standards with progressive learning and hands-on validation