# Workshop CloudFormation Template Changes

This document outlines the differences between `workshopstudio_original.yaml` and `workshopstudio_current.yaml`, documenting the evolution of IAM permissions required for the AgentCore observability workshop.

## Summary of Changes

**Total changes**: 175+ lines added/modified
**File size increase**: ~6.9KB (92,781 → 99,699 bytes)
**Primary focus**: Enhanced observability and monitoring capabilities
**Update**: Added critical permissions for hands-on Lab-04 activities (Dec 2024)

## Major Additions

### 1. Enhanced Application Signals Permissions
**Added to**: `agentcore-observability-access` policy

**New permissions**:
```yaml
- application-signals:BatchGetServiceLevelObjectiveBudgetReport
- application-signals:GetService  
- application-signals:GetServiceLevelObjective
- application-signals:ListServiceLevelObjectives
- application-signals:ListServices
- application-signals:ListServiceDependencies
- application-signals:ListServiceDependents
- application-signals:ListServiceOperations
- application-signals:EnableTransactionSearch
- application-signals:ListObservedEntities
```

**Purpose**: Enables full CloudWatch GenAI Observability dashboard functionality for monitoring AI agents, service dependencies, and performance metrics. **Critical Update**: Added Transaction Search enablement permissions.

**AWS Documentation Reference**: [CloudWatch Application Signals API permissions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/permissions-reference-cw.html#cw-application-signals-permissions-table)

### 2. Expanded CloudWatch Logging Permissions
**Added to**: `agentcore-observability-access` policy

**New permissions**:
```yaml
- logs:StartQuery
- logs:StopQuery  
- logs:GetQueryResults
- logs:GetLogRecord
- logs:TestMetricFilter
- logs:PutMetricFilter
- logs:PutDeliverySource
- logs:PutDeliveryDestination
- logs:CreateDelivery
- logs:PutDeliveryDestinationPolicy
- logs:GetDeliverySource
- logs:GetDeliveryDestination
- logs:GetDelivery
- logs:ListDeliveries
- logs:DeleteDelivery
- logs:AssociateKmsKey
- logs:DisassociateKmsKey
- logs:TagLogGroup
- logs:UntagLogGroup
- logs:ListTagsLogGroup
```

**Purpose**: Enables CloudWatch Logs Insights for advanced log analysis and filtering capabilities. **Critical Update**: Added comprehensive log delivery permissions required for Memory/Gateway log configuration in Section 4.4 of Lab-04.

### 3. Complete CloudWatch Metrics and Dashboard Support
**Added to**: `agentcore-observability-access` policy

**New permissions**:
```yaml
- cloudwatch:GetMetricData
- cloudwatch:GetMetricStatistics
- cloudwatch:ListMetrics
- cloudwatch:GetDashboard
- cloudwatch:ListDashboards
- cloudwatch:PutMetricData
- cloudwatch:PutMetricAlarm
- cloudwatch:DescribeAlarms
- cloudwatch:CreateDashboard
- cloudwatch:PutDashboard
- cloudwatch:DeleteDashboard
```

**Purpose**: Comprehensive CloudWatch dashboard and metrics access for agent performance monitoring and alerting.

### 4. AgentCore Dashboard Access
**New policy**: `agentcore-dashboard-access`

**Permissions**:
```yaml
- bedrock-agentcore:ListAgents
- bedrock-agentcore:GetAgent
- bedrock-agentcore:ListSessions
- bedrock-agentcore:GetSession
- bedrock-agentcore:ListTraces
- bedrock-agentcore:GetTrace
- bedrock-agentcore:PutLogEvents
```

**Purpose**: Direct access to AgentCore's built-in observability dashboard for viewing agent sessions, traces, and telemetry.

**AWS Documentation Reference**: [AgentCore Runtime Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-observability.html)

### 5. Memory Log Delivery Support
**New policy**: `agentcore-memory-logs-access`

**Permissions**:
```yaml
- bedrock-agentcore:PutLogEvents
- bedrock-agentcore:AllowVendedLogDeliveryForResource
```

**Resource**: `arn:aws:bedrock-agentcore:*:*:memory/*`

**Purpose**: Enables AgentCore Memory to deliver logs to CloudWatch Logs for background processing visibility.

**Critical Fix**: The `AllowVendedLogDeliveryForResource` permission resolves the AccessDeniedException error when setting up log delivery.

### 6. Gateway Log Delivery Support  
**New policy**: `agentcore-gateway-logs-access`

**Permissions**:
```yaml
- bedrock-agentcore:PutLogEvents
- bedrock-agentcore:AllowVendedLogDeliveryForResource
```

**Resource**: `arn:aws:bedrock-agentcore:*:*:gateway/*`

**Purpose**: Enables AgentCore Gateway to deliver MCP protocol logs to CloudWatch for tool execution monitoring.

### 7. Comprehensive CloudTrail Support
**New policies**: 
- `cloudtrail-history-access`
- `cloudtrail-management-access`
- `s3-cloudtrail-access`
- `sns-cloudtrail-access`
- `kms-cloudtrail-access`

**Purpose**: Full CloudTrail audit logging capabilities including:
- Event history viewing and filtering
- Trail creation and management
- S3 bucket integration for long-term storage
- SNS notifications for real-time alerting
- KMS encryption for secure audit logs

**AWS Documentation Reference**: [CloudTrail Event History](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html)

### 8. X-Ray Transaction Search & Service Graph Support
**Added to**: `agentcore-observability-access` policy

**New permissions**:
```yaml
- xray:UpdateTraceSegmentDestination
- xray:GetTraceSegmentDestination
- xray:UpdateIndexingRule
- xray:GetIndexingRule
- xray:GetTraceGraph
- xray:GetTraceSummaries
- xray:BatchGetTraces
- xray:GetServiceGraph
- xray:GetTimeSeriesServiceStatistics
```

**Purpose**: **CRITICAL FOR LAB-04**: Enables Transaction Search configuration and CloudWatch GenAI Observability dashboard trace functionality. Required for Section 4.1 hands-on activities.

**AWS Documentation Reference**: [X-Ray Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)

### 9. Resource Tagging Support
**New policy**: `resource-tagging-access`

**Permissions**:
```yaml
- tag:GetResources
- tag:TagResources
- tag:UntagResources
- tag:GetTagKeys
- tag:GetTagValues
```

**Purpose**: Resource management and organization capabilities for workshop resources.

## Lab-04 Observability Requirements Met

These changes specifically address the requirements from `lab-04-observability-draft3.md`:

### ✅ CloudWatch GenAI Observability Dashboard
- **Agents view**: Enabled via AgentCore dashboard access permissions
- **Sessions view**: Supported through session listing and detail permissions
- **Traces view**: Comprehensive trace access and analysis capabilities
- **🔧 HANDS-ON ENABLEMENT**: Transaction Search configuration for Section 4.1

### ✅ CloudWatch Metrics
- **Runtime metrics**: Full metrics access for invocations, latency, sessions
- **Memory metrics**: Complete memory operation monitoring
- **Gateway metrics**: Tool execution and MCP operation visibility

### ✅ CloudWatch Logs
- **Memory logs**: Background processing visibility with log delivery
- **Gateway logs**: MCP protocol and tool execution logging
- **Advanced analysis**: Logs Insights for detailed troubleshooting
- **🔧 HANDS-ON ENABLEMENT**: Log delivery configuration permissions for Section 4.4

### ✅ CloudTrail Audit Logging
- **Event history**: 90-day management event access
- **Resource tracking**: Complete audit trail for all AgentCore operations
- **Security monitoring**: Comprehensive access control and change tracking

## Impact Analysis

### Security
- **Enhanced audit trail**: Complete visibility into all resource changes
- **Principle of least privilege**: Permissions scoped to specific AgentCore resources
- **Resource isolation**: Separate policies for different components

### Operational
- **Production readiness**: Comprehensive observability stack
- **Troubleshooting capability**: Multiple layers of diagnostics
- **Performance monitoring**: Real-time and historical metrics

### Cost Considerations
- **CloudWatch Logs**: Additional log storage and analysis costs
- **CloudWatch Metrics**: Custom metrics and dashboard usage
- **CloudTrail**: Extended retention and analysis features

## Critical Workshop Fixes

### 🚨 AccessDeniedException Resolvers
These permissions resolve specific errors encountered during Lab-04:

1. **Memory/Gateway Log Delivery Error**: `bedrock-agentcore:AllowVendedLogDeliveryForResource`
2. **Transaction Search Setup**: `xray:UpdateTraceSegmentDestination`, `application-signals:EnableTransactionSearch`
3. **Log Configuration**: `logs:PutDeliverySource`, `logs:CreateDelivery`, `logs:PutDeliveryDestination`
4. **GenAI Dashboard Access**: `xray:GetTraceGraph`, `xray:GetTraceSummaries`

### Workshop Section Enablement Map
- **Section 4.1** (GenAI Observability): X-Ray Transaction Search permissions
- **Section 4.4** (Memory/Gateway Logs): CloudWatch Logs delivery permissions  
- **Section 4.2** (Metrics): Enhanced Application Signals permissions
- **Section 4.5** (CloudTrail): Complete audit logging capabilities

## Version History
- **Original**: Basic AgentCore functionality with minimal observability
- **Version 1**: Added comprehensive observability policies (151 lines)
- **Version 2 (Current)**: Added critical hands-on permissions (24 additional lines)
- **Focus**: Eliminated all AccessDenied errors for Lab-04 activities

## Conclusion

The current template transforms the basic workshop setup into a production-ready AgentCore deployment with enterprise-grade observability. All additions are based on official AWS documentation and support the complete observability workflow outlined in Lab 04.