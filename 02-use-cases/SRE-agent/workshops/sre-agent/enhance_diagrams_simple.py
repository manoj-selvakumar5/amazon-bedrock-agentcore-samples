#!/usr/bin/env python3
"""
Script to enhance architecture diagrams in workshop notebooks:
- Add placeholder cells for architecture diagrams
- Allow for external diagram files to be loaded later
- Improve diagram explanations
"""

import json
import os
from pathlib import Path

# Define the workshop directory
WORKSHOP_DIR = Path(__file__).parent
NOTEBOOKS_DIR = WORKSHOP_DIR / "notebooks"

# Diagram cell content for each notebook
DIAGRAM_CELLS = {
    "00-single-tool-agent.ipynb": {
        "markdown_header": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Enhanced Architecture Diagram\n",
                "\n",
                "The diagram below shows the flow from the Agent through the tool to the backend API:"
            ]
        },
        "diagram_placeholder": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "**Architecture Diagram Placeholder**\n",
                "\n",
                "*This is a placeholder for the Single Tool Architecture diagram that will be added separately.*\n",
                "\n",
                "Key components in the architecture:\n",
                "- **Strands Agent**: Claude 3 Haiku model with tool management and response processing\n",
                "- **@tool Function**: get_pod_status function with parameter handling and response formatting\n",
                "- **FastAPI Backend**: /pods endpoint with JSON pod data and status information\n",
                "\n",
                "Data flow: Agent → Tool → Backend → Tool → Agent"
            ]
        }
    },
    "01-multiple-tools-agent.ipynb": {
        "markdown_header": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Enhanced Architecture Diagram\n",
                "\n",
                "The diagram below shows how the Agent orchestrates multiple tools to gather comprehensive information:"
            ]
        },
        "diagram_placeholder": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "**Architecture Diagram Placeholder**\n",
                "\n",
                "*This is a placeholder for the Multiple Tools Architecture diagram that will be added separately.*\n",
                "\n",
                "Key components in the architecture:\n",
                "- **Strands Agent**: Claude 3 Haiku model with tool orchestration and response integration\n",
                "- **@tool Functions**: 3 specialized tools (get_pod_status, get_pod_events, get_pod_resources)\n",
                "- **FastAPI Backend**: Multiple endpoints (/pods, /pods/{name}/events, /pods/{name}/resources)\n",
                "\n",
                "Data flow: The Agent intelligently selects and orchestrates appropriate tools based on the investigation needs"
            ]
        }
    },
    "02-gateway-integration.ipynb": {
        "markdown_header": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### Enhanced Gateway Architecture Diagram\n",
                "\n",
                "The diagram below shows how the AgentCore Gateway adds security and standardization layers between the Agent and backend services:"
            ]
        },
        "diagram_placeholder": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "**Architecture Diagram Placeholder**\n",
                "\n",
                "*This is a placeholder for the AgentCore Gateway Architecture diagram that will be added separately.*\n",
                "\n",
                "Key components in the architecture:\n",
                "- **Strands Agent**: Claude 3 Haiku model with Gateway Client and tool orchestration\n",
                "- **AgentCore Gateway**: Multiple layers including Authentication (OAuth 2.0), MCP Protocol, and Monitoring\n",
                "- **Secure Backend APIs**: Auth-protected endpoints for pods, events, and resources\n",
                "\n",
                "Data flow:\n",
                "1. Agent → Gateway: Auth Request\n",
                "2. Gateway → Agent: Token Response\n",
                "3. Agent → Gateway: Tool Request + Token\n",
                "4. Gateway → Backend: Authenticated API Calls\n",
                "5. Gateway: Monitoring and logging of all operations"
            ]
        }
    }
}

def find_architecture_section(notebook):
    """Find the architecture section in a notebook."""
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "markdown":
            source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            if "Architecture" in source and "```" in source:
                return i
    return -1

def enhance_diagrams(notebook_path, notebook_filename):
    """Enhance architecture diagrams in a notebook."""
    if notebook_filename not in DIAGRAM_CELLS:
        print(f"⚠️ No diagram cells defined for {notebook_filename}")
        return
    
    # Read notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find architecture section
    arch_idx = find_architecture_section(notebook)
    if arch_idx == -1:
        print(f"⚠️ Architecture section not found in {notebook_filename}")
        return
    
    # Insert enhanced diagram cells after architecture section
    notebook["cells"].insert(arch_idx + 1, DIAGRAM_CELLS[notebook_filename]["markdown_header"])
    notebook["cells"].insert(arch_idx + 2, DIAGRAM_CELLS[notebook_filename]["diagram_placeholder"])
    print(f"✅ Enhanced architecture diagram in {notebook_filename}")
    
    # Write updated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)

def main():
    """Main function to enhance architecture diagrams in all notebooks."""
    # Get all notebook files
    notebook_files = list(NOTEBOOKS_DIR.glob("*.ipynb"))
    
    if not notebook_files:
        print(f"⚠️ No notebook files found in {NOTEBOOKS_DIR}")
        return
    
    # Enhance diagrams in each notebook
    for notebook_path in notebook_files:
        notebook_filename = notebook_path.name
        enhance_diagrams(notebook_path, notebook_filename)
    
    print(f"✅ Enhanced architecture diagrams in notebooks")

if __name__ == "__main__":
    main()