#!/usr/bin/env python3
"""
Script to improve technical accuracy in workshop notebooks:
- Add detailed explanations of Strands framework
- Add technical details on AgentCore Gateway
- Enhance explanations of AWS services and concepts
"""

import json
import os
from pathlib import Path

# Define the workshop directory
WORKSHOP_DIR = Path(__file__).parent
NOTEBOOKS_DIR = WORKSHOP_DIR / "notebooks"

# Technical improvement cells for each notebook
TECH_IMPROVEMENT_CELLS = {
    "00-single-tool-agent.ipynb": {
        "strands_explanation": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Understanding Strands Framework with Amazon Bedrock\n",
                "\n",
                "The Strands framework provides a powerful way to create agents with Amazon Bedrock models. Let's explore the key components:\n",
                "\n",
                "### BedrockModel Integration\n",
                "\n",
                "The `BedrockModel` class provides direct integration with Amazon Bedrock:\n",
                "\n",
                "- **Authentication**: Uses AWS credentials and handles AWS Signature V4 signing\n",
                "- **Model Management**: Supports all Claude models with appropriate prompting\n",
                "- **Request Formatting**: Handles model-specific prompt structures\n",
                "- **Token Management**: Efficiently manages token usage and context windows\n",
                "\n",
                "### @tool Decorator\n",
                "\n",
                "The `@tool` decorator transforms Python functions into agent tools:\n",
                "\n",
                "- **Automatic Documentation**: Converts docstrings and type hints into tool descriptions\n",
                "- **Parameter Validation**: Validates input parameters against type specifications\n",
                "- **Error Handling**: Provides consistent error handling across tools\n",
                "- **Function Integration**: Seamlessly integrates Python functions with LLM reasoning\n",
                "\n",
                "### Agent Architecture\n",
                "\n",
                "The Strands `Agent` class orchestrates the interaction between model and tools:\n",
                "\n",
                "- **Tool Selection**: Analyzes queries to select appropriate tools\n",
                "- **Context Management**: Maintains conversation context efficiently\n",
                "- **System Prompt**: Uses the system prompt to define agent behavior\n",
                "- **Response Formatting**: Structures responses for consistency\n",
                "\n",
                "This architecture provides a production-ready foundation for building robust agents with Amazon Bedrock."
            ]
        }
    },
    "02-gateway-integration.ipynb": {
        "gateway_explanation": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Amazon Bedrock AgentCore Gateway Deep Dive\n",
                "\n",
                "AgentCore Gateway is a crucial component for production-grade agent deployments. Let's explore its architecture and capabilities in detail:\n",
                "\n",
                "### Security Architecture\n",
                "\n",
                "AgentCore Gateway implements multiple security layers:\n",
                "\n",
                "- **Authentication**: OAuth 2.0 token-based authentication with configurable token lifetimes\n",
                "- **Authorization**: Fine-grained access control for tools and operations\n",
                "- **Transport Security**: TLS/SSL encryption for all communications\n",
                "- **Input Validation**: Request validation against MCP schemas\n",
                "- **AWS Integration**: Seamless integration with AWS IAM, Secrets Manager, and KMS\n",
                "\n",
                "### Model Context Protocol (MCP)\n",
                "\n",
                "MCP standardizes communication between agents and tools:\n",
                "\n",
                "- **Tool Definition**: JSON schema-based tool definitions\n",
                "- **Parameter Typing**: Strong typing for tool parameters\n",
                "- **Request Transformation**: Converts agent requests to API calls\n",
                "- **Response Handling**: Formats responses for agent consumption\n",
                "- **Error Management**: Standardized error handling and reporting\n",
                "\n",
                "### Production Capabilities\n",
                "\n",
                "Key features for production deployments:\n",
                "\n",
                "- **Monitoring**: Request/response logging and metrics\n",
                "- **Rate Limiting**: Configurable throttling policies\n",
                "- **Versioning**: Tool version management\n",
                "- **High Availability**: Support for redundant deployments\n",
                "- **Resource Isolation**: Separate resource allocation for tools\n",
                "\n",
                "### Integration Patterns\n",
                "\n",
                "AgentCore Gateway supports various integration patterns:\n",
                "\n",
                "- **Direct Integration**: Connect directly to backend services\n",
                "- **Proxy Mode**: Act as a proxy for existing APIs\n",
                "- **Multi-Backend**: Connect to multiple backend services\n",
                "- **Chain Pattern**: Chain multiple tools for complex operations\n",
                "\n",
                "This architecture enables secure, scalable, and maintainable agent deployments in production environments."
            ]
        }
    }
}

def find_insertion_point(notebook, notebook_filename):
    """Find appropriate insertion points for technical improvements."""
    if notebook_filename == "00-single-tool-agent.ipynb":
        # For notebook 0, insert after agent initialization
        for i, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code" and "agent = Agent(" in str(cell["source"]):
                return i + 1
    
    elif notebook_filename == "02-gateway-integration.ipynb":
        # For notebook 2, insert after gateway architecture overview
        for i, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "markdown" and "Gateway Architecture Overview" in str(cell["source"]):
                for j in range(i+1, len(notebook["cells"])):
                    if notebook["cells"][j]["cell_type"] == "markdown":
                        return j
    
    return -1

def add_technical_improvements(notebook_path, notebook_filename):
    """Add technical accuracy improvements to a notebook."""
    if notebook_filename not in TECH_IMPROVEMENT_CELLS:
        print(f"⚠️ No technical improvement cells defined for {notebook_filename}")
        return
    
    # Read notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find insertion point
    insert_idx = find_insertion_point(notebook, notebook_filename)
    if insert_idx == -1:
        print(f"⚠️ Could not find insertion point for {notebook_filename}")
        return
    
    # Insert technical improvement cells
    if notebook_filename == "00-single-tool-agent.ipynb":
        notebook["cells"].insert(insert_idx, TECH_IMPROVEMENT_CELLS[notebook_filename]["strands_explanation"])
        print(f"✅ Added Strands framework explanation to {notebook_filename}")
    
    elif notebook_filename == "02-gateway-integration.ipynb":
        notebook["cells"].insert(insert_idx, TECH_IMPROVEMENT_CELLS[notebook_filename]["gateway_explanation"])
        print(f"✅ Added AgentCore Gateway deep dive to {notebook_filename}")
    
    # Write updated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)

def main():
    """Main function to add technical accuracy improvements."""
    # Get all notebook files
    notebook_files = list(NOTEBOOKS_DIR.glob("*.ipynb"))
    
    if not notebook_files:
        print(f"⚠️ No notebook files found in {NOTEBOOKS_DIR}")
        return
    
    # Add technical improvements to each notebook
    for notebook_path in notebook_files:
        notebook_filename = notebook_path.name
        add_technical_improvements(notebook_path, notebook_filename)
    
    print(f"✅ Added technical accuracy improvements to notebooks")

if __name__ == "__main__":
    main()