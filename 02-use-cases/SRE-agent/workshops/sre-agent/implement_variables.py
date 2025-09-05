#!/usr/bin/env python3
"""
Script to add variable management to workshop notebooks:
- Add variable storage cells at the end of notebooks
- Add variable loading cells at the beginning of notebooks
- Implement proper variable progression between notebooks
"""

import json
import os
import re
from pathlib import Path

# Define the workshop directory
WORKSHOP_DIR = Path(__file__).parent
NOTEBOOKS_DIR = WORKSHOP_DIR / "notebooks"

# Variable cells content for each notebook
VARIABLE_CELLS = {
    "00-single-tool-agent.ipynb": {
        "store": {
            "cell_type": "code",
            "source": [
                "# Store important variables for the next notebook\n",
                "# These will be available when you run %store -r in the next notebook\n",
                "%store model_id = model.model_id if agent else \"us.anthropic.claude-3-haiku-20240307-v1:0\"\n",
                "%store pod_data_schema = PODS_DATA\n",
                "\n",
                "print(\"✅ Variables stored for next notebook\")"
            ],
            "metadata": {},
            "execution_count": None,
            "outputs": []
        }
    },
    "01-multiple-tools-agent.ipynb": {
        "load": {
            "cell_type": "code",
            "source": [
                "# Load variables from previous notebook\n",
                "try:\n",
                "    %store -r model_id\n",
                "    %store -r pod_data_schema\n",
                "    \n",
                "    # Use loaded variables\n",
                "    print(f\"✅ Loaded variables from previous notebook\")\n",
                "    print(f\"   Using model ID: {model_id}\")\n",
                "    \n",
                "    # We'll use the pod schema as a reference for our enhanced data model\n",
                "    print(f\"   Loaded basic pod schema with pod data\")\n",
                "    \n",
                "except NameError as e:\n",
                "    print(f\"⚠️ Could not load some variables from previous notebook: {e}\")\n",
                "    print(\"   Setting default values instead\")\n",
                "    \n",
                "    # Set defaults if variables weren't loaded\n",
                "    if 'model_id' not in locals():\n",
                "        model_id = \"us.anthropic.claude-3-haiku-20240307-v1:0\"\n",
                "        print(f\"   Using default model ID: {model_id}\")\n",
                "        \n",
                "    if 'pod_schema' not in locals():\n",
                "        pod_data_schema = None"
            ],
            "metadata": {},
            "execution_count": None,
            "outputs": []
        },
        "store": {
            "cell_type": "code",
            "source": [
                "# Store important variables for the next notebook\n",
                "%store model_id = model.model_id if agent else \"us.anthropic.claude-3-haiku-20240307-v1:0\"\n",
                "%store events_data_schema = EVENTS_DATA\n",
                "%store resources_data_schema = RESOURCES_DATA\n",
                "\n",
                "print(\"✅ Variables stored for next notebook\")"
            ],
            "metadata": {},
            "execution_count": None,
            "outputs": []
        }
    },
    "02-gateway-integration.ipynb": {
        "load": {
            "cell_type": "code",
            "source": [
                "# Load variables from previous notebook\n",
                "try:\n",
                "    %store -r model_id\n",
                "    %store -r events_data_schema\n",
                "    %store -r resources_data_schema\n",
                "    \n",
                "    # Use loaded variables\n",
                "    print(f\"✅ Loaded variables from previous notebook\")\n",
                "    print(f\"   Using model ID: {model_id}\")\n",
                "    \n",
                "    # We'll use these schemas to build our gateway MCP configuration\n",
                "    print(\"   Loaded data schemas for MCP configuration\")\n",
                "    \n",
                "except NameError as e:\n",
                "    print(f\"⚠️ Could not load some variables from previous notebook: {e}\")\n",
                "    print(\"   Setting default values instead\")\n",
                "    \n",
                "    # Set defaults if variables weren't loaded\n",
                "    if 'model_id' not in locals():\n",
                "        model_id = \"us.anthropic.claude-3-haiku-20240307-v1:0\"\n",
                "        \n",
                "    if 'events_data_schema' not in locals() or 'resources_data_schema' not in locals():\n",
                "        print(\"   No data schemas loaded - will create from scratch\")"
            ],
            "metadata": {},
            "execution_count": None,
            "outputs": []
        },
        "store": {
            "cell_type": "code",
            "source": [
                "# Store Gateway configuration for future notebooks\n",
                "import uuid\n",
                "\n",
                "%store gateway_id = f\"mock-gateway-{uuid.uuid4().hex[:8]}\"\n",
                "%store gateway_config_data = gateway_config\n",
                "%store mcp_tools_config_data = mcp_tools_config\n",
                "\n",
                "print(\"✅ Gateway configuration stored for future notebooks\")"
            ],
            "metadata": {},
            "execution_count": None,
            "outputs": []
        }
    }
}

def find_section_marker(notebook, marker_text):
    """Find a cell index that contains the specified marker text."""
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "markdown":
            source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            if marker_text in source:
                return i
    return -1

def add_variable_management(notebook_path, notebook_filename):
    """Add variable management cells to a notebook."""
    if notebook_filename not in VARIABLE_CELLS:
        print(f"⚠️ No variable cells defined for {notebook_filename}")
        return
    
    # Read notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Add variable loading cell after imports
    if "load" in VARIABLE_CELLS[notebook_filename]:
        # Find a good position after imports
        for i, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code" and any(
                line.startswith("import ") or "from " in line
                for line in (cell["source"] if isinstance(cell["source"], list) else [cell["source"]])
            ):
                # Insert after this cell
                insert_position = i + 1
                
                # Create markdown header for variables section
                var_header = {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Load Variables from Previous Notebook\n", "\n", "Load any variables saved from previous notebook sessions."]
                }
                
                # Insert cells
                notebook["cells"].insert(insert_position, var_header)
                notebook["cells"].insert(insert_position + 1, VARIABLE_CELLS[notebook_filename]["load"])
                print(f"✅ Added variable loading cell to {notebook_filename}")
                break
    
    # Add variable storage cell before summary
    if "store" in VARIABLE_CELLS[notebook_filename]:
        # Find summary section
        summary_idx = find_section_marker(notebook, "## Summary")
        if summary_idx == -1:
            summary_idx = find_section_marker(notebook, "### Summary")
        
        if summary_idx != -1:
            # Create markdown header for storage section
            store_header = {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Store Variables for Next Notebook\n", "\n", "Store important variables for use in the next notebook."]
            }
            
            # Insert cells
            notebook["cells"].insert(summary_idx, store_header)
            notebook["cells"].insert(summary_idx + 1, VARIABLE_CELLS[notebook_filename]["store"])
            print(f"✅ Added variable storage cell to {notebook_filename}")
        else:
            # Add at the end if no summary section
            notebook["cells"].append({
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Store Variables for Next Notebook\n", "\n", "Store important variables for use in the next notebook."]
            })
            notebook["cells"].append(VARIABLE_CELLS[notebook_filename]["store"])
            print(f"✅ Added variable storage cell to the end of {notebook_filename}")
    
    # Write updated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)

def main():
    """Main function to add variable management to all notebooks."""
    # Get all notebook files
    notebook_files = list(NOTEBOOKS_DIR.glob("*.ipynb"))
    
    if not notebook_files:
        print(f"⚠️ No notebook files found in {NOTEBOOKS_DIR}")
        return
    
    # Add variable management to each notebook
    for notebook_path in notebook_files:
        notebook_filename = notebook_path.name
        add_variable_management(notebook_path, notebook_filename)
    
    print(f"✅ Added variable management to notebooks")

if __name__ == "__main__":
    main()