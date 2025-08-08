# 🔧 SRE Agent Workshop - Build Multi-Agent Systems with Amazon Bedrock AgentCore

## 📚 Workshop Overview

This hands-on workshop teaches you how to build a production-ready Site Reliability Engineering (SRE) Agent using Amazon Bedrock AgentCore. You'll learn to create a sophisticated multi-agent system that can investigate infrastructure issues, analyze logs and metrics, and provide personalized responses based on user roles.

### Workshop Details

| Information         | Details                                                                                    |
|:--------------------|:-------------------------------------------------------------------------------------------|
| Workshop type       | Interactive Hands-on                                                                       |
| Agent type          | Multi-Agent System                                                                         |
| Agentic Framework   | LangGraph with Strands Agents                                                             |
| LLM models          | Amazon Nova Pro, Anthropic Claude Sonnet 3.7                                             |
| Workshop components | Gateway, Memory, Runtime, Multi-Agent Orchestration, Production Deployment               |
| Workshop vertical   | DevOps/SRE                                                                                |
| Example complexity  | Intermediate to Advanced                                                                   |
| Duration           | 4-5 hours                                                                                  |
| Prerequisites      | AWS Account, Python 3.12+, Basic familiarity with AI agents                             |

### Workshop Architecture

The workshop progressively builds a complete SRE Agent system:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Foundation    │ -> │     Gateway     │ -> │  Multi-Agent    │
│   Setup & Demo  │    │  & MCP Tools    │    │   System        │
│   Backend       │    │  Integration    │    │  Orchestration  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        |
┌─────────────────┐    ┌─────────────────┐             |
│   Production    │ <- │    Memory &     │ <-----------┘
│   Deployment    │    │ Personalization │
│   & Monitoring  │    │   Integration   │
└─────────────────┘    └─────────────────┘
```

## 🎯 Learning Objectives

By the end of this workshop, you will:

- **Understand AgentCore Architecture**: Learn how Runtime, Gateway, Memory, and Identity work together
- **Build Multi-Agent Systems**: Create specialized agents that collaborate on complex investigations
- **Implement MCP Protocol**: Transform APIs into tools using Model Context Protocol
- **Deploy Production Agents**: Deploy scalable agents to AgentCore Runtime
- **Add User Personalization**: Implement memory-based personalization for different user roles
- **Monitor and Debug**: Set up observability for production agent monitoring

## 📋 Prerequisites

### Required
- **AWS Account** with appropriate permissions (IAM, EC2, Bedrock, etc.)
- **Python 3.12+** and `uv` package manager
- **Basic AWS CLI** configuration
- **Jupyter Notebook** environment
- **SSL Certificate** for HTTPS endpoints (required for AgentCore Gateway)

### Recommended
- Basic understanding of AI agents and LLM concepts
- Familiarity with AWS services (Lambda, Cognito, ECR)
- Knowledge of SRE/DevOps practices
- Docker basics for container deployment

## 🚀 Workshop Structure

### Part 1: Foundation Setup (30-45 min)
**Notebook**: `01-sre-agent-foundations.ipynb`

- Set up development environment and dependencies
- Understand SRE Agent architecture and components
- Configure demo backend servers with synthetic data
- Run your first SRE investigation locally

**Key Outcomes**: Working local SRE agent with demo data

### Part 2: AgentCore Gateway Integration (45-60 min)
**Notebook**: `02-gateway-and-mcp-tools.ipynb`

- Create Amazon Cognito authentication
- Deploy AgentCore Gateway with MCP tools
- Transform backend APIs into agent tools
- Test individual tool integrations

**Key Outcomes**: Secure gateway with working MCP tools

### Part 3: Multi-Agent System (45-60 min)
**Notebook**: `03-multi-agent-system.ipynb`

- Build specialist agents (Kubernetes, Logs, Metrics, Runbooks)
- Implement supervisor agent with LangGraph
- Configure agent collaboration and tool routing
- Test complex multi-step investigations

**Key Outcomes**: Complete multi-agent orchestration system

### Part 4: Memory and Personalization (45-60 min)
**Notebook**: `04-memory-and-personalization.ipynb`

- Set up AgentCore Memory for persistent learning
- Configure user personas and preferences
- Implement automatic preference capture
- Test personalized investigation reports

**Key Outcomes**: Personalized agent responses based on user roles

### Part 5: Production Deployment (30-45 min)
**Notebook**: `05-production-deployment.ipynb`

- Containerize and deploy to AgentCore Runtime
- Configure production authentication and monitoring
- Set up observability and debugging
- Test production scalability

**Key Outcomes**: Production-ready SRE agent deployment

## 🛠️ Quick Start

1. **Clone and Navigate**:
```bash
git clone https://github.com/awslabs/amazon-bedrock-agentcore-samples
cd amazon-bedrock-agentcore-samples/02-use-cases/SRE-agent/workshops/sre-agent
```

2. **Set up Environment**:
```bash
uv venv --python 3.12
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

3. **Configure AWS**:
```bash
aws configure  # Set your AWS credentials and region
```

4. **Start with First Notebook**:
```bash
jupyter notebook notebooks/01-sre-agent-foundations.ipynb
```

## 📁 Workshop Structure

```
workshops/sre-agent/
├── README.md                          # This overview
├── requirements.txt                   # All Python dependencies
├── notebooks/                         # Interactive Jupyter notebooks
│   ├── 01-sre-agent-foundations.ipynb
│   ├── 02-gateway-and-mcp-tools.ipynb
│   ├── 03-multi-agent-system.ipynb
│   ├── 04-memory-and-personalization.ipynb
│   └── 05-production-deployment.ipynb
├── helpers/                           # Workshop utilities
│   ├── workshop_utils.py              # Common AWS operations
│   ├── sre_scenarios.py               # Pre-built incident scenarios
│   └── validation_helpers.py          # Progress validation functions
├── configs/                           # Configuration files
│   ├── workshop_config.yaml           # Centralized workshop settings
│   └── demo_personas.yaml             # User persona definitions
├── docs/                             # Supporting documentation
│   ├── TROUBLESHOOTING.md             # Common issues and solutions
│   └── ARCHITECTURE.md                # Deep-dive architecture guide
└── images/                           # Architecture diagrams
    └── *.png                         # Notebook illustrations
```

## 🔧 Common Scenarios

The workshop includes several realistic SRE scenarios:

- **High API Response Times**: Investigate performance degradation across microservices
- **Pod Crash Loops**: Debug Kubernetes container issues with log analysis
- **Database Connection Errors**: Trace connection pool exhaustion patterns
- **Memory Leaks**: Analyze resource usage trends and alerts
- **Service Mesh Issues**: Investigate inter-service communication failures

## 🧹 Cleanup

Each notebook includes cleanup sections. For complete cleanup:

```bash
# Run the provided cleanup script
python helpers/cleanup_workshop.py --all

# Or manual cleanup of major resources
aws bedrock-agentcore-control delete-gateway --gateway-id <your-gateway-id>
aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id <your-runtime-id>
```

## 🆘 Support

- **Troubleshooting Guide**: `docs/TROUBLESHOOTING.md`
- **Architecture Deep-dive**: `docs/ARCHITECTURE.md`
- **AWS Documentation**: [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- **Issues**: Report problems in the [GitHub repository](https://github.com/awslabs/amazon-bedrock-agentcore-samples/issues)

## 📝 Workshop Feedback

We value your feedback! Please share your experience:
- Time spent on each section
- Difficult concepts or unclear instructions  
- Suggestions for improvement
- Additional scenarios you'd like to see

---

**Ready to build intelligent SRE agents?** Start with [Notebook 1: Foundation Setup](notebooks/01-sre-agent-foundations.ipynb) 🚀