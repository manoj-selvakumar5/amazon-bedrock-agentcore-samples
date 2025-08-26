"""
Observability utilities for AgentCore components
Shared utilities for Labs 7 and 8 to avoid code repetition
"""

import boto3
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from scripts.utils import get_ssm_parameter, put_ssm_parameter


class AgentCoreObservability:
    """Centralized observability management - extends Lab 7's AgentCoreMetricsClient"""
    
    def __init__(self):
        self.session = boto3.Session()
        self.region = self.session.region_name
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.logs_client = boto3.client('logs', region_name=self.region)
        self.sns_client = boto3.client('sns', region_name=self.region)
        
        # Load components from previous labs
        self.components = self._load_components()
    
    def _load_components(self) -> Dict[str, str]:
        """Load all AgentCore components from previous labs"""
        components = {}
        
        try:
            components['memory_id'] = get_ssm_parameter("/app/customersupport/agentcore/memory_id")
        except:
            pass
            
        try:
            components['gateway_arn'] = get_ssm_parameter("/app/customersupport/agentcore/gateway_arn")
            components['gateway_id'] = components['gateway_arn'].split('/')[-1]
        except:
            pass
            
        try:
            components['runtime_arn'] = get_ssm_parameter("/app/customersupport/agentcore/runtime_arn")
            components['runtime_name'] = components['runtime_arn'].split('/')[-1].split('-')[0]
        except:
            pass
            
        return components
    
    def create_log_groups_for_memory(self) -> bool:
        """Create log groups for Memory observability"""
        if 'memory_id' not in self.components:
            return False
        
        memory_id = self.components['memory_id']
        log_group_base = f"/aws/vendedlogs/bedrock-agentcore/memory"
        
        log_groups = [
            f"{log_group_base}/APPLICATION_LOGS/{memory_id}",
            f"{log_group_base}/extraction/{memory_id}",
            f"{log_group_base}/consolidation/{memory_id}"
        ]
        
        success = True
        for log_group in log_groups:
            try:
                self.logs_client.create_log_group(logGroupName=log_group)
                self.logs_client.put_retention_policy(
                    logGroupName=log_group,
                    retentionInDays=7
                )
            except self.logs_client.exceptions.ResourceAlreadyExistsException:
                pass  # Already exists is fine
            except Exception as e:
                print(f"Error creating {log_group}: {str(e)}")
                success = False
        
        return success
    
    def create_sns_topic(self, topic_name: str = "CustomerSupportAgent-Alerts") -> Optional[str]:
        """Create SNS topic for alarms"""
        try:
            response = self.sns_client.create_topic(Name=topic_name)
            topic_arn = response['TopicArn']
            put_ssm_parameter("/app/customersupport/observability/sns_topic_arn", topic_arn)
            return topic_arn
        except Exception as e:
            print(f"Error creating SNS topic: {str(e)}")
            return None


class StructuredLogger:
    """Enhanced JSON logger with correlation support"""
    
    def __init__(self, component_name: str, session_id: str = None):
        self.component = component_name
        self.session_id = session_id or str(uuid.uuid4())
        self.logger = logging.getLogger(f"{component_name}-{self.session_id}")
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(self.JsonFormatter(self.component, self.session_id))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    class JsonFormatter(logging.Formatter):
        def __init__(self, component: str, session_id: str):
            self.component = component
            self.session_id = session_id
            super().__init__()
        
        def format(self, record):
            log_obj = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "component": self.component,
                "session_id": self.session_id,
                "message": record.getMessage(),
            }
            
            if hasattr(record, 'extra_fields'):
                log_obj.update(record.extra_fields)
            
            return json.dumps(log_obj)
    
    def log(self, level: str, message: str, **kwargs):
        """Log with extra structured fields"""
        extra = {'extra_fields': kwargs} if kwargs else {}
        getattr(self.logger, level)(message, extra=extra)


class StandardAlarms:
    """Standard alarm configurations for AgentCore"""
    
    @staticmethod
    def get_runtime_alarms(runtime_name: str, topic_arn: str) -> List[Dict]:
        """Get standard Runtime alarms"""
        return [
            {
                'AlarmName': f'CustomerSupport-HighErrorRate-{runtime_name}',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'SystemErrors',
                'Namespace': 'AWS/Bedrock/AgentCore/Runtime',
                'Period': 300,
                'Statistic': 'Sum',
                'Threshold': 5.0,
                'ActionsEnabled': True,
                'AlarmActions': [topic_arn],
                'AlarmDescription': 'Alert when error rate exceeds 5 errors in 5 minutes',
                'Dimensions': [{'Name': 'RuntimeName', 'Value': runtime_name}]
            },
            {
                'AlarmName': f'CustomerSupport-HighLatency-{runtime_name}',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'Latency',
                'Namespace': 'AWS/Bedrock/AgentCore/Runtime',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 3000.0,
                'ActionsEnabled': True,
                'AlarmActions': [topic_arn],
                'AlarmDescription': 'Alert when average latency exceeds 3 seconds',
                'Dimensions': [{'Name': 'RuntimeName', 'Value': runtime_name}]
            }
        ]


def simulate_customer_interaction(session_id: str = None) -> str:
    """Simulate customer interaction across all components"""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Use the same customer queries from Lab 1
    steps = [
        ("Runtime", "Customer asks about ThinkPad return policy", {"query_type": "return_policy"}),
        ("Memory", "Retrieved previous ThinkPad conversations", {"records": 2}),
        ("Gateway", "Invoked get_return_policy tool", {"tool": "get_return_policy", "duration_ms": 145}),
        ("Memory", "Stored new conversation", {"memory_type": "conversation"}),
        ("Runtime", "Response sent to customer", {"tokens": 156})
    ]
    
    for component, message, attrs in steps:
        logger = StructuredLogger(component, session_id)
        logger.log("info", message, **attrs)
    
    return session_id