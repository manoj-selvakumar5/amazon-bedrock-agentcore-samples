# IAM Policy Changes Report: AgentCore Lab Enhancement

## Executive Summary

This report documents the changes made to the IAM policy for the Amazon Bedrock AgentCore workshop. The updated policy (`iam-policy-with-agentcore-lab.json`) maintains the complete structure and permissions of the original policy while adding a single new statement that grants comprehensive AgentCore lab permissions required for workshop exercises.

## File Overview

| File | Statements | Purpose |
|------|------------|---------|
| `iam-policy-original.json` | 15 | Base workshop permissions |
| `iam-policy-with-agentcore-lab.json` | 16 | Enhanced with AgentCore lab capabilities |

## Changes Analysis

### ✅ Preserved Elements

**All 15 original statements remain completely unchanged:**

1. **AllReaperSupportedServices** - AWS service permissions (CloudFormation, Lambda, S3, etc.)
2. **BedrockAgentCoreReadPermission** - Basic AgentCore read/invoke permissions
3. **BedrockAgentCoreObservability** - Application signals discovery
4. **AmazonBedrockReadOnly** - Bedrock service read-only access
5. **EC2Permissions** - VPC and subnet describe permissions
6. **BedrockPolicies** - Model invocation and tagging permissions
7. **BedrockModelSubscriptions** - Marketplace subscription management
8. **DenyXXLInstances** - Prevention of expensive EC2 instance launches
9. **DontBuyEC2ReservationsPlz** - EC2 reservation purchase restrictions
10. **DontBuyRDSReservationsPlz** - RDS reservation purchase restrictions
11. **DontBuyDynamodbReservationsPlz** - DynamoDB reservation purchase restrictions
12. **PassRoleToBedrock** - IAM role management for Bedrock services
13. **PassRole** - Participant role passing permissions
14. **BedrockModelAccess** - Allowed foundation models (Titan, Claude, Nova)
15. **DenyBedrockModelAccessForOtherModels** - Blocked foundation models

### ➕ New Addition

**Statement #16: BedrockAgentCoreLabAccess**

A comprehensive set of 19 AgentCore permissions enabling advanced workshop capabilities.

## New Permissions Breakdown

### Memory Management (4 permissions)
- `bedrock-agentcore:CreateMemory` - Create agent memory stores
- `bedrock-agentcore:UpdateMemory` - Modify memory configurations  
- `bedrock-agentcore:GetMemory` - Retrieve memory details
- `bedrock-agentcore:ListMemories` - List available memories

### Gateway Operations (4 permissions)
- `bedrock-agentcore:CreateGateway` - Create communication gateways
- `bedrock-agentcore:CreateGatewayTarget` - Define gateway endpoints
- `bedrock-agentcore:GetGateway` - Retrieve gateway configurations
- `bedrock-agentcore:ListGateways` - List configured gateways

### Agent Runtime Management (5 permissions)
- `bedrock-agentcore:CreateAgentRuntime` - Create agent runtime instances
- `bedrock-agentcore:UpdateAgentRuntime` - Modify runtime configurations
- `bedrock-agentcore:GetAgentRuntime` - Retrieve runtime details
- `bedrock-agentcore:ListAgentRuntimes` - List agent runtimes
- `bedrock-agentcore:InvokeAgentRuntime` - Execute runtime operations

### Session & Event Handling (3 permissions)
- `bedrock-agentcore:ListSessions` - List active agent sessions
- `bedrock-agentcore:CreateEvent` - Create agent events
- `bedrock-agentcore:GetEvent` - Retrieve event information

### Memory Records Access (2 permissions)
- `bedrock-agentcore:RetrieveMemoryRecords` - Access stored memory data
- `bedrock-agentcore:ListMemoryRecords` - List memory records

### Observability (1 permission)
- `bedrock-agentcore:AllowVendedLogDeliveryForResource` - Enable logging for AgentCore resources

## Technical Specifications

### File Structure Preservation
- **JSON formatting**: Maintained original 4-space indentation
- **Statement order**: Preserved exact sequence from original file
- **Field ordering**: Kept original field arrangement within statements
- **Resource specifications**: All wildcard (`*`) and ARN patterns unchanged
- **Conditions**: All conditional logic preserved exactly

### Permission Scope
- **Resource targeting**: All new permissions apply to `"Resource": "*"` (global scope)
- **Effect**: All new permissions use `"Effect": "Allow"`
- **No conflicts**: New permissions do not override or conflict with existing restrictions

## Impact Assessment

### Enabled Capabilities
The new permissions enable workshop participants to:

1. **Build Intelligent Agents** - Create and manage agent runtimes with persistent memory
2. **Implement Communication Patterns** - Set up gateways for agent-to-agent communication
3. **Monitor Agent Behavior** - Track sessions, events, and memory usage
4. **Debug and Troubleshoot** - Access logs and memory records for analysis
5. **Iterate and Improve** - Update agent configurations and memory stores

### Security Considerations
- **Principle of Least Privilege**: Permissions are scoped specifically to AgentCore services
- **No Elevation**: No additional IAM or administrative permissions granted
- **Existing Restrictions Maintained**: All cost-control and model access restrictions remain in place

## Recommendations

### Implementation
1. **Deploy Gradually**: Test with a subset of workshop participants first
2. **Monitor Usage**: Track AgentCore API calls to ensure expected usage patterns
3. **Review Logs**: Monitor CloudTrail for AgentCore operations

### Future Considerations
- **Cleanup**: Consider removing AgentCore lab permissions after workshop completion
- **Refinement**: May narrow permissions based on actual workshop requirements
- **Documentation**: Update workshop materials to reflect new capabilities

## Conclusion

The enhanced IAM policy successfully adds comprehensive AgentCore lab functionality while maintaining all existing permissions and security controls. This additive approach ensures backward compatibility while enabling advanced workshop exercises involving agent memory, communication gateways, and runtime management.

---
*Report generated: 2025-09-10*  
*Files analyzed: `iam-policy-original.json`, `iam-policy-with-agentcore-lab.json`*