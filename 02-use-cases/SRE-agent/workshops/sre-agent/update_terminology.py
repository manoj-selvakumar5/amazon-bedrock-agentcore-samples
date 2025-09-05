#!/usr/bin/env python3
"""
Script to update terminology in workshop notebooks:
- Replace "AI Agent" with "Agent" 
- Replace "Module" with "Notebook"
- Update other terminology for consistency
"""

import json
import os
import re
from pathlib import Path

# Define the workshop directory
WORKSHOP_DIR = Path(__file__).parent
NOTEBOOKS_DIR = WORKSHOP_DIR / "notebooks"

def update_notebook_cell(cell, replacements):
    """Update content of a notebook cell."""
    if cell["cell_type"] == "markdown" or cell["cell_type"] == "code":
        # Handle source as either string or list
        if isinstance(cell["source"], list):
            updated_source = []
            for line in cell["source"]:
                updated_line = line
                for pattern, replacement in replacements:
                    updated_line = re.sub(pattern, replacement, updated_line)
                updated_source.append(updated_line)
            cell["source"] = updated_source
        else:
            for pattern, replacement in replacements:
                cell["source"] = re.sub(pattern, replacement, cell["source"])
    
    return cell

def update_notebook(notebook_path, replacements):
    """Update terminology in a Jupyter notebook."""
    # Read notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Update each cell
    for cell in notebook["cells"]:
        update_notebook_cell(cell, replacements)
    
    # Write updated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)
    
    print(f"✅ Updated {notebook_path}")

def main():
    """Main function to update terminology in all notebooks."""
    # Define replacements as (pattern, replacement) tuples
    replacements = [
        (r'AI INVESTIGATION RESULTS', 'AGENT INVESTIGATION RESULTS'),
        (r'AI investigation', 'Agent investigation'),
        (r'What the AI Agent did', 'What the Agent did'),
        (r'AI Agent', 'Agent'),
        (r'AI-powered', 'Agent-powered'),
        (r'This module demonstrated', 'This notebook demonstrated'),
        (r'Module (\d+)', r'Notebook \1'),
        (r'module demonstrated', 'notebook demonstrated')
    ]
    
    # Get all notebook files
    notebook_files = list(NOTEBOOKS_DIR.glob("*.ipynb"))
    
    if not notebook_files:
        print(f"⚠️ No notebook files found in {NOTEBOOKS_DIR}")
        return
    
    # Update each notebook
    for notebook_path in notebook_files:
        update_notebook(notebook_path, replacements)
    
    print(f"✅ Updated terminology in {len(notebook_files)} notebooks")

if __name__ == "__main__":
    main()