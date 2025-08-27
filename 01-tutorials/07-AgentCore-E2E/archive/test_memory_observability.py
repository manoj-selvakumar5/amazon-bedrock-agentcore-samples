#!/usr/bin/env python3
"""
Test script for AgentCore Memory Observability
==============================================

This script tests the memory observability functionality without requiring
full AWS setup. It validates the class structure and method signatures.
"""

import sys
import logging
from unittest.mock import Mock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that the required modules can be imported when available"""
    try:
        # Test the main module structure
        import agentcore_memory_observability as amo
        logger.info("✅ Successfully imported agentcore_memory_observability")
        
        # Check main classes exist
        assert hasattr(amo, 'ObservableMemoryClient')
        assert hasattr(amo, 'ObservableCustomerSupportMemoryHooks')
        assert hasattr(amo, 'AgentCoreMemoryObservability')
        logger.info("✅ All required classes are present")
        
        return True
    except ImportError as e:
        logger.warning(f"⚠️ Import test skipped due to missing dependencies: {e}")
        return False

def test_class_structure():
    """Test the class structure and method signatures"""
    try:
        with patch.multiple(
            'agentcore_memory_observability',
            MemoryClient=Mock(),
            trace=Mock(),
            Agent=Mock(),
            BedrockModel=Mock(),
            HookProvider=Mock(),
        ):
            import agentcore_memory_observability as amo
            
            # Test ObservableMemoryClient
            mock_client = amo.ObservableMemoryClient("us-east-1")
            assert hasattr(mock_client, 'create_memory_and_wait')
            assert hasattr(mock_client, 'create_event')
            assert hasattr(mock_client, 'retrieve_memories')
            logger.info("✅ ObservableMemoryClient structure is correct")
            
            # Test AgentCoreMemoryObservability
            mock_obs = amo.AgentCoreMemoryObservability("us-east-1")
            assert hasattr(mock_obs, 'setup_observability_environment')
            assert hasattr(mock_obs, 'create_or_get_memory_resource')
            assert hasattr(mock_obs, 'seed_customer_history')
            assert hasattr(mock_obs, 'create_agent_with_memory_hooks')
            logger.info("✅ AgentCoreMemoryObservability structure is correct")
            
            return True
    except Exception as e:
        logger.error(f"❌ Class structure test failed: {e}")
        return False

def test_configuration():
    """Test the configuration and environment setup"""
    try:
        # Test argument parsing
        import agentcore_memory_observability as amo
        
        # Mock sys.argv for argument parsing test
        with patch.object(sys, 'argv', ['test', '--session-id', 'test-123', '--actor-id', 'customer-test']):
            args = amo.parse_arguments()
            assert args.session_id == 'test-123'
            assert args.actor_id == 'customer-test'
            logger.info("✅ Argument parsing works correctly")
        
        return True
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Testing AgentCore Memory Observability")
    logger.info("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Class Structure Test", test_class_structure), 
        ("Configuration Test", test_configuration),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} passed")
            else:
                logger.warning(f"⚠️ {test_name} skipped or failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL/SKIP"
        logger.info(f"  {status}: {test_name}")
    
    logger.info(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! The memory observability system is ready to use.")
    else:
        logger.info("⚠️ Some tests failed or were skipped due to missing dependencies.")
        logger.info("   This is expected if AgentCore packages are not installed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
