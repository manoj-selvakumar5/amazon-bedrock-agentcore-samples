#!/usr/bin/env python3
"""
Script to add validation and testing cells to workshop notebooks:
- Add tool testing and validation in notebooks
- Add performance testing
- Add security validation for gateway
"""

import json
import os
from pathlib import Path

# Define the workshop directory
WORKSHOP_DIR = Path(__file__).parent
NOTEBOOKS_DIR = WORKSHOP_DIR / "notebooks"

# Validation cells for each notebook
VALIDATION_CELLS = {
    "00-single-tool-agent.ipynb": {
        "markdown_header": {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Validation and Testing\n",
                "\n",
                "Let's validate that our Agent has correctly understood the core concepts by testing it with a specific question:"
            ]
        },
        "validation_code": {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "# Validate agent understanding\n",
                "if agent:\n",
                "    print(\"Running validation test...\\n\")\n",
                "    \n",
                "    validation_prompt = (\n",
                "        \"VALIDATION TEST: A pod is reporting 98% memory usage and is in CrashLoopBackOff state. \"\n",
                "        \"In one sentence, what is the most likely issue?\"\n",
                "    )\n",
                "    \n",
                "    # Execute validation test\n",
                "    try:\n",
                "        start_time = time.time()\n",
                "        validation_response = agent(validation_prompt)\n",
                "        validation_time = round(time.time() - start_time, 2)\n",
                "        \n",
                "        print(f\"Validation completed in {validation_time} seconds\\n\")\n",
                "        print(\"Agent response:\")\n",
                "        \n",
                "        # Access the response correctly\n",
                "        if hasattr(validation_response, 'content'):\n",
                "            response_text = str(validation_response.content)\n",
                "            print(response_text)\n",
                "        elif hasattr(validation_response, 'message'):\n",
                "            response_text = str(validation_response.message)\n",
                "            print(response_text)\n",
                "        else:\n",
                "            response_text = str(validation_response)\n",
                "            print(response_text)\n",
                "        \n",
                "        # Check for key concepts in response\n",
                "        key_concepts = [\"memory\", \"leak\", \"OOM\", \"out of memory\", \"resource\", \"exhaustion\", \"limit\"]\n",
                "        found_concepts = [concept for concept in key_concepts if concept.lower() in response_text.lower()]\n",
                "        \n",
                "        print(f\"\\nValidation check:\")\n",
                "        if found_concepts:\n",
                "            print(f\"✅ Agent correctly identified key concepts: {', '.join(found_concepts)}\")\n",
                "        else:\n",
                "            print(f\"⚠️ Agent response doesn't contain expected concepts like: {', '.join(key_concepts[:3])}\")\n",
                "        \n",
                "    except Exception as e:\n",
                "        print(f\"❌ Validation test failed: {e}\")\n",
                "else:\n",
                "    print(\"❌ Agent not initialized - cannot run validation\")"
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
                "## Tool Validation and Testing\n",
                "\n",
                "Let's test our tools individually before we use them with the Agent. This helps identify any issues with specific tools:"
            ]
        },
        "validation_code": {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "# Test individual tools before agent integration\n",
                "import time\n",
                "from IPython.display import clear_output\n",
                "\n",
                "# Function to run tool and measure performance\n",
                "def test_tool(tool_func, **params):\n",
                "    start_time = time.time()\n",
                "    result = tool_func(**params)\n",
                "    duration = time.time() - start_time\n",
                "    return result, duration\n",
                "\n",
                "# Run validation tests\n",
                "print(\"Running validation tests on tools...\\n\")\n",
                "\n",
                "# Test 1: Tool status check\n",
                "tool_statuses = {}\n",
                "\n",
                "# Test get_pod_status\n",
                "result1, time1 = test_tool(get_pod_status)\n",
                "tool_statuses[\"get_pod_status\"] = {\n",
                "    \"success\": \"Pod:\" in result1, \n",
                "    \"time\": round(time1, 2),\n",
                "    \"status\": \"✅ Pass\" if \"Pod:\" in result1 else \"❌ Fail\"\n",
                "}\n",
                "\n",
                "# Test get_pod_events\n",
                "result2, time2 = test_tool(get_pod_events, pod_name=\"payment-service-7d4f8-x5m1q\")\n",
                "tool_statuses[\"get_pod_events\"] = {\n",
                "    \"success\": \"OutOfMemoryKilled\" in result2, \n",
                "    \"time\": round(time2, 2),\n",
                "    \"status\": \"✅ Pass\" if \"OutOfMemoryKilled\" in result2 else \"❌ Fail\"\n",
                "}\n",
                "\n",
                "# Test get_pod_resources\n",
                "result3, time3 = test_tool(get_pod_resources, pod_name=\"payment-service-7d4f8-x5m1q\")\n",
                "tool_statuses[\"get_pod_resources\"] = {\n",
                "    \"success\": \"Memory Usage History\" in result3, \n",
                "    \"time\": round(time3, 2),\n",
                "    \"status\": \"✅ Pass\" if \"Memory Usage History\" in result3 else \"❌ Fail\"\n",
                "}\n",
                "\n",
                "# Display results\n",
                "print(\"Tool Validation Results:\")\n",
                "for tool_name, data in tool_statuses.items():\n",
                "    print(f\"{data['status']} {tool_name} ({data['time']}s)\")\n",
                "    \n",
                "# Check if all tools passed\n",
                "all_passed = all(data[\"success\"] for data in tool_statuses.values())\n",
                "print(f\"\\nOverall: {'✅ All tools working properly' if all_passed else '❌ Some tools failed'}\")\n",
                "\n",
                "# Calculate average tool response time\n",
                "avg_time = sum(data[\"time\"] for data in tool_statuses.values()) / len(tool_statuses)\n",
                "print(f\"Average tool response time: {round(avg_time, 2)}s\")"
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
                "## Gateway Security Validation\n",
                "\n",
                "Let's test the security features of our Gateway implementation to ensure it's providing the expected protections:"
            ]
        },
        "validation_code": {
            "cell_type": "code",
            "metadata": {},
            "source": [
                "# Validate gateway security features\n",
                "import time\n",
                "from IPython.display import clear_output\n",
                "\n",
                "# Test function to validate gateway security aspects\n",
                "def validate_gateway_security():\n",
                "    security_tests = {}\n",
                "    \n",
                "    # Test 1: Authentication required\n",
                "    try:\n",
                "        # Test unauthenticated access\n",
                "        response = requests.get(\"http://127.0.0.1:8000/pods\")\n",
                "        if response.status_code == 401:\n",
                "            security_tests[\"Authentication Required\"] = \"✅ Passed - Authentication enforced\"\n",
                "        else:\n",
                "            security_tests[\"Authentication Required\"] = \"❌ Failed - No authentication required\"\n",
                "    except Exception as e:\n",
                "        security_tests[\"Authentication Required\"] = f\"⚠️ Test error: {str(e)[:50]}...\"\n",
                "        \n",
                "    # Test 2: Token management\n",
                "    try:\n",
                "        # Test token refresh by invalidating current token\n",
                "        original_token = gateway_client.token\n",
                "        gateway_client.token = \"invalid_token\"\n",
                "        \n",
                "        # This should throw an error or auto-refresh the token\n",
                "        try:\n",
                "            response = gateway_client.call_tool(\"get_pod_status\")\n",
                "            \n",
                "            if gateway_client.token != \"invalid_token\" and gateway_client.token != original_token:\n",
                "                security_tests[\"Token Refresh\"] = \"✅ Passed - Token auto-refreshed\"\n",
                "            else:\n",
                "                security_tests[\"Token Refresh\"] = \"❌ Failed - Token not refreshed\"\n",
                "        except Exception as e:\n",
                "            if \"401\" in str(e) or \"unauthorized\" in str(e).lower() or \"authentication\" in str(e).lower():\n",
                "                security_tests[\"Token Refresh\"] = \"✅ Passed - Invalid token rejected\"\n",
                "            else:\n",
                "                security_tests[\"Token Refresh\"] = f\"❌ Failed - Unexpected error: {str(e)[:50]}...\"\n",
                "            \n",
                "        # Restore original token\n",
                "        gateway_client.token = original_token\n",
                "    except Exception as e:\n",
                "        security_tests[\"Token Refresh\"] = f\"❌ Failed - {str(e)[:50]}...\"\n",
                "        gateway_client.token = original_token\n",
                "    \n",
                "    # Test 3: Tool validation\n",
                "    try:\n",
                "        gateway_client.call_tool(\"nonexistent_tool\")\n",
                "        security_tests[\"Tool Validation\"] = \"❌ Failed - Invalid tool not rejected\"\n",
                "    except ValueError:\n",
                "        security_tests[\"Tool Validation\"] = \"✅ Passed - Invalid tool rejected\"\n",
                "    except Exception as e:\n",
                "        if \"not found\" in str(e).lower() or \"unknown\" in str(e).lower() or \"invalid\" in str(e).lower():\n",
                "            security_tests[\"Tool Validation\"] = \"✅ Passed - Invalid tool rejected\"\n",
                "        else:\n",
                "            security_tests[\"Tool Validation\"] = f\"⚠️ Partial - {type(e).__name__} raised\"\n",
                "        \n",
                "    return security_tests\n",
                "\n",
                "# Run the validation\n",
                "print(\"Running Gateway security validation...\")\n",
                "security_results = validate_gateway_security()\n",
                "\n",
                "# Display results\n",
                "print(\"\\nGateway Security Validation Results:\")\n",
                "for test_name, result in security_results.items():\n",
                "    print(f\"{test_name}: {result}\")\n",
                "\n",
                "# Overall assessment\n",
                "passes = sum(1 for result in security_results.values() if \"✅ Passed\" in result)\n",
                "print(f\"\\nSecurity Score: {passes}/{len(security_results)} tests passed\")"
            ],
            "execution_count": None,
            "outputs": []
        }
    }
}

def find_insertion_point_for_validation(notebook, notebook_filename):
    """Find appropriate insertion point for validation cells."""
    # For all notebooks, insert before the Summary section
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "markdown":
            source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            if "## Summary" in source or "## Summary and Next Steps" in source:
                return i
    
    # If no Summary section found, insert before the last cell
    return len(notebook["cells"]) - 1

def add_validation(notebook_path, notebook_filename):
    """Add validation cells to a notebook."""
    if notebook_filename not in VALIDATION_CELLS:
        print(f"⚠️ No validation cells defined for {notebook_filename}")
        return
    
    # Read notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find insertion point
    insert_idx = find_insertion_point_for_validation(notebook, notebook_filename)
    if insert_idx == -1:
        print(f"⚠️ Could not find insertion point for {notebook_filename}")
        return
    
    # Insert validation cells
    notebook["cells"].insert(insert_idx, VALIDATION_CELLS[notebook_filename]["markdown_header"])
    notebook["cells"].insert(insert_idx + 1, VALIDATION_CELLS[notebook_filename]["validation_code"])
    print(f"✅ Added validation cells to {notebook_filename}")
    
    # Write updated notebook
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)

def main():
    """Main function to add validation cells."""
    # Get all notebook files
    notebook_files = list(NOTEBOOKS_DIR.glob("*.ipynb"))
    
    if not notebook_files:
        print(f"⚠️ No notebook files found in {NOTEBOOKS_DIR}")
        return
    
    # Add validation cells to each notebook
    for notebook_path in notebook_files:
        notebook_filename = notebook_path.name
        add_validation(notebook_path, notebook_filename)
    
    print(f"✅ Added validation cells to notebooks")

if __name__ == "__main__":
    main()