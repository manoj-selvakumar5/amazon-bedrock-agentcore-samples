#!/usr/bin/env python3
"""
Validation Helpers for SRE Agent Workshop
Functions to validate workshop progress and success criteria.
"""

import json
import time
import logging
import requests
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class WorkshopValidator:
    """Main validation class for workshop progress."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.region = config.get('aws', {}).get('region', 'us-east-1')
        
    def validate_environment_setup(self) -> Dict[str, bool]:
        """Validate basic environment setup."""
        results = {}
        
        # Check Python version
        results['python_version'] = self._check_python_version()
        
        # Check required packages
        results['required_packages'] = self._check_required_packages()
        
        # Check AWS credentials
        results['aws_credentials'] = self._check_aws_credentials()
        
        # Check AWS permissions
        results['aws_permissions'] = self._check_aws_permissions()
        
        # Check SSL certificates (if specified)
        results['ssl_certificates'] = self._check_ssl_certificates()
        
        return results
    
    def validate_backend_services(self, backend_urls: List[str]) -> Dict[str, bool]:
        """Validate backend services are running and accessible."""
        results = {}
        
        for url in backend_urls:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                results[url] = response.status_code == 200
                logger.info(f"Backend service {url}: {'✓' if results[url] else '✗'}")
            except Exception as e:
                results[url] = False
                logger.error(f"Backend service {url} failed: {e}")
        
        return results
    
    def validate_cognito_setup(self, user_pool_id: str, client_id: str) -> Dict[str, bool]:
        """Validate Cognito User Pool configuration."""
        results = {}
        cognito = boto3.client('cognito-idp', region_name=self.region)
        
        try:
            # Check User Pool exists
            pool_response = cognito.describe_user_pool(UserPoolId=user_pool_id)
            results['user_pool_exists'] = True
            logger.info(f"✓ User Pool {user_pool_id} exists")
            
            # Check App Client exists
            client_response = cognito.describe_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client_id
            )
            results['app_client_exists'] = True
            logger.info(f"✓ App Client {client_id} exists")
            
            # Check OAuth configuration
            client_config = client_response['UserPoolClient']
            has_oauth = 'client_credentials' in client_config.get('AllowedOAuthFlows', [])
            results['oauth_configured'] = has_oauth
            logger.info(f"{'✓' if has_oauth else '✗'} OAuth client_credentials flow configured")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                results['user_pool_exists'] = False
                results['app_client_exists'] = False
                results['oauth_configured'] = False
                logger.error(f"✗ Cognito resources not found: {e}")
            else:
                raise
        
        return results
    
    def validate_gateway_setup(self, gateway_id: str) -> Dict[str, bool]:
        """Validate AgentCore Gateway configuration."""
        results = {}
        gateway_client = boto3.client('bedrock-agentcore-control', region_name=self.region)
        
        try:
            # Check Gateway exists and is ready
            gateway_response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            gateway_status = gateway_response['gateway']['status']
            results['gateway_exists'] = True
            results['gateway_ready'] = gateway_status == 'READY'
            
            logger.info(f"✓ Gateway {gateway_id} exists")
            logger.info(f"{'✓' if results['gateway_ready'] else '✗'} Gateway status: {gateway_status}")
            
            # Check Gateway targets
            targets_response = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id)
            targets = targets_response.get('targets', [])
            results['has_targets'] = len(targets) > 0
            results['targets_ready'] = all(t.get('status') == 'READY' for t in targets)
            
            logger.info(f"{'✓' if results['has_targets'] else '✗'} Gateway has {len(targets)} targets")
            logger.info(f"{'✓' if results['targets_ready'] else '✗'} All targets ready")
            
        except ClientError as e:
            results['gateway_exists'] = False
            results['gateway_ready'] = False
            results['has_targets'] = False
            results['targets_ready'] = False
            logger.error(f"✗ Gateway validation failed: {e}")
        
        return results
    
    def validate_mcp_tools_access(self, gateway_url: str, access_token: str) -> Dict[str, bool]:
        """Validate MCP tools are accessible through gateway."""
        results = {}
        
        try:
            # Test ListTools endpoint
            headers = {'Authorization': f'Bearer {access_token}'}
            
            list_tools_response = requests.post(
                f"{gateway_url}/mcp/v1/tools/list",
                headers=headers,
                json={},
                timeout=10
            )
            
            results['list_tools_accessible'] = list_tools_response.status_code == 200
            
            if results['list_tools_accessible']:
                tools_data = list_tools_response.json()
                tools = tools_data.get('tools', [])
                results['tools_count'] = len(tools)
                results['has_k8s_tools'] = any('k8s' in tool.get('name', '').lower() for tool in tools)
                results['has_logs_tools'] = any('log' in tool.get('name', '').lower() for tool in tools)
                results['has_metrics_tools'] = any('metric' in tool.get('name', '').lower() for tool in tools)
                results['has_runbook_tools'] = any('runbook' in tool.get('name', '').lower() for tool in tools)
                
                logger.info(f"✓ ListTools accessible, found {results['tools_count']} tools")
                logger.info(f"{'✓' if results['has_k8s_tools'] else '✗'} Kubernetes tools available")
                logger.info(f"{'✓' if results['has_logs_tools'] else '✗'} Logs tools available")
                logger.info(f"{'✓' if results['has_metrics_tools'] else '✗'} Metrics tools available")  
                logger.info(f"{'✓' if results['has_runbook_tools'] else '✗'} Runbook tools available")
                
                # Test invoking a simple tool
                if tools:
                    test_tool = tools[0]
                    invoke_response = requests.post(
                        f"{gateway_url}/mcp/v1/tools/call",
                        headers=headers,
                        json={
                            "name": test_tool['name'],
                            "arguments": {}
                        },
                        timeout=15
                    )
                    results['tool_invocation_works'] = invoke_response.status_code == 200
                    logger.info(f"{'✓' if results['tool_invocation_works'] else '✗'} Tool invocation test")
                
            else:
                logger.error(f"✗ ListTools failed: {list_tools_response.status_code}")
                results['tools_count'] = 0
                results['has_k8s_tools'] = False
                results['has_logs_tools'] = False
                results['has_metrics_tools'] = False
                results['has_runbook_tools'] = False
                results['tool_invocation_works'] = False
                
        except Exception as e:
            logger.error(f"✗ MCP tools validation failed: {e}")
            results = {
                'list_tools_accessible': False,
                'tools_count': 0,
                'has_k8s_tools': False,
                'has_logs_tools': False,
                'has_metrics_tools': False,
                'has_runbook_tools': False,
                'tool_invocation_works': False
            }
        
        return results
    
    def validate_agent_functionality(self, test_prompt: str = None) -> Dict[str, bool]:
        """Validate SRE agent functionality with a test investigation."""
        results = {}
        
        if not test_prompt:
            test_prompt = "Check the health of the payment service pods"
        
        try:
            # Try to run the SRE agent with a simple prompt
            import sys
            import subprocess
            
            # Get the root directory (where sre-agent CLI should be available)
            workshop_root = Path(__file__).parent.parent.parent.parent
            
            # Try to run sre-agent CLI
            result = subprocess.run([
                sys.executable, "-m", "sre_agent.cli",
                "--prompt", test_prompt,
                "--provider", "bedrock"
            ], 
            cwd=str(workshop_root),
            capture_output=True, 
            text=True, 
            timeout=60
            )
            
            results['agent_executable'] = result.returncode == 0
            results['agent_responds'] = len(result.stdout.strip()) > 0
            
            if results['agent_executable']:
                # Check if response contains expected investigation elements
                output = result.stdout.lower()
                results['uses_multiple_agents'] = 'kubernetes' in output or 'logs' in output
                results['provides_analysis'] = any(word in output for word in ['analysis', 'investigation', 'findings'])
                results['includes_recommendations'] = any(word in output for word in ['recommend', 'suggest', 'next steps'])
                
                logger.info("✓ Agent executable and responsive")
                logger.info(f"{'✓' if results['uses_multiple_agents'] else '✗'} Uses multiple agents")
                logger.info(f"{'✓' if results['provides_analysis'] else '✗'} Provides analysis")
                logger.info(f"{'✓' if results['includes_recommendations'] else '✗'} Includes recommendations")
            else:
                logger.error(f"✗ Agent execution failed: {result.stderr}")
                results['uses_multiple_agents'] = False
                results['provides_analysis'] = False
                results['includes_recommendations'] = False
                
        except Exception as e:
            logger.error(f"✗ Agent functionality validation failed: {e}")
            results = {
                'agent_executable': False,
                'agent_responds': False,
                'uses_multiple_agents': False,
                'provides_analysis': False,
                'includes_recommendations': False
            }
        
        return results
    
    def validate_memory_integration(self, user_id: str = "Alice") -> Dict[str, bool]:
        """Validate AgentCore Memory integration."""
        results = {}
        
        try:
            # Check if memory client can be imported and initialized
            from sre_agent.memory.client import SREMemoryClient
            
            memory_client = SREMemoryClient()
            results['memory_client_available'] = True
            logger.info("✓ Memory client available")
            
            # Try to list memories
            try:
                memories = memory_client.list_memories()
                results['memory_service_accessible'] = True
                results['has_user_memories'] = any(m.get('actorId') == user_id for m in memories)
                logger.info("✓ Memory service accessible")
                logger.info(f"{'✓' if results['has_user_memories'] else '✗'} User memories found for {user_id}")
            except Exception as e:
                results['memory_service_accessible'] = False
                results['has_user_memories'] = False
                logger.error(f"✗ Memory service access failed: {e}")
                
        except ImportError as e:
            results['memory_client_available'] = False
            results['memory_service_accessible'] = False
            results['has_user_memories'] = False
            logger.error(f"✗ Memory client import failed: {e}")
        
        return results
    
    def validate_runtime_deployment(self, agent_runtime_arn: str) -> Dict[str, bool]:
        """Validate AgentCore Runtime deployment."""
        results = {}
        runtime_client = boto3.client('bedrock-agentcore', region_name=self.region)
        control_client = boto3.client('bedrock-agentcore-control', region_name=self.region)
        
        try:
            # Extract runtime ID from ARN
            runtime_id = agent_runtime_arn.split('/')[-1]
            
            # Check runtime status
            runtime_response = control_client.get_agent_runtime(agentRuntimeId=runtime_id)
            runtime_status = runtime_response['agentRuntime']['status']
            
            results['runtime_exists'] = True
            results['runtime_ready'] = runtime_status == 'READY'
            logger.info(f"✓ Runtime {runtime_id} exists")
            logger.info(f"{'✓' if results['runtime_ready'] else '✗'} Runtime status: {runtime_status}")
            
            # Test runtime invocation
            if results['runtime_ready']:
                test_payload = {"prompt": "Hello, are you working?"}
                invoke_response = runtime_client.invoke_agent_runtime(
                    agentRuntimeArn=agent_runtime_arn,
                    qualifier="DEFAULT",
                    payload=json.dumps(test_payload)
                )
                
                # Check if we got a response
                results['runtime_invocable'] = True
                response_content = b''.join(invoke_response['response'])
                results['runtime_responds'] = len(response_content) > 0
                
                logger.info("✓ Runtime invocable")
                logger.info(f"{'✓' if results['runtime_responds'] else '✗'} Runtime responds to test")
            else:
                results['runtime_invocable'] = False
                results['runtime_responds'] = False
                
        except ClientError as e:
            results['runtime_exists'] = False
            results['runtime_ready'] = False  
            results['runtime_invocable'] = False
            results['runtime_responds'] = False
            logger.error(f"✗ Runtime validation failed: {e}")
        
        return results
    
    def _check_python_version(self) -> bool:
        """Check if Python version is 3.12+."""
        import sys
        version_info = sys.version_info
        is_valid = version_info.major == 3 and version_info.minor >= 12
        logger.info(f"{'✓' if is_valid else '✗'} Python {version_info.major}.{version_info.minor}")
        return is_valid
    
    def _check_required_packages(self) -> bool:
        """Check if required packages are installed."""
        required_packages = [
            'boto3', 'botocore', 'requests', 'pyyaml', 
            'langgraph', 'langchain_core', 'strands',
            'bedrock_agentcore'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"✗ Missing packages: {', '.join(missing_packages)}")
            return False
        
        logger.info("✓ All required packages installed")
        return True
    
    def _check_aws_credentials(self) -> bool:
        """Check if AWS credentials are configured."""
        try:
            sts = boto3.client('sts')
            response = sts.get_caller_identity()
            logger.info(f"✓ AWS credentials configured for account {response['Account']}")
            return True
        except Exception as e:
            logger.error(f"✗ AWS credentials not configured: {e}")
            return False
    
    def _check_aws_permissions(self) -> bool:
        """Check if required AWS permissions are available."""
        permissions_to_check = [
            ('sts', 'get_caller_identity'),
            ('bedrock-agentcore-control', 'list_gateways'),
            ('cognito-idp', 'list_user_pools'),
            ('iam', 'list_roles'),
        ]
        
        failed_permissions = []
        
        for service, operation in permissions_to_check:
            try:
                client = boto3.client(service, region_name=self.region)
                
                # Try to call each operation
                if operation == 'get_caller_identity':
                    client.get_caller_identity()
                elif operation == 'list_gateways':
                    client.list_gateways()
                elif operation == 'list_user_pools':
                    client.list_user_pools(MaxResults=1)
                elif operation == 'list_roles':
                    client.list_roles(MaxItems=1)
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                    failed_permissions.append(f"{service}:{operation}")
                # Other errors might be due to resource states, not permissions
        
        if failed_permissions:
            logger.error(f"✗ Missing permissions: {', '.join(failed_permissions)}")
            return False
        
        logger.info("✓ Required AWS permissions available")
        return True
    
    def _check_ssl_certificates(self) -> bool:
        """Check SSL certificates if specified in config."""
        ssl_config = self.config.get('ssl', {})
        cert_path = ssl_config.get('cert_path')
        key_path = ssl_config.get('key_path')
        
        if not cert_path or not key_path:
            logger.info("ℹ SSL certificates not specified in config")
            return True  # Not required
        
        try:
            cert_file = Path(cert_path)
            key_file = Path(key_path)
            
            if not cert_file.exists():
                logger.error(f"✗ SSL certificate not found: {cert_path}")
                return False
            
            if not key_file.exists():
                logger.error(f"✗ SSL private key not found: {key_path}")
                return False
            
            logger.info("✓ SSL certificates found")
            return True
            
        except Exception as e:
            logger.error(f"✗ SSL certificate check failed: {e}")
            return False


def print_validation_summary(validation_results: Dict[str, Dict[str, bool]]):
    """Print a formatted summary of validation results."""
    print("\n" + "="*60)
    print("WORKSHOP VALIDATION SUMMARY")
    print("="*60)
    
    total_checks = 0
    passed_checks = 0
    
    for section, results in validation_results.items():
        print(f"\n{section.upper().replace('_', ' ')}:")
        print("-" * 40)
        
        for check, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {check.replace('_', ' ').title():<30} {status}")
            total_checks += 1
            if passed:
                passed_checks += 1
    
    print("\n" + "="*60)
    success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
    print(f"OVERALL: {passed_checks}/{total_checks} checks passed ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🎉 All validation checks passed! Ready to proceed.")
    elif success_rate >= 80:
        print("⚠️  Most checks passed. Review failed items before proceeding.")
    else:
        print("❌ Multiple validation failures. Please address issues before continuing.")
    
    print("="*60)