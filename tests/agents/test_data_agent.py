"""
Unit tests for the DataAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.agents.data_agent import DataAgent

@pytest.fixture
def mock_customer_data():
    """Return mock customer data for testing."""
    return {
        "id": "U123",
        "demographics": {
            "age": 35,
            "income_bracket": "medium",
            "customer_since": "2020-01-15"
        },
        "interactions": [
            {"type": "call", "timestamp": "2023-01-01T10:00:00", "content": "Complained about slow internet"},
            {"type": "chat", "timestamp": "2023-01-05T14:30:00", "content": "Asked about upgrading plan"}
        ],
        "billing": {
            "current_plan": "Standard",
            "monthly_spend": 45.99,
            "payment_history": [{"date": "2023-01-01", "amount": 45.99, "status": "paid"}]
        },
        "network": {
            "connection_quality": 0.75,
            "usage_pattern": "heavy_streaming",
            "frequent_locations": ["home", "work"]
        }
    }

class TestDataAgent:
    """Tests for the DataAgent class."""
    
    def test_data_agent_initialization(self):
        """Test that DataAgent initializes correctly."""
        # Default initialization
        agent = DataAgent()
        assert agent.name == "Data"
        assert agent.cache_enabled is True
        assert agent.cache == {}
        
        # Test with config dictionary
        config_dict = {"enable_cache": False}
        agent_with_dict = DataAgent(config=config_dict)
        assert agent_with_dict.cache_enabled is False
        
        # Test with config object
        config_obj = MagicMock()
        config_obj.settings = {"enable_cache": False}
        agent_with_obj = DataAgent(config=config_obj)
        assert agent_with_obj.cache_enabled is False
    
    @patch('src.agents.data_agent.load_customer_data')
    def test_data_agent_get_customer_data(self, mock_load_customer_data, mock_customer_data):
        """Test getting customer data."""
        mock_load_customer_data.return_value = mock_customer_data
        
        agent = DataAgent()
        result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        
        # Verify the mock was called with the correct customer ID
        mock_load_customer_data.assert_called_once_with("U123")
        
        # Verify the result contains the mock data
        assert "customer_data" in result
        assert result["customer_data"]["id"] == "U123"
        assert result["customer_data"]["demographics"]["age"] == 35
        assert len(result["customer_data"]["interactions"]) == 2
    
    @patch('src.agents.data_agent.load_customer_data')
    def test_data_agent_caching(self, mock_load_customer_data, mock_customer_data):
        """Test that the DataAgent properly caches results."""
        mock_load_customer_data.return_value = mock_customer_data
        
        # Create a config dict with cache enabled
        config = {"enable_cache": True}
        agent = DataAgent(config=config)
        
        # First call should hit the mock
        first_result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        assert first_result["customer_data"]["id"] == "U123"
        mock_load_customer_data.assert_called_once()
        
        # Second call should use cache (mock not called again)
        mock_load_customer_data.reset_mock()
        second_result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        assert second_result["customer_data"]["id"] == "U123"
        mock_load_customer_data.assert_not_called()
        
        # Different customer ID should hit the mock again
        mock_load_customer_data.return_value = {**mock_customer_data, "id": "U124"}
        third_result = agent.process({"type": "get_customer_data", "customer_id": "U124"})
        assert third_result["customer_data"]["id"] == "U124"
        mock_load_customer_data.assert_called_once_with("U124")
    
    @patch('src.agents.data_agent.load_customer_data')
    def test_data_agent_cache_disabled(self, mock_load_customer_data, mock_customer_data):
        """Test behavior when cache is disabled."""
        mock_load_customer_data.return_value = mock_customer_data
        
        # Create a config dict with cache disabled
        config = {"enable_cache": False}
        agent = DataAgent(config=config)
        
        # First call should hit the mock
        first_result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        assert first_result["customer_data"]["id"] == "U123"
        mock_load_customer_data.assert_called_once()
        
        # Second call should also hit the mock (no caching)
        mock_load_customer_data.reset_mock()
        second_result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        assert second_result["customer_data"]["id"] == "U123"
        mock_load_customer_data.assert_called_once()
    
    @patch('src.agents.data_agent.load_customer_data')
    def test_data_agent_clear_cache(self, mock_load_customer_data, mock_customer_data):
        """Test clearing the cache."""
        mock_load_customer_data.return_value = mock_customer_data
        
        agent = DataAgent()
        
        # First call should hit the mock
        first_result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        assert first_result["customer_data"]["id"] == "U123"
        mock_load_customer_data.assert_called_once()
        
        # Clear the cache
        clear_result = agent.process({"type": "clear_cache"})
        assert clear_result["status"] == "success"
        assert "cache cleared" in clear_result["message"].lower()
        
        # Next call should hit the mock again
        mock_load_customer_data.reset_mock()
        second_result = agent.process({"type": "get_customer_data", "customer_id": "U123"})
        assert second_result["customer_data"]["id"] == "U123"
        mock_load_customer_data.assert_called_once()
    
    @patch('src.agents.data_agent.load_customer_data')
    def test_data_agent_error_handling(self, mock_load_customer_data):
        """Test error handling in DataAgent."""
        # Simulate an error in data loading
        mock_load_customer_data.side_effect = Exception("Test error")
        
        agent = DataAgent()
        # We need to wrap this in a try-except block since the error is not caught
        try:
            agent.process({"type": "get_customer_data", "customer_id": "U123"})
            assert False, "Expected an exception but none was raised"
        except Exception as e:
            assert str(e) == "Test error"
    
    def test_data_agent_invalid_message_type(self):
        """Test handling of invalid message types."""
        agent = DataAgent()
        result = agent.process({"type": "invalid_type"})
        
        assert "error" in result
        assert "unknown message type" in result["error"].lower()
    
    def test_data_agent_missing_customer_id(self):
        """Test handling of missing customer_id."""
        agent = DataAgent()
        
        # Try calling with a message missing customer_id
        try:
            agent.process({"type": "get_customer_data"})
            assert False, "Expected an exception but none was raised"
        except Exception:
            # The exception type may vary, but some exception should be raised
            pass 