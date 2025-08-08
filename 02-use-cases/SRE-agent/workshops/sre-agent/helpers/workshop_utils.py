#!/usr/bin/env python3
"""
Workshop Utilities for SRE Agent Workshop
Common utilities for AWS resource creation, configuration, and cleanup.
"""

import boto3
import json
import time
import logging
import subprocess
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Workshop configuration
WORKSHOP_DIR = Path(__file__).parent.parent
CONFIG_FILE = WORKSHOP_DIR / "configs" / "workshop_config.yaml"


def load_workshop_config() -> Dict[str, Any]:
    """Load workshop configuration from YAML file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found: {CONFIG_FILE}. Using defaults.")
        return {
            "aws": {"region": "us-east-1"},
            "names": {
                "prefix": "sre-workshop",
                "cognito_pool": "sre-agent-pool",
                "gateway": "sre-gateway",
                "runtime": "sre-runtime"
            }
        }


def get_aws_account_id() -> str:
    """Get current AWS account ID."""
    try:
        sts_client = boto3.client('sts')
        return sts_client.get_caller_identity()['Account']
    except Exception as e:
        logger.error(f"Failed to get AWS account ID: {e}")
        raise


def create_cognito_user_pool(pool_name: str, region: str = 'us-east-1') -> Tuple[str, str, str]:
    """
    Create Cognito User Pool with required configuration for AgentCore Gateway.
    
    Returns:
        Tuple of (user_pool_id, client_id, client_secret)
    """
    cognito = boto3.client('cognito-idp', region_name=region)
    
    try:
        # Create User Pool
        pool_response = cognito.create_user_pool(
            PoolName=pool_name,
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': False,
                    'RequireLowercase': False,
                    'RequireNumbers': False,
                    'RequireSymbols': False,
                }
            },
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True,
                }
            ]
        )
        user_pool_id = pool_response['UserPool']['Id']
        logger.info(f"Created User Pool: {user_pool_id}")
        
        # Create Resource Server
        resource_server_response = cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier='sre-gateway',
            Name='SRE Gateway Resource Server',
            Scopes=[
                {'ScopeName': 'read', 'ScopeDescription': 'Read access to gateway'},
                {'ScopeName': 'write', 'ScopeDescription': 'Write access to gateway'}
            ]
        )
        logger.info("Created Resource Server")
        
        # Create App Client
        client_response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=f'{pool_name}-client',
            GenerateSecret=True,
            AllowedOAuthFlows=['client_credentials'],
            AllowedOAuthScopes=['sre-gateway/read', 'sre-gateway/write'],
            AllowedOAuthFlowsUserPoolClient=True,
            SupportedIdentityProviders=['COGNITO']
        )
        
        client_id = client_response['UserPoolClient']['ClientId']
        client_secret = client_response['UserPoolClient']['ClientSecret']
        logger.info(f"Created App Client: {client_id}")
        
        # Create User Pool Domain (required for token endpoint)
        domain_name = f"{pool_name}-{int(time.time())}"
        try:
            cognito.create_user_pool_domain(
                Domain=domain_name,
                UserPoolId=user_pool_id
            )
            logger.info(f"Created User Pool Domain: {domain_name}")
        except ClientError as e:
            if 'InvalidParameterException' in str(e):
                logger.warning(f"Domain already exists or invalid: {domain_name}")
            else:
                raise
        
        return user_pool_id, client_id, client_secret
        
    except ClientError as e:
        if 'UsernameExistsException' in str(e):
            logger.warning(f"User pool {pool_name} already exists")
            # Return existing pool info if needed
            raise
        else:
            logger.error(f"Failed to create Cognito resources: {e}")
            raise


def get_cognito_token(user_pool_id: str, client_id: str, client_secret: str, region: str = 'us-east-1') -> str:
    """Get OAuth token from Cognito for API authentication."""
    import base64
    import requests
    
    # Get token endpoint from user pool
    token_endpoint = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/oauth2/token"
    
    # Prepare credentials
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'client_credentials',
        'scope': 'sre-gateway/read sre-gateway/write'
    }
    
    response = requests.post(token_endpoint, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get token: {response.text}")


def create_iam_role(role_name: str, service_principals: List[str], policies: List[str]) -> str:
    """
    Create IAM role with specified service principals and policies.
    
    Args:
        role_name: Name of the IAM role
        service_principals: List of service principals (e.g., ['lambda.amazonaws.com'])
        policies: List of policy ARNs to attach
        
    Returns:
        Role ARN
    """
    iam = boto3.client('iam')
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": service_principals
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Create role
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role created by SRE Agent Workshop"
        )
        role_arn = role_response['Role']['Arn']
        logger.info(f"Created IAM role: {role_arn}")
        
        # Attach policies
        for policy_arn in policies:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            logger.info(f"Attached policy {policy_arn} to {role_name}")
        
        # Wait for role to be available
        time.sleep(10)
        
        return role_arn
        
    except ClientError as e:
        if 'EntityAlreadyExists' in str(e):
            logger.warning(f"Role {role_name} already exists")
            # Get existing role ARN
            role_response = iam.get_role(RoleName=role_name)
            return role_response['Role']['Arn']
        else:
            logger.error(f"Failed to create IAM role: {e}")
            raise


def create_lambda_function(function_name: str, zip_file_path: str, role_arn: str, region: str = 'us-east-1') -> str:
    """
    Create Lambda function from ZIP file.
    
    Returns:
        Function ARN
    """
    lambda_client = boto3.client('lambda', region_name=region)
    
    with open(zip_file_path, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.12',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='Demo function for SRE Agent Workshop',
            Timeout=30,
            MemorySize=128
        )
        
        function_arn = response['FunctionArn']
        logger.info(f"Created Lambda function: {function_arn}")
        return function_arn
        
    except ClientError as e:
        if 'ResourceConflictException' in str(e):
            logger.warning(f"Lambda function {function_name} already exists")
            # Get existing function ARN
            response = lambda_client.get_function(FunctionName=function_name)
            return response['Configuration']['FunctionArn']
        else:
            logger.error(f"Failed to create Lambda function: {e}")
            raise


def wait_for_resource_ready(check_function, max_wait_time: int = 300, check_interval: int = 10) -> bool:
    """
    Generic function to wait for AWS resource to be ready.
    
    Args:
        check_function: Function that returns True when resource is ready
        max_wait_time: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        True if resource became ready, False if timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            if check_function():
                return True
        except Exception as e:
            logger.debug(f"Resource not ready yet: {e}")
        
        logger.info(f"Waiting for resource... ({int(time.time() - start_time)}s elapsed)")
        time.sleep(check_interval)
    
    logger.error(f"Resource not ready after {max_wait_time}s")
    return False


def cleanup_cognito_resources(user_pool_id: str, region: str = 'us-east-1'):
    """Clean up Cognito User Pool and related resources."""
    cognito = boto3.client('cognito-idp', region_name=region)
    
    try:
        # Get all clients and delete them
        clients_response = cognito.list_user_pool_clients(UserPoolId=user_pool_id)
        for client in clients_response.get('UserPoolClients', []):
            cognito.delete_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client['ClientId']
            )
            logger.info(f"Deleted User Pool Client: {client['ClientId']}")
        
        # Delete resource servers
        resource_servers = cognito.list_resource_servers(UserPoolId=user_pool_id)
        for server in resource_servers.get('ResourceServers', []):
            cognito.delete_resource_server(
                UserPoolId=user_pool_id,
                Identifier=server['Identifier']
            )
            logger.info(f"Deleted Resource Server: {server['Identifier']}")
        
        # Delete User Pool Domain if exists
        try:
            domain_response = cognito.describe_user_pool_domain(Domain=f"sre-gateway-{user_pool_id}")
            if domain_response:
                cognito.delete_user_pool_domain(Domain=f"sre-gateway-{user_pool_id}")
                logger.info("Deleted User Pool Domain")
        except ClientError:
            pass  # Domain doesn't exist
        
        # Delete User Pool
        cognito.delete_user_pool(UserPoolId=user_pool_id)
        logger.info(f"Deleted User Pool: {user_pool_id}")
        
    except ClientError as e:
        logger.error(f"Failed to cleanup Cognito resources: {e}")


def cleanup_iam_role(role_name: str):
    """Clean up IAM role and attached policies."""
    iam = boto3.client('iam')
    
    try:
        # Detach all policies
        policies_response = iam.list_attached_role_policies(RoleName=role_name)
        for policy in policies_response.get('AttachedPolicies', []):
            iam.detach_role_policy(
                RoleName=role_name,
                PolicyArn=policy['PolicyArn']
            )
            logger.info(f"Detached policy {policy['PolicyArn']} from {role_name}")
        
        # Delete role
        iam.delete_role(RoleName=role_name)
        logger.info(f"Deleted IAM role: {role_name}")
        
    except ClientError as e:
        if 'NoSuchEntity' not in str(e):
            logger.error(f"Failed to cleanup IAM role: {e}")


def cleanup_lambda_function(function_name: str, region: str = 'us-east-1'):
    """Clean up Lambda function."""
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        lambda_client.delete_function(FunctionName=function_name)
        logger.info(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
        if 'ResourceNotFound' not in str(e):
            logger.error(f"Failed to cleanup Lambda function: {e}")


def get_private_ip() -> str:
    """Get EC2 instance private IP address."""
    try:
        import requests
        
        # Get instance metadata token
        token_response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        )
        
        if token_response.status_code == 200:
            token = token_response.text
            
            # Get private IP
            ip_response = requests.get(
                "http://169.254.169.254/latest/meta-data/local-ipv4",
                headers={"X-aws-ec2-metadata-token": token},
                timeout=2
            )
            
            if ip_response.status_code == 200:
                return ip_response.text
    except Exception as e:
        logger.warning(f"Could not get EC2 private IP: {e}")
    
    return "127.0.0.1"  # Fallback for local development


def validate_ssl_certificates(cert_path: str, key_path: str) -> bool:
    """Validate SSL certificate files exist and are readable."""
    try:
        if not os.path.exists(cert_path):
            logger.error(f"SSL certificate not found: {cert_path}")
            return False
        
        if not os.path.exists(key_path):
            logger.error(f"SSL private key not found: {key_path}")
            return False
        
        # Try to read files
        with open(cert_path, 'r') as f:
            cert_content = f.read()
        
        with open(key_path, 'r') as f:
            key_content = f.read()
        
        if not cert_content or not key_content:
            logger.error("SSL certificate or key files are empty")
            return False
        
        logger.info("SSL certificates validated successfully")
        return True
        
    except Exception as e:
        logger.error(f"SSL certificate validation failed: {e}")
        return False


def run_backend_servers(host: str = None, ssl_cert: str = None, ssl_key: str = None) -> subprocess.Popen:
    """
    Start demo backend servers for the workshop.
    
    Returns:
        Popen object for the running process
    """
    workshop_root = Path(__file__).parent.parent.parent.parent
    backend_dir = workshop_root / "backend"
    script_path = backend_dir / "scripts" / "start_demo_backend.sh"
    
    if not script_path.exists():
        raise FileNotFoundError(f"Backend script not found: {script_path}")
    
    cmd = [str(script_path)]
    
    if host:
        cmd.extend(["--host", host])
    
    if ssl_cert and ssl_key:
        cmd.extend(["--ssl-certfile", ssl_cert, "--ssl-keyfile", ssl_key])
    
    logger.info(f"Starting backend servers: {' '.join(cmd)}")
    
    return subprocess.Popen(
        cmd,
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )