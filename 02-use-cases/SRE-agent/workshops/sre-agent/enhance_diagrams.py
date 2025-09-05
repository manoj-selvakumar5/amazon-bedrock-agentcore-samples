#!/usr/bin/env python3
"""
Script to enhance architecture diagrams in workshop notebooks:
- Replace ASCII art diagrams with Python-generated diagrams
- Create more detailed visual representations
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
        "diagram_code": {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "# Install pydot if not available\n",
                "try:\n",
                "    import pydot\n",
                "    from IPython.display import Image, display\n",
                "except ImportError:\n",
                "    !pip install pydot graphviz --quiet\n",
                "    import pydot\n",
                "    from IPython.display import Image, display\n",
                "\n",
                "# Create a new graph for the Single Tool architecture\n",
                "graph = pydot.Dot(graph_type='digraph', rankdir='LR', \n",
                "                  label='Single Tool Architecture', labelloc='t')\n",
                "\n",
                "# Create nodes with detailed labels\n",
                "agent_node = pydot.Node(\"Strands Agent\", shape=\"box\", \n",
                "                        label=\"Strands Agent\\n- Claude 3 Haiku\\n- Tool Management\\n- Response Processing\", \n",
                "                        style=\"filled\", fillcolor=\"#E9F7EF\")\n",
                "\n",
                "tool_node = pydot.Node(\"Tool\", shape=\"box\", \n",
                "                       label=\"@tool Function\\n- get_pod_status\\n- Parameter Handling\\n- Response Formatting\", \n",
                "                       style=\"filled\", fillcolor=\"#D4EFDF\")\n",
                "\n",
                "backend_node = pydot.Node(\"Backend\", shape=\"box\", \n",
                "                          label=\"FastAPI Backend\\n- /pods Endpoint\\n- JSON Pod Data\\n- Status Information\", \n",
                "                          style=\"filled\", fillcolor=\"#D5F5E3\")\n",
                "\n",
                "# Create edges with descriptions\n",
                "edge1 = pydot.Edge(agent_node, tool_node, label=\"Tool invocation\")\n",
                "edge2 = pydot.Edge(tool_node, backend_node, label=\"HTTP request\")\n",
                "edge3 = pydot.Edge(backend_node, tool_node, label=\"JSON response\", dir=\"back\")\n",
                "edge4 = pydot.Edge(tool_node, agent_node, label=\"Formatted results\", dir=\"back\")\n",
                "\n",
                "# Add nodes and edges to the graph\n",
                "graph.add_node(agent_node)\n",
                "graph.add_node(tool_node)\n",
                "graph.add_node(backend_node)\n",
                "graph.add_edge(edge1)\n",
                "graph.add_edge(edge2)\n",
                "graph.add_edge(edge3)\n",
                "graph.add_edge(edge4)\n",
                "\n",
                "# Save and display the graph\n",
                "graph_file = \"single_tool_architecture.png\"\n",
                "graph.write_png(graph_file)\n",
                "display(Image(filename=graph_file))\n",
                "\n",
                "print(\"The diagram shows the single tool architecture with one-way data flow.\")"
            ],
            "execution_count": None,
            "outputs": []
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
        "diagram_code": {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "# Install pydot if not available\n",
                "try:\n",
                "    import pydot\n",
                "    from IPython.display import Image, display\n",
                "except ImportError:\n",
                "    !pip install pydot graphviz --quiet\n",
                "    import pydot\n",
                "    from IPython.display import Image, display\n",
                "\n",
                "# Create a new graph for the Multiple Tools architecture\n",
                "graph = pydot.Dot(graph_type='digraph', rankdir='LR', \n",
                "                  label='Multiple Tools Architecture', labelloc='t')\n",
                "\n",
                "# Create nodes with detailed labels\n",
                "agent_node = pydot.Node(\"Strands Agent\", shape=\"box\", \n",
                "                        label=\"Strands Agent\\n- Claude 3 Haiku\\n- Tool Orchestration\\n- Response Integration\", \n",
                "                        style=\"filled\", fillcolor=\"#E9F7EF\")\n",
                "\n",
                "# Create a cluster subgraph for tools\n",
                "tools_cluster = pydot.Cluster(\"tools_cluster\", label=\"@tool Functions\", style=\"filled\", fillcolor=\"#D4EFDF\")\n",
                "\n",
                "tool1_node = pydot.Node(\"Tool1\", label=\"get_pod_status\", shape=\"box\")\n",
                "tool2_node = pydot.Node(\"Tool2\", label=\"get_pod_events\", shape=\"box\")\n",
                "tool3_node = pydot.Node(\"Tool3\", label=\"get_pod_resources\", shape=\"box\")\n",
                "\n",
                "tools_cluster.add_node(tool1_node)\n",
                "tools_cluster.add_node(tool2_node)\n",
                "tools_cluster.add_node(tool3_node)\n",
                "\n",
                "# Create a cluster subgraph for backend endpoints\n",
                "backend_cluster = pydot.Cluster(\"backend_cluster\", label=\"FastAPI Backend\", style=\"filled\", fillcolor=\"#D5F5E3\")\n",
                "\n",
                "endpoint1_node = pydot.Node(\"Endpoint1\", label=\"/pods\", shape=\"box\")\n",
                "endpoint2_node = pydot.Node(\"Endpoint2\", label=\"/pods/{name}/events\", shape=\"box\")\n",
                "endpoint3_node = pydot.Node(\"Endpoint3\", label=\"/pods/{name}/resources\", shape=\"box\")\n",
                "\n",
                "backend_cluster.add_node(endpoint1_node)\n",
                "backend_cluster.add_node(endpoint2_node)\n",
                "backend_cluster.add_node(endpoint3_node)\n",
                "\n",
                "# Add clusters to main graph\n",
                "graph.add_subgraph(tools_cluster)\n",
                "graph.add_subgraph(backend_cluster)\n",
                "graph.add_node(agent_node)\n",
                "\n",
                "# Create edges with descriptions\n",
                "edge1 = pydot.Edge(agent_node, tool1_node, label=\"Tool 1\")\n",
                "edge2 = pydot.Edge(agent_node, tool2_node, label=\"Tool 2\")\n",
                "edge3 = pydot.Edge(agent_node, tool3_node, label=\"Tool 3\")\n",
                "\n",
                "edge4 = pydot.Edge(tool1_node, endpoint1_node)\n",
                "edge5 = pydot.Edge(tool2_node, endpoint2_node)\n",
                "edge6 = pydot.Edge(tool3_node, endpoint3_node)\n",
                "\n",
                "# Add edges to the graph\n",
                "graph.add_edge(edge1)\n",
                "graph.add_edge(edge2)\n",
                "graph.add_edge(edge3)\n",
                "graph.add_edge(edge4)\n",
                "graph.add_edge(edge5)\n",
                "graph.add_edge(edge6)\n",
                "\n",
                "# Save and display the graph\n",
                "graph_file = \"multi_tool_architecture.png\"\n",
                "graph.write_png(graph_file)\n",
                "display(Image(filename=graph_file))\n",
                "\n",
                "print(\"The diagram shows how the Agent orchestrates multiple specialized tools to gather comprehensive information.\")"
            ],
            "execution_count": None,
            "outputs": []
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
        "diagram_code": {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "# Install pydot if not available\n",
                "try:\n",
                "    import pydot\n",
                "    from IPython.display import Image, display\n",
                "except ImportError:\n",
                "    !pip install pydot graphviz --quiet\n",
                "    import pydot\n",
                "    from IPython.display import Image, display\n",
                "\n",
                "# Create a new graph for the Gateway architecture\n",
                "graph = pydot.Dot(graph_type='digraph', rankdir='LR', \n",
                "                  label='AgentCore Gateway Architecture', labelloc='t')\n",
                "\n",
                "# Create nodes with detailed labels\n",
                "agent_node = pydot.Node(\"Strands Agent\", shape=\"box\", \n",
                "                        label=\"Strands Agent\\n- Claude 3 Haiku\\n- Gateway Client\\n- Tool Orchestration\", \n",
                "                        style=\"filled\", fillcolor=\"#E9F7EF\")\n",
                "\n",
                "# Create a cluster subgraph for gateway components\n",
                "gateway_cluster = pydot.Cluster(\"gateway_cluster\", label=\"AgentCore Gateway\", style=\"filled\", fillcolor=\"#EBF5FB\")\n",
                "\n",
                "auth_node = pydot.Node(\"Auth\", label=\"Authentication\\n- OAuth 2.0\\n- Token Management\", shape=\"box\")\n",
                "mcp_node = pydot.Node(\"MCP\", label=\"MCP Protocol\\n- Tool Definition\\n- Request Transform\", shape=\"box\")\n",
                "monitor_node = pydot.Node(\"Monitor\", label=\"Monitoring\\n- Request Logs\\n- Performance\\n- Analytics\", shape=\"box\")\n",
                "\n",
                "gateway_cluster.add_node(auth_node)\n",
                "gateway_cluster.add_node(mcp_node)\n",
                "gateway_cluster.add_node(monitor_node)\n",
                "\n",
                "# Create a cluster subgraph for backend endpoints\n",
                "backend_cluster = pydot.Cluster(\"backend_cluster\", label=\"Secure Backend APIs\", style=\"filled\", fillcolor=\"#D5F5E3\")\n",
                "\n",
                "endpoint1_node = pydot.Node(\"Endpoint1\", label=\"/pods\\n(Auth Protected)\", shape=\"box\")\n",
                "endpoint2_node = pydot.Node(\"Endpoint2\", label=\"/pods/{name}/events\\n(Auth Protected)\", shape=\"box\")\n",
                "endpoint3_node = pydot.Node(\"Endpoint3\", label=\"/pods/{name}/resources\\n(Auth Protected)\", shape=\"box\")\n",
                "\n",
                "backend_cluster.add_node(endpoint1_node)\n",
                "backend_cluster.add_node(endpoint2_node)\n",
                "backend_cluster.add_node(endpoint3_node)\n",
                "\n",
                "# Add clusters to main graph\n",
                "graph.add_subgraph(gateway_cluster)\n",
                "graph.add_subgraph(backend_cluster)\n",
                "graph.add_node(agent_node)\n",
                "\n",
                "# Create edges with descriptions\n",
                "edge1 = pydot.Edge(agent_node, auth_node, label=\"1. Auth Request\")\n",
                "edge2 = pydot.Edge(auth_node, agent_node, label=\"2. Token Response\", dir=\"back\")\n",
                "edge3 = pydot.Edge(agent_node, mcp_node, label=\"3. Tool Request + Token\")\n",
                "\n",
                "edge4 = pydot.Edge(mcp_node, endpoint1_node, label=\"API Call\")\n",
                "edge5 = pydot.Edge(mcp_node, endpoint2_node, label=\"API Call\")\n",
                "edge6 = pydot.Edge(mcp_node, endpoint3_node, label=\"API Call\")\n",
                "\n",
                "edge7 = pydot.Edge(mcp_node, monitor_node, style=\"dotted\", label=\"Logging\")\n",
                "edge8 = pydot.Edge(auth_node, monitor_node, style=\"dotted\", label=\"Logging\")\n",
                "\n",
                "# Add edges to the graph\n",
                "graph.add_edge(edge1)\n",
                "graph.add_edge(edge2)\n",
                "graph.add_edge(edge3)\n",
                "graph.add_edge(edge4)\n",
                "graph.add_edge(edge5)\n",
                "graph.add_edge(edge6)\n",
                "graph.add_edge(edge7)\n",
                "graph.add_edge(edge8)\n",
                "\n",
                "# Save and display the graph\n",
                "graph_file = \"gateway_architecture.png\"\n",
                "graph.write_png(graph_file)\n",
                "display(Image(filename=graph_file))\n",
                "\n",
                "print(\"The diagram shows the security and protocol transformation layers added by the AgentCore Gateway.\")"
            ],
            "execution_count": None,
            "outputs": []
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
    notebook["cells"].insert(arch_idx + 2, DIAGRAM_CELLS[notebook_filename]["diagram_code"])
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