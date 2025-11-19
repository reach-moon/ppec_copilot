# tests/test_mem0_client.py
import pytest
from unittest.mock import patch, MagicMock
import importlib

# Force reimport of the module to avoid caching issues
import app.core.mem0_client
importlib.reload(app.core.mem0_client)
from app.core.mem0_client import get_mem0_client, Mem0ClientSingleton


class TestMem0Client:
    """Test cases for Mem0 client singleton implementation"""

    def setup_method(self):
        """Reset singleton instance before each test"""
        Mem0ClientSingleton._instance = None
        # Clear the LRU cache to ensure fresh initialization
        get_mem0_client.cache_clear()

    def test_singleton_instance(self):
        """Test that Mem0ClientSingleton returns the same instance"""
        instance1 = Mem0ClientSingleton()
        instance2 = Mem0ClientSingleton()
        assert instance1 is instance2

    def test_get_mem0_client_returns_same_instance(self):
        """Test that get_mem0_client returns the same client instance"""
        with patch('app.core.mem0_client.Memory') as mock_memory:
            # Mock the Memory class to avoid actual initialization
            mock_client = MagicMock()
            mock_memory.from_config.return_value = mock_client

            # Reset singleton for clean test
            Mem0ClientSingleton._instance = None
            # Clear the LRU cache to ensure fresh initialization
            get_mem0_client.cache_clear()

            client1 = get_mem0_client()
            client2 = get_mem0_client()

            # Both calls should return the same client instance
            assert client1 is client2
            # Memory.from_config should only be called once due to lru_cache
            mock_memory.from_config.assert_called_once()

    def test_get_client_returns_client(self):
        """Test that get_client method returns the client"""
        with patch('app.core.mem0_client.Memory') as mock_memory:
            mock_client = MagicMock()
            mock_memory.from_config.return_value = mock_client

            # Reset singleton for clean test
            Mem0ClientSingleton._instance = None

            singleton = Mem0ClientSingleton()
            client = singleton.get_client()

            assert client is mock_client

    @patch('app.core.mem0_client.Memory')
    def test_client_initialization_with_config(self, mock_memory):
        """Test that client is initialized with proper configuration"""
        mock_client = MagicMock()
        mock_memory.from_config.return_value = mock_client

        # Reset the singleton instance for fresh test
        Mem0ClientSingleton._instance = None

        singleton = Mem0ClientSingleton()
        client = singleton.get_client()

        # Check that from_config was called with a configuration dict
        mock_memory.from_config.assert_called_once()
        args, kwargs = mock_memory.from_config.call_args
        config = args[0] if args else kwargs['config']

        # Verify the structure of the configuration
        assert 'llm' in config
        assert 'embedder' in config
        assert 'vector_store' in config
        assert 'version' in config

        # Verify LLM config structure
        assert 'provider' in config['llm']
        assert 'config' in config['llm']

        # Verify embedder config structure
        assert 'provider' in config['embedder']
        assert 'config' in config['embedder']

        # Verify vector_store config structure
        assert 'provider' in config['vector_store']
        assert 'config' in config['vector_store']

    def test_client_initialization_failure(self):
        """Test that client handles initialization failure gracefully"""
        with patch('app.core.mem0_client.Memory') as mock_memory:
            # Simulate initialization failure
            mock_memory.from_config.side_effect = Exception("Initialization failed")

            # Reset the singleton instance for fresh test
            Mem0ClientSingleton._instance = None

            singleton = Mem0ClientSingleton()
            client = singleton.get_client()

            # Should return None when initialization fails
            assert client is None
            mock_memory.from_config.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])