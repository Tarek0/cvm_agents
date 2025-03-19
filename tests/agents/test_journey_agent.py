"""
Unit tests for the JourneyAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.agents.journey_agent import JourneyAgent

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

@pytest.fixture
def mock_journey():
    """Return a mock customer journey for testing."""
    return [
        {
            "date": "2023-01-01",
            "type": "call",
            "channel": "support",
            "description": "Customer called about slow internet",
            "sentiment": "negative",
            "churn_probability": 0.35
        },
        {
            "date": "2023-01-05",
            "type": "chat",
            "channel": "website",
            "description": "Customer asked about upgrading plan",
            "sentiment": "neutral",
            "churn_probability": 0.25
        },
        {
            "date": "2023-01-10",
            "type": "email",
            "channel": "marketing",
            "description": "Customer received promotional email",
            "sentiment": "positive",
            "churn_probability": 0.15
        }
    ]

class TestJourneyAgent:
    """Tests for the JourneyAgent class."""
    
    def test_journey_agent_initialization(self):
        """Test that JourneyAgent initializes correctly."""
        # Default initialization
        agent = JourneyAgent()
        assert agent.name == "Journey"
        assert agent.cache_enabled is True
        assert hasattr(agent, "journey_cache")
        assert agent.journey_cache == {}
        
        # Test with config dictionary
        config_dict = {"enable_cache": False, "max_journey_events": 100}
        agent_with_dict = JourneyAgent(config=config_dict)
        assert agent_with_dict.cache_enabled is False
        assert agent_with_dict.max_journey_events == 100
        
        # Test with config object
        config_obj = MagicMock()
        config_obj.settings = {"enable_cache": False, "max_journey_events": 75}
        agent_with_obj = JourneyAgent(config=config_obj)
        assert agent_with_obj.cache_enabled is False
        assert agent_with_obj.max_journey_events == 75
    
    @patch('src.agents.journey_agent.build_customer_journey')
    def test_journey_agent_build_journey(self, mock_build_journey, mock_customer_data):
        """Test building a customer journey from data."""
        # Setup mock return value
        mock_journey = [
            {"date": "2023-01-01", "type": "call", "sentiment": "negative"},
            {"date": "2023-01-05", "type": "chat", "sentiment": "neutral"}
        ]
        mock_build_journey.return_value = mock_journey
        
        agent = JourneyAgent()
        result = agent.process({
            "type": "build_journey", 
            "customer_id": "U123", 
            "customer_data": mock_customer_data
        })
        
        # Verify the journey was built correctly
        assert "customer_id" in result
        assert result["customer_id"] == "U123"
        assert "journey" in result
        assert result["journey"] == mock_journey
        
        # Verify the mock was called with correct arguments
        mock_build_journey.assert_called_once_with("U123", mock_customer_data)
    
    def test_journey_agent_missing_customer_data(self):
        """Test handling of missing or empty customer_data in build_journey."""
        agent = JourneyAgent()
        
        result = agent.process({
            "type": "build_journey", 
            "customer_id": "U123",
            "customer_data": None
        })
        
        assert "error" in result
        assert "No data provided for customer" in result["error"]
    
    def test_journey_agent_analyze_journey(self, mock_journey):
        """Test analyzing a journey."""
        agent = JourneyAgent()
        
        result = agent.process({
            "type": "analyze_journey", 
            "journey": mock_journey
        })
        
        # Check expected fields in response
        assert "journey_length" in result
        assert result["journey_length"] == 3
        assert "metrics" in result
        assert "status" in result
        assert result["status"] == "success"
        
        # Check metrics structure
        metrics = result["metrics"]
        assert "sentiment" in metrics
        assert "interactions_by_channel" in metrics
        assert "recent_activity" in metrics
        assert "churn_risk" in metrics
        
        # Verify sentiment counts
        assert metrics["sentiment"]["positive"] == 1
        assert metrics["sentiment"]["neutral"] == 1
        assert metrics["sentiment"]["negative"] == 1
        
        # Verify interaction channels
        assert "call" in metrics["interactions_by_channel"]
        assert "chat" in metrics["interactions_by_channel"]
        assert "email" in metrics["interactions_by_channel"]
        
        # Verify recent activity is the latest date
        assert metrics["recent_activity"] == "2023-01-10"
        
        # Verify churn risk is present
        assert metrics["churn_risk"] is not None
    
    def test_journey_agent_analyze_empty_journey(self):
        """Test analyzing an empty journey."""
        agent = JourneyAgent()
        
        result = agent.process({
            "type": "analyze_journey", 
            "journey": []
        })
        
        assert "error" in result
        assert "No journey data provided for analysis" in result["error"]
    
    def test_journey_agent_summarize_journey(self, mock_journey):
        """Test summarizing a journey."""
        agent = JourneyAgent()
        
        result = agent.process({
            "type": "get_journey_summary", 
            "journey": mock_journey,
            "max_events": 2
        })
        
        # Check expected fields in response
        assert "total_events" in result
        assert result["total_events"] == 3
        assert "events_included" in result
        assert result["events_included"] == 2
        assert "recent_events" in result
        assert len(result["recent_events"]) == 2
        assert "status" in result
        assert result["status"] == "success"
        
        # Verify the events are sorted with most recent first
        first_event_date = result["recent_events"][0]["date"]
        second_event_date = result["recent_events"][1]["date"]
        assert first_event_date >= second_event_date
    
    def test_journey_agent_summarize_empty_journey(self):
        """Test summarizing an empty journey."""
        agent = JourneyAgent()
        
        result = agent.process({
            "type": "get_journey_summary", 
            "journey": []
        })
        
        assert "error" in result
        assert "No journey data provided for summarization" in result["error"]
    
    def test_journey_agent_invalid_message_type(self):
        """Test handling of invalid message types."""
        agent = JourneyAgent()
        result = agent.process({"type": "invalid_type"})
        
        assert "error" in result
        assert "Unknown message type" in result["error"] 