# SRE Agent Workshop Notebooks Analysis Prompt

## Objective

Conduct a comprehensive technical analysis and critical evaluation of the Amazon Bedrock AgentCore SRE workshop notebooks, focusing on clarity, technical accuracy, and educational effectiveness. Rewrite content where necessary to improve the learning experience while maintaining technical precision.

## Target Audience

This content is developed at the 300-level (advanced) for developers who already possess fundamental knowledge of:

- Generative AI concepts and implementations
- Large Language Models (LLMs) and their capabilities
- Agent architectures and orchestration patterns
- AWS services and cloud infrastructure

The workshop assumes participants have moved beyond basic concepts and are ready to implement production-grade solutions with Amazon Bedrock AgentCore.

## Analysis Requirements

### Technical Accuracy

1. **Bedrock AgentCore Concepts**:
   - Research Amazon Bedrock AgentCore in depth
   - Ensure all explanations of Gateway, Memory, Runtime, MCP protocol, and other AgentCore components are technically accurate
   - Identify any conceptual errors or oversimplifications in the current notebooks

2. **Architecture Explanations**:
   - Evaluate the clarity of architectural explanations
   - Verify the relationship between components is correctly represented
   - Ensure proper explanation of how various services interact

3. **Technical Consistency Requirements**:
   - **Model Consistency**: Ensure model references match between architecture diagrams, code implementation, and documentation
   - **Port Accuracy**: Verify port numbers and URLs are consistent across diagrams and code
   - **Service Names**: Use accurate Amazon Bedrock AgentCore service names throughout
   - **Terminology Precision**: Replace all "AI Agent" with "Strands Agent" or "SRE Agent" consistently
   - **Code-Documentation Alignment**: Ensure technical details in markdown cells match actual implementation

4. **Model Configuration Standards**:
   - **Preferred Models**: Use Claude 3.7 Sonnet inference profiles for optimal performance
   - **Model ID Format**: Use complete model IDs (e.g., `us.anthropic.claude-3-7-sonnet-20250219-v1:0`)
   - **Consistency Check**: Verify model references are identical in:
     - Prerequisites section
     - Architecture diagrams
     - Code implementation
     - Comments and documentation
   - **Regional Considerations**: Ensure model availability matches the specified AWS region

### Content Quality

1. **Progression Logic**:
   - Assess if each notebook builds progressively on previous concepts
   - Verify appropriate complexity increase between notebooks
   - Ensure new concepts are properly introduced and explained

2. **Educational Value**:
   - Evaluate effectiveness of teaching approaches
   - Identify areas where explanations could be enhanced
   - Suggest improvements to help users grasp complex concepts

3. **Markdown Content**:
   - Evaluate clarity, organization, and effectiveness of all markdown cells
   - Suggest improvements for explanatory text
   - Ensure consistency in terminology and tone

### Architecture Diagrams

For each notebook, suggest improvements for the architecture diagrams. Include detailed specifications for:
Example:
1. **Notebook 1: Multiple Tools Architecture Diagram**
   - [DIAGRAM PLACEHOLDER: Multi-tool Agent Architecture]
   - Components to include:
     - Strands Agent with Claude 3 Haiku
     - Three tool functions (get_pod_status, get_pod_events, get_pod_resources)
     - FastAPI backend with data stores
     - Data flow and request/response patterns
   - Highlight the orchestration flow and multi-pod analysis capabilities

## Technical Deep Dives Required

1. **AgentCore Gateway**
   - Explain the gateway architecture in detail
   - Clarify how it enhances security through authentication
   - Detail MCP protocol transformation processes
   - Describe production deployment considerations

2. **Strands Framework Integration**
   - Explain how Strands integrates with Bedrock models
   - Detail the @tool decorator functionality and limitations
   - Clarify tool orchestration patterns

3. **Tool Design Patterns**
   - Analyze the design patterns used in tool implementation
   - Evaluate error handling approaches
   - Suggest improvements for resilience and observability

## Code Documentation Standards

### Function Docstrings Requirements
1. **AWS-Style Formatting**: Use comprehensive docstrings with proper sections:
   - Brief description of function purpose
   - Args section with type hints and descriptions
   - Returns section with type and detailed description
   - Raises section for exceptions
   - Note section for additional context

2. **Example Format**:
   ```python
   @tool
   def get_pod_status(namespace: str = "production") -> str:
       """
       Get comprehensive status information for Kubernetes pods in the specified namespace.
       
       This tool function is designed to work with Strands Agents and provides detailed pod 
       information for SRE troubleshooting scenarios.
       
       Args:
           namespace (str): Kubernetes namespace to query. Defaults to "production".
           
       Returns:
           str: Formatted string containing comprehensive pod status information including:
                - Pod health and readiness status
                - Resource usage (CPU and memory)  
                - Container status and restart information
                
       Raises:
           requests.RequestException: If the API request fails
           Exception: For other unexpected errors
           
       Note:
           This tool is decorated with @tool to make it available to Strands Agents.
       """
   ```

### Inline Comments Standards
1. **Educational Clarity**: Add detailed inline comments explaining Strands Agent concepts
2. **AgentCore Integration**: Comment on how code integrates with Amazon Bedrock AgentCore
3. **Technical Context**: Explain why specific patterns or approaches are used
4. **Learning Support**: Help users understand complex concepts through contextual comments

### Examples of Proper Inline Comments:
```python
# Create Bedrock model instance
# BedrockModel handles the connection to Amazon Bedrock service
model = BedrockModel(model_id=MODEL_ID, region=REGION)

# Create Strands Agent with comprehensive SRE system prompt
# The Agent class from Strands orchestrates model calls and tool usage
agent = Agent(
    model=model,  # Amazon Bedrock model for reasoning
    tools=[get_pod_status],  # List of tools available to the agent
    system_prompt="""..."""
)
```

## Formatting and Style Standards

### Emoji Usage Standards
1. **Strict Emoji Policy**: Use only ✅ and ❌ emojis throughout all notebooks for status indicators
2. **No Other Emojis**: Remove all other emojis (🚀, 🎯, 📁, 📚, 💡, 🔌, ⚠️, ⚡, 🚨, 📋, 🤝, etc.)
3. **Consistent Application**: Apply emoji standards consistently across all cells and documentation
4. **CLAUDE.md Compliance**: Follow the global instruction to use minimal emoji usage with only ✅ and ❌

### Markdown Formatting Standards
1. **Architecture Diagrams**: Always format architecture diagrams in proper markdown code blocks using ```text
2. **Section Hierarchy**: Maintain consistent heading structure and proper nesting
3. **Code Block Formatting**: Use appropriate language identifiers in code blocks
4. **Consistent Formatting**: Ensure uniform styling across all markdown cells

## Terminology Guidelines

1. Always use "Notebook" instead of "Module" when referring to individual workshop components
2. Use precise AWS service names (e.g., "Amazon Bedrock AgentCore" not just "AgentCore")  
3. **Critical**: Use "Strands Agent" or "SRE Agent" instead of "AI Agent" throughout all content
4. Assume the audience has advanced knowledge - avoid explaining basic concepts
5. Maintain consistent terminology for technical concepts throughout
6. Use technically precise language appropriate for a 300-level audience

## Notebook Variables Management

Evaluate and enhance the management of notebook variables for a seamless workshop experience:

1. **Variable Persistence Between Notebooks**:
   - Ensure each notebook properly stores key variables needed for subsequent notebooks
   - Add clear sections for variable storage at the end of each notebook
   - Include proper loading of previous variables at the beginning of each notebook

2. **Implementation Requirements**:
   - Use Jupyter's `%store` magic command for variable persistence
   - Add a "Prerequisites" section at the beginning of notebooks that require variables from previous notebooks
   - Include clear code examples like:
     ```python
     # Load variables from previous notebook
     %store -r agent_id
     %store -r knowledge_base_name
     # etc.
     ```
   - Add a "Next Steps" section at the end of notebooks to store variables needed later:
     ```python
     # Store variables for the next notebook
     %store kb_id
     %store knowledge_base_name
     %store bucket_name
     # etc.
     ```

3. **Error Prevention**:
   - Include validation checks for loaded variables
   - Add fallback mechanisms if variables aren't available
   - Provide troubleshooting guidance for variable persistence issues

## Implementation Standards

### Notebook Update Checklist
When updating workshop notebooks to meet AWS standards, follow this systematic approach:

1. **Formatting Review**:
   - ✅ Replace all emojis with only ✅ and ❌
   - ✅ Format architecture diagrams in proper markdown code blocks
   - ✅ Ensure consistent section hierarchy and formatting

2. **Code Documentation Enhancement**:
   - ✅ Update function docstrings with AWS-style formatting (Args, Returns, Raises, Note)
   - ✅ Add comprehensive inline comments explaining Strands Agent concepts
   - ✅ Include educational context for AgentCore integration points

3. **Technical Accuracy Verification**:
   - ✅ Replace all "AI Agent" references with "Strands Agent" or "SRE Agent"
   - ✅ Verify model consistency across documentation and code
   - ✅ Check port numbers and technical details match between diagrams and implementation
   - ✅ Ensure Amazon Bedrock AgentCore service names are accurate

4. **Model Configuration Validation**:
   - ✅ Use Claude 3.7 Sonnet inference profile where specified
   - ✅ Include complete model IDs in code
   - ✅ Verify model references match across all sections

### Successful Implementation Example
The `00-single-tool-agent-improved.ipynb` notebook serves as the reference implementation for these standards. Key improvements made include:

- **Emoji Standardization**: Removed 🚀, 🚨, ⚡, ⚠️ emojis and used only ✅ and ❌
- **Architecture Diagram**: Formatted in proper markdown code block with technical accuracy
- **Enhanced Docstrings**: Added comprehensive AWS-style documentation for `get_pod_status()` function
- **Inline Comments**: Added educational comments explaining Strands Agent concepts and BedrockModel usage
- **Terminology Consistency**: Replaced "AI Agent" with "Strands Agent" or "SRE Agent" throughout
- **Model Accuracy**: Updated to use Claude 3.7 Sonnet inference profile consistently
- **Technical Precision**: Ensured port numbers and service names are accurate

## Technical Resources

Use the following resources to ensure accuracy in your analysis:

1. AWS Bedrock AgentCore documentation
2. Model Context Protocol (MCP) specifications
3. Strands Agents framework documentation
4. FastAPI best practices
5. OAuth 2.0 authentication standards
6. Kubernetes API specifications
7. Jupyter notebook variable persistence documentation





## Latest Notebook Improvements Summary

### Key Changes Made to 00-single-tool-agent-improved.ipynb
The following improvements have been successfully implemented to align with AWS documentation standards:

#### 1. **Formatting and Style Standardization**
- **Emoji Cleanup**: Replaced all emojis (🚀, 🚨, ⚡, ⚠️) with only ✅ and ❌ status indicators
- **Architecture Diagram**: Formatted diagram in proper markdown code block with consistent technical details
- **AWS Callouts**: Added proper `> [!IMPORTANT]` callout for experimental nature disclaimer
- **Consistent Formatting**: Ensured uniform styling across all markdown cells

#### 2. **Code Documentation Enhancement**
- **Enhanced Docstrings**: Upgraded `get_pod_status()` function with comprehensive AWS-style docstring including Args, Returns, Raises, and Note sections
- **Educational Comments**: Added detailed inline comments explaining:
  - Strands Agent concepts and integration patterns
  - Amazon Bedrock AgentCore connection handling
  - Tool orchestration and LLM consumption formatting
  - Context for SRE troubleshooting scenarios

#### 3. **Technical Accuracy Corrections**
- **Terminology Consistency**: Replaced all "AI Agent" references with "Strands Agent" or "SRE Agent"
- **Model Consistency**: Updated to use Claude 3.7 Sonnet inference profile throughout (MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
- **Port Accuracy**: Verified port 8000 consistency between architecture diagram and code implementation
- **Service Names**: Ensured accurate Amazon Bedrock AgentCore service references

#### 4. **Educational Value Improvements**
- **Progressive Learning**: Enhanced explanations to build understanding step-by-step
- **Technical Context**: Added comments explaining why specific patterns are used
- **Integration Clarity**: Improved explanations of how components work together

The updated notebook now serves as a reference implementation for AWS documentation standards while maintaining its educational effectiveness for advanced users learning Amazon Bedrock AgentCore and Strands Agents.