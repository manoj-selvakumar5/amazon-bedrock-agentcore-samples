#!/usr/bin/env python3
"""
SRE Scenarios for Workshop
Pre-built incident scenarios for testing the SRE Agent system.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SREScenario:
    """Represents an SRE incident scenario for testing."""
    
    id: str
    title: str
    description: str
    severity: Severity
    affected_services: List[str]
    symptoms: List[str]
    expected_investigation_steps: List[str]
    expected_tools_used: List[str]
    learning_objectives: List[str]
    estimated_time: str
    difficulty: str  # beginner, intermediate, advanced


class SREScenarios:
    """Collection of pre-built SRE scenarios for the workshop."""
    
    @staticmethod
    def get_all_scenarios() -> List[SREScenario]:
        """Get all available scenarios."""
        return [
            SREScenarios.api_response_degradation(),
            SREScenarios.pod_crash_loop(),
            SREScenarios.database_connection_errors(),
            SREScenarios.memory_leak_investigation(),
            SREScenarios.service_mesh_failure(),
            SREScenarios.disk_space_alert(),
            SREScenarios.load_balancer_issues(),
            SREScenarios.certificate_expiration(),
        ]
    
    @staticmethod
    def get_scenario_by_id(scenario_id: str) -> SREScenario:
        """Get scenario by ID."""
        scenarios = SREScenarios.get_all_scenarios()
        for scenario in scenarios:
            if scenario.id == scenario_id:
                return scenario
        raise ValueError(f"Scenario not found: {scenario_id}")
    
    @staticmethod
    def get_scenarios_by_difficulty(difficulty: str) -> List[SREScenario]:
        """Get scenarios filtered by difficulty level."""
        scenarios = SREScenarios.get_all_scenarios()
        return [s for s in scenarios if s.difficulty == difficulty]
    
    @staticmethod
    def api_response_degradation() -> SREScenario:
        """High API response times scenario."""
        return SREScenario(
            id="api-response-degradation",
            title="API Response Time Degradation",
            description="API response times have increased by 3x in the last hour across multiple microservices",
            severity=Severity.HIGH,
            affected_services=["payment-service", "user-service", "notification-service"],
            symptoms=[
                "Average response time increased from 200ms to 600ms",
                "Error rate increased from 0.1% to 2.3%",
                "User complaints about slow checkout process",
                "Database connection pool showing high utilization"
            ],
            expected_investigation_steps=[
                "Check current performance metrics across all services",
                "Analyze error logs for the affected time period",
                "Examine database connection patterns",
                "Review recent deployments and configuration changes",
                "Check resource utilization (CPU, memory, network)"
            ],
            expected_tools_used=[
                "get_performance_metrics",
                "get_error_rates", 
                "search_logs",
                "get_resource_metrics",
                "analyze_trends"
            ],
            learning_objectives=[
                "Learn to correlate metrics across multiple services",
                "Practice identifying bottlenecks in distributed systems",
                "Understand performance monitoring best practices"
            ],
            estimated_time="15-20 minutes",
            difficulty="intermediate"
        )
    
    @staticmethod
    def pod_crash_loop() -> SREScenario:
        """Pod crash looping scenario."""
        return SREScenario(
            id="pod-crash-loop",
            title="Payment Service Pods Crash Looping",
            description="Payment service pods are repeatedly crashing and restarting, causing service unavailability",
            severity=Severity.CRITICAL,
            affected_services=["payment-service"],
            symptoms=[
                "Pods stuck in CrashLoopBackOff state",
                "Payment processing completely unavailable",
                "High restart count on payment-service pods",
                "OOM (Out of Memory) errors in container logs"
            ],
            expected_investigation_steps=[
                "Check pod status and recent events",
                "Examine container logs for error messages",
                "Review resource requests and limits",
                "Check deployment configuration",
                "Analyze memory usage patterns"
            ],
            expected_tools_used=[
                "get_pod_status",
                "get_cluster_events",
                "search_logs",
                "get_resource_usage",
                "get_deployment_status"
            ],
            learning_objectives=[
                "Understand Kubernetes pod lifecycle and failure modes",
                "Learn to diagnose resource-related pod failures",
                "Practice log analysis for container debugging"
            ],
            estimated_time="10-15 minutes",
            difficulty="beginner"
        )
    
    @staticmethod
    def database_connection_errors() -> SREScenario:
        """Database connection pool exhaustion scenario."""
        return SREScenario(
            id="database-connection-errors",
            title="Database Connection Pool Exhaustion",
            description="Applications are failing to connect to the database due to connection pool exhaustion",
            severity=Severity.HIGH,
            affected_services=["user-service", "order-service", "inventory-service"],
            symptoms=[
                "Connection timeout errors in application logs",
                "Database connection pool at 100% utilization",
                "Intermittent 503 Service Unavailable errors",
                "Slow query performance reported by users"
            ],
            expected_investigation_steps=[
                "Check database connection metrics",
                "Analyze application logs for connection errors",
                "Review database performance metrics",
                "Examine connection pool configuration",
                "Look for long-running queries or transactions"
            ],
            expected_tools_used=[
                "search_logs",
                "get_error_logs",
                "get_performance_metrics",
                "analyze_log_patterns",
                "get_troubleshooting_guide"
            ],
            learning_objectives=[
                "Learn to diagnose database connectivity issues",
                "Understand connection pool management",
                "Practice correlating application and database metrics"
            ],
            estimated_time="20-25 minutes",
            difficulty="intermediate"
        )
    
    @staticmethod
    def memory_leak_investigation() -> SREScenario:
        """Memory leak causing service degradation."""
        return SREScenario(
            id="memory-leak-investigation",
            title="Memory Leak Causing Service Degradation",
            description="User service showing steady memory growth over time, leading to periodic OOM kills",
            severity=Severity.MEDIUM,
            affected_services=["user-service"],
            symptoms=[
                "Gradual memory usage increase over several days",
                "Periodic pod restarts due to OOM kills",
                "Slow response times during high memory usage periods",
                "GC pressure warnings in application logs"
            ],
            expected_investigation_steps=[
                "Analyze memory usage trends over time",
                "Check for OOM kill events in container logs",
                "Review garbage collection patterns",
                "Examine heap dump data if available",
                "Look for recent code changes that might cause leaks"
            ],
            expected_tools_used=[
                "get_resource_metrics",
                "analyze_trends",
                "get_cluster_events",
                "search_logs",
                "get_common_resolutions"
            ],
            learning_objectives=[
                "Learn to identify memory leak patterns",
                "Practice long-term trend analysis",
                "Understand JVM memory management in containers"
            ],
            estimated_time="25-30 minutes",
            difficulty="advanced"
        )
    
    @staticmethod
    def service_mesh_failure() -> SREScenario:
        """Service mesh communication breakdown."""
        return SREScenario(
            id="service-mesh-failure",
            title="Service Mesh Communication Breakdown",
            description="Inter-service communication failing due to service mesh configuration issues",
            severity=Severity.HIGH,
            affected_services=["all-services"],
            symptoms=[
                "503 Service Unavailable errors between services",
                "Istio sidecar proxy errors in logs",
                "Circuit breaker activation across multiple services",
                "Distributed tracing showing incomplete traces"
            ],
            expected_investigation_steps=[
                "Check service mesh proxy health",
                "Examine inter-service communication patterns",
                "Review service mesh configuration changes",
                "Analyze network policies and security rules",
                "Check certificate validity for mTLS"
            ],
            expected_tools_used=[
                "get_pod_status",
                "search_logs",
                "get_cluster_events",
                "get_troubleshooting_guide",
                "get_incident_playbook"
            ],
            learning_objectives=[
                "Understand service mesh troubleshooting",
                "Learn to diagnose network connectivity issues",
                "Practice distributed system debugging"
            ],
            estimated_time="30-35 minutes",
            difficulty="advanced"
        )
    
    @staticmethod
    def disk_space_alert() -> SREScenario:
        """Disk space running low on nodes."""
        return SREScenario(
            id="disk-space-alert",
            title="Disk Space Alert on Kubernetes Nodes",
            description="Multiple Kubernetes nodes showing high disk utilization, risking pod evictions",
            severity=Severity.MEDIUM,
            affected_services=["all-services"],
            symptoms=[
                "Disk usage above 85% on several nodes",
                "Pod eviction warnings in cluster events",
                "New pod scheduling failures",
                "Log rotation not keeping up with log volume"
            ],
            expected_investigation_steps=[
                "Check disk usage across all nodes",
                "Identify largest log files and directories",
                "Review log retention policies",
                "Check for filled temporary directories",
                "Examine pod resource usage patterns"
            ],
            expected_tools_used=[
                "get_node_status",
                "get_resource_usage",
                "get_cluster_events",
                "search_runbooks",
                "get_common_resolutions"
            ],
            learning_objectives=[
                "Learn cluster resource management",
                "Practice node-level troubleshooting",
                "Understand pod eviction policies"
            ],
            estimated_time="15-20 minutes",
            difficulty="beginner"
        )
    
    @staticmethod
    def load_balancer_issues() -> SREScenario:
        """Load balancer health check failures."""
        return SREScenario(
            id="load-balancer-issues",
            title="Load Balancer Health Check Failures",
            description="Application Load Balancer removing healthy instances due to failing health checks",
            severity=Severity.HIGH,
            affected_services=["web-frontend", "api-gateway"],
            symptoms=[
                "Instances being marked unhealthy by ALB",
                "Reduced capacity in target groups",
                "Intermittent connection timeouts for users",
                "Health check endpoint responding with errors"
            ],
            expected_investigation_steps=[
                "Check ALB target group health",
                "Examine health check endpoint logs",
                "Review application startup and readiness",
                "Check security group and network ACL rules",
                "Analyze load balancer access logs"
            ],
            expected_tools_used=[
                "get_availability_metrics",
                "search_logs",
                "get_error_logs",
                "get_troubleshooting_guide",
                "analyze_log_patterns"
            ],
            learning_objectives=[
                "Understand load balancer health checking",
                "Learn to diagnose connectivity issues",
                "Practice AWS networking troubleshooting"
            ],
            estimated_time="20-25 minutes",
            difficulty="intermediate"
        )
    
    @staticmethod
    def certificate_expiration() -> SREScenario:
        """SSL certificate expiration causing service disruption."""
        return SREScenario(
            id="certificate-expiration",
            title="SSL Certificate Expiration",
            description="SSL/TLS certificates expired causing HTTPS service disruption",
            severity=Severity.CRITICAL,
            affected_services=["api-gateway", "web-frontend"],
            symptoms=[
                "HTTPS connections failing with certificate errors",
                "Browser showing security warnings",
                "API clients unable to establish secure connections",
                "Certificate validation errors in logs"
            ],
            expected_investigation_steps=[
                "Check certificate expiration dates",
                "Verify certificate chain validity",
                "Review certificate renewal processes",
                "Check certificate storage and distribution",
                "Examine TLS handshake errors in logs"
            ],
            expected_tools_used=[
                "search_logs",
                "get_error_logs",
                "get_incident_playbook",
                "get_escalation_procedures",
                "get_common_resolutions"
            ],
            learning_objectives=[
                "Learn certificate lifecycle management",
                "Practice security incident response",
                "Understand TLS troubleshooting"
            ],
            estimated_time="10-15 minutes",
            difficulty="beginner"
        )


def get_scenario_prompts() -> Dict[str, str]:
    """Get user prompts for each scenario."""
    return {
        "api-response-degradation": "API response times have degraded 3x in the last hour. Users are complaining about slow performance. Please investigate.",
        
        "pod-crash-loop": "The payment service pods are crash looping and payment processing is down. This is critical - please investigate immediately.",
        
        "database-connection-errors": "We're seeing database connection errors across multiple services. Applications can't connect to the database consistently.",
        
        "memory-leak-investigation": "The user service memory usage keeps growing over time and pods are getting OOM killed. Please investigate this potential memory leak.",
        
        "service-mesh-failure": "Services can't communicate with each other. We're seeing 503 errors between all our microservices. The service mesh might be down.",
        
        "disk-space-alert": "We got alerts that disk space is running low on our Kubernetes nodes. Pods might get evicted soon.",
        
        "load-balancer-issues": "The load balancer is marking healthy instances as unhealthy and users are experiencing connection issues.",
        
        "certificate-expiration": "HTTPS connections are failing with certificate errors. Users can't access our secure endpoints."
    }


def get_workshop_test_sequence() -> List[str]:
    """Get recommended sequence of scenarios for workshop testing."""
    return [
        "pod-crash-loop",          # Start with beginner Kubernetes issue
        "disk-space-alert",        # Basic node-level troubleshooting
        "certificate-expiration",  # Simple security issue
        "api-response-degradation", # Multi-service performance issue
        "database-connection-errors", # Database connectivity
        "load-balancer-issues",    # AWS-specific networking
        "memory-leak-investigation", # Advanced performance analysis
        "service-mesh-failure"     # Most complex distributed system issue
    ]