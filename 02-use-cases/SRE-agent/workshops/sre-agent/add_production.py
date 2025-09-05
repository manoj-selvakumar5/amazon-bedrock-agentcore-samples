#!/usr/bin/env python3
"""
Script to add production deployment guidance to workshop notebooks:
- Add deployment best practices
- Add monitoring recommendations
- Add security considerations
- Add scaling guidance
"""

import json
import os
from pathlib import Path

# Define the workshop directory
WORKSHOP_DIR = Path(__file__).parent
NOTEBOOKS_DIR = WORKSHOP_DIR / "notebooks"

# Production guidance cells for each notebook
PRODUCTION_GUIDANCE_CELLS = {
    "00-single-tool-agent.ipynb": {
        "production_guidance": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Production Deployment Considerations\n",
                "\n",
                "When deploying this single-tool SRE agent to production, consider the following best practices:\n",
                "\n",
                "### Security Considerations\n",
                "\n",
                "- **Authentication**: Implement OAuth or AWS IAM authentication for all API endpoints\n",
                "- **API Security**: Deploy FastAPI with proper CORS, rate limiting, and input validation\n",
                "- **Model Access Control**: Use AWS Bedrock's resource-based policies to control model access\n",
                "- **Secrets Management**: Use AWS Secrets Manager or Parameter Store for credentials\n",
                "\n",
                "### Reliability Best Practices\n",
                "\n",
                "- **API Redundancy**: Deploy multiple instances behind a load balancer\n",
                "- **Fallback Strategies**: Implement graceful degradation if models or APIs are unavailable\n",
                "- **Circuit Breaking**: Add circuit breakers for external service calls\n",
                "- **Timeouts and Retries**: Configure appropriate timeouts and retry strategies\n",
                "\n",
                "### Monitoring and Observability\n",
                "\n",
                "- **Agent Usage**: Track investigation volume, response times, and success rates\n",
                "- **Model Performance**: Monitor token usage, latency, and error rates\n",
                "- **Business Impact**: Measure incident resolution time improvements\n",
                "- **Logging**: Implement structured logging with correlation IDs\n",
                "\n",
                "### Scaling Considerations\n",
                "\n",
                "- **Horizontal Scaling**: Use containerization with Kubernetes or ECS\n",
                "- **Model Concurrency**: Configure appropriate model concurrency for your use case\n",
                "- **Rate Limiting**: Implement client-side rate limiting to manage model costs\n",
                "- **Caching**: Add response caching for frequently requested data\n",
                "\n",
                "For production deployment, consider using Amazon Bedrock AgentCore Runtime, which provides built-in scaling, security, and monitoring capabilities specifically designed for agent deployments."
            ]
        }
    },
    "01-multiple-tools-agent.ipynb": {
        "production_guidance": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Production Deployment Considerations\n",
                "\n",
                "When deploying this multi-tool SRE agent to production, consider these advanced production considerations:\n",
                "\n",
                "### Tool Orchestration Architecture\n",
                "\n",
                "- **Tool Registry**: Implement a central registry for tool discovery and versioning\n",
                "- **Tool Authorization**: Apply granular permissions to specific tools based on sensitivity\n",
                "- **Tool Metrics**: Track tool usage, latency, and success rates individually\n",
                "- **Tool Documentation**: Maintain up-to-date documentation for all tools\n",
                "\n",
                "### Performance Optimization\n",
                "\n",
                "- **Parallelization**: Execute independent tool calls concurrently using async patterns\n",
                "- **Data Caching**: Cache tool responses with appropriate TTL values\n",
                "- **Batching**: Group related requests when possible to reduce API calls\n",
                "- **Streaming**: For long-running operations, implement streaming responses\n",
                "\n",
                "### Operational Excellence\n",
                "\n",
                "- **Tool Validation**: Add regular health checks for all tools\n",
                "- **Circuit Breaking**: Implement circuit breakers for individual tools\n",
                "- **Canary Deployments**: Roll out tool changes gradually with canary testing\n",
                "- **Tool Versioning**: Support versioned tools for backward compatibility\n",
                "\n",
                "### Infrastructure as Code\n",
                "\n",
                "- **AWS CDK or CloudFormation**: Define infrastructure using IaC\n",
                "- **CI/CD Pipeline**: Automate testing and deployment of agent tools\n",
                "- **Environment Parity**: Ensure dev/test environments match production\n",
                "- **Configuration Management**: Externalize configuration for different environments\n",
                "\n",
                "For production deployment, Amazon Bedrock AgentCore Gateway provides a secure and scalable solution for tool orchestration with built-in monitoring, authentication, and access control."
            ]
        }
    },
    "02-gateway-integration.ipynb": {
        "production_guidance": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Production Deployment Considerations\n",
                "\n",
                "When deploying this Gateway-enabled SRE agent to production, consider these gateway-specific considerations:\n",
                "\n",
                "### Gateway Security Hardening\n",
                "\n",
                "- **TLS Configuration**: Use TLS 1.2+ with strong cipher suites\n",
                "- **JWT Tokens**: Implement JWT with appropriate expiration and signature validation\n",
                "- **OAuth Scopes**: Define granular OAuth scopes for different tool categories\n",
                "- **IP Restrictions**: Consider IP-based access controls for private deployments\n",
                "\n",
                "### MCP Protocol Configuration\n",
                "\n",
                "- **Schema Validation**: Enforce strict JSON Schema validation for all tool requests\n",
                "- **Response Formatting**: Standardize error responses across all tools\n",
                "- **Protocol Versioning**: Support MCP protocol versioning for compatibility\n",
                "- **Documentation**: Generate OpenAPI/Swagger docs for all MCP endpoints\n",
                "\n",
                "### Multi-Region Deployment\n",
                "\n",
                "- **Regional Redundancy**: Deploy gateways in multiple AWS regions\n",
                "- **Global Routing**: Use Route53 for intelligent traffic routing\n",
                "- **Data Sovereignty**: Consider data residency requirements for tool data\n",
                "- **Disaster Recovery**: Implement cross-region failover procedures\n",
                "\n",
                "### Gateway Monitoring\n",
                "\n",
                "- **Request Tracing**: Implement distributed tracing with AWS X-Ray\n",
                "- **Authentication Metrics**: Monitor auth success/failure rates\n",
                "- **Latency Tracking**: Track end-to-end and per-tool latency\n",
                "- **Usage Analytics**: Implement detailed usage dashboards by client\n",
                "\n",
                "### Cost Optimization\n",
                "\n",
                "- **Request Batching**: Batch compatible requests where possible\n",
                "- **Response Caching**: Cache frequent responses with appropriate invalidation\n",
                "- **Request Filtering**: Implement request deduplication when appropriate\n",
                "- **Tiered Access**: Consider tiered access plans for different usage patterns\n",
                "\n",
                "Amazon Bedrock AgentCore Gateway is specifically designed for production environments with built-in scaling, security, and monitoring features. Consider using AgentCore Runtime in conjunction with the Gateway for a complete production solution."
            ]
        }
    }
}

def find_insertion_point_for_production(notebook, notebook_filename):
    """Find appropriate insertion point for production guidance cells."""
    # For all notebooks, insert after the Summary section
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "markdown":
            source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            if "## Summary and Next Steps" in source:
                # Look for the next markdown cell or the end of the notebook
                for j in range(i+1, len(notebook["cells"])):
                    if notebook["cells"][j]["cell_type"] == "markdown":
                        return j
                # If no more markdown cells, insert at the end
                return len(notebook["cells"])
    
    # If no Summary section found, insert at the end
    return len(notebook["cells"]) - 1

def add_production_guidance(notebook_path, notebook_filename):
    """Add production guidance cells to a notebook."""
    if notebook_filename not in PRODUCTION_GUIDANCE_CELLS:
        print(f"⚠️ No production guidance defined for {notebook_filename}")
        return
    
    # Read notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find insertion point
    insert_idx = find_insertion_point_for_production(notebook, notebook_filename)
    if insert_idx == -1:
        print(f"⚠️ Could not find insertion point for {notebook_filename}")
        return
    
    # Insert production guidance cell
    notebook["cells"].insert(insert_idx, PRODUCTION_GUIDANCE_CELLS[notebook_filename]["production_guidance"])
    print(f"✅ Added production guidance to {notebook_filename}")
    
    # Write updated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)

def main():
    """Main function to add production guidance to notebooks."""
    # Get all notebook files
    notebook_files = list(NOTEBOOKS_DIR.glob("*.ipynb"))
    
    if not notebook_files:
        print(f"⚠️ No notebook files found in {NOTEBOOKS_DIR}")
        return
    
    # Add production guidance to each notebook
    for notebook_path in notebook_files:
        notebook_filename = notebook_path.name
        add_production_guidance(notebook_path, notebook_filename)
    
    print(f"✅ Added production guidance to notebooks")

if __name__ == "__main__":
    main()