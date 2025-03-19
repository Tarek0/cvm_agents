"""
Unit tests for the TriggerAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.agents.trigger_agent import TriggerAgent, LiteLLMModel

@pytest.fixture
def mock_customer_data():
    """Return mock customer data for testing."""
    return {
        "U123": {
            "id": "U123",
            "demographics": {
                "age": 35,
                "income_bracket": "medium",
                "customer_since": "2020-01-15"
            },
            "interactions": [
                {"type": "call", "timestamp": "2023-01-01T10:00:00", "content": "Complained about slow internet and network issues"},
                {"type": "chat", "timestamp": "2023-01-05T14:30:00", "content": "Asked about upgrading plan"}
            ],
            "billing": {
                "current_plan": "Standard",
                "monthly_spend": 45.99,
                "payment_history": [{"date": "2023-01-01", "amount": 45.99, "status": "paid"}]
            },
            "network": {
                "connection_quality": 0.55,  # Poor connection quality
                "usage_pattern": "heavy_streaming",
                "frequent_locations": ["home", "work"]
            }
        },
        "U124": {
            "id": "U124",
            "demographics": {
                "age": 42,
                "income_bracket": "high",
                "customer_since": "2018-05-20"
            },
            "interactions": [
                {"type": "call", "timestamp": "2023-01-10T11:15:00", "content": "Disputed billing charge for international calls"},
                {"type": "email", "timestamp": "2023-01-12T09:45:00", "content": "Follow-up on billing dispute, customer threatening to leave"}
            ],
            "billing": {
                "current_plan": "Premium",
                "monthly_spend": 89.99,
                "payment_history": [
                    {"date": "2023-01-01", "amount": 89.99, "status": "paid"},
                    {"date": "2022-12-01", "amount": 89.99, "status": "paid"}
                ]
            },
            "network": {
                "connection_quality": 0.85,
                "usage_pattern": "business_usage",
                "frequent_locations": ["work", "international"]
            }
        },
        "U125": {
            "id": "U125",
            "demographics": {
                "age": 28,
                "income_bracket": "low",
                "customer_since": "2022-08-10"
            },
            "interactions": [
                {"type": "chat", "timestamp": "2023-01-15T16:20:00", "content": "Asked about downgrading plan to save money"}
            ],
            "billing": {
                "current_plan": "Basic",
                "monthly_spend": 29.99,
                "payment_history": [
                    {"date": "2023-01-01", "amount": 29.99, "status": "paid"},
                    {"date": "2022-12-01", "amount": 29.99, "status": "late"}
                ]
            },
            "network": {
                "connection_quality": 0.75,
                "usage_pattern": "light_usage",
                "frequent_locations": ["home"]
            }
        }
    }

@pytest.fixture
def mock_network_data():
    """Return mock customer network data for testing."""
    return {
        "call_transcripts": [
            {"summary": "Customer reported network issues and slow connection", "sentiment": "negative"},
            {"summary": "Follow-up on network issues, still unresolved", "sentiment": "negative"}
        ],
        "web_transcripts": [
            {"summary": "Asked about network speed and quality", "sentiment": "neutral"}
        ],
        "network_data": [
            {"connection_quality": "poor", "download_speed_mbps": 2.5, "latency_ms": 120, "packet_loss_percent": 2.3}
        ]
    }

@pytest.fixture
def mock_billing_data():
    """Return mock customer billing data for testing."""
    return {
        "call_transcripts": [
            {"summary": "Customer disputed a charge on their bill", "sentiment": "negative"}
        ],
        "billing_data": [
            {"payment_status": "overdue", "monthly_charge": 49.99, "additional_charges": 25.0}
        ]
    }

@pytest.fixture
def mock_churn_data():
    """Return mock customer churn data for testing."""
    return {
        "call_transcripts": [
            {"summary": "Customer threatened to cancel service", "sentiment": "negative"},
            {"summary": "Customer complained about service", "sentiment": "negative"}
        ],
        "churn_score": [
            {"churn_probability": 0.75, "risk_factors": ["service issues", "billing disputes"]}
        ]
    }

@pytest.fixture
def mock_high_value_data():
    """Return mock high value customer data for testing."""
    return {
        "usage_data": [
            {"data_usage_gb": 50.0, "voice_usage_minutes": 500}
        ],
        "billing_data": [
            {"monthly_charge": 99.99, "additional_charges": 0}
        ],
        "churn_score": [
            {"customer_lifetime_months": 48, "churn_probability": 0.1}
        ]
    }

@pytest.fixture
def mock_roaming_data():
    """Return mock customer roaming data for testing."""
    return {
        "call_transcripts": [
            {"summary": "Customer asked about roaming charges while traveling abroad", "sentiment": "neutral"}
        ],
        "usage_data": [
            {"roaming_data_gb": 1.5, "roaming_voice_minutes": 30}
        ]
    }

class TestTriggerAgent:
    """Tests for the TriggerAgent class."""
    
    def test_trigger_agent_initialization(self):
        """Test that TriggerAgent initializes correctly."""
        # Default initialization
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        
        agent = TriggerAgent(config=config)
        assert agent.name == "Trigger"
        assert agent.config == config
        assert agent.llm is not None
        assert hasattr(agent, "predefined_triggers")
        assert len(agent.predefined_triggers) > 0
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_network_issues(self, mock_load_all_customer_data, mock_customer_data):
        """Test identifying customers with network issues."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock one of the predefined trigger functions directly
        original_trigger = agent.predefined_triggers["network_issues"]
        agent.predefined_triggers["network_issues"] = MagicMock(return_value={
            "matches": True,
            "evidence": {
                "network": {"connection_quality": 0.55},
                "interactions": ["slow internet and network issues"]
            }
        })
        
        try:
            result = agent.process({
                "type": "trigger_customers",
                "customer_ids": ["U123", "U124", "U125"],
                "trigger_type": "network_issues"
            })
            
            # Verify the results
            assert result["status"] == "success"
            assert isinstance(result["matches"], list)
            assert len(result["matches"]) > 0
        finally:
            # Restore the original trigger function
            agent.predefined_triggers["network_issues"] = original_trigger
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_billing_disputes(self, mock_load_all_customer_data, mock_customer_data):
        """Test identifying customers with billing disputes."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock one of the predefined trigger functions directly
        original_trigger = agent.predefined_triggers["billing_disputes"]
        agent.predefined_triggers["billing_disputes"] = MagicMock(return_value={
            "matches": True,
            "evidence": {
                "interactions": ["Disputed billing charge for international calls"]
            }
        })
        
        try:
            result = agent.process({
                "type": "trigger_customers",
                "customer_ids": ["U123", "U124", "U125"],
                "trigger_type": "billing_disputes"
            })
            
            # Verify the results
            assert result["status"] == "success"
            assert isinstance(result["matches"], list)
            assert len(result["matches"]) > 0
        finally:
            # Restore the original trigger function
            agent.predefined_triggers["billing_disputes"] = original_trigger
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_churn_risk(self, mock_load_all_customer_data, mock_customer_data):
        """Test identifying customers with churn risk."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock one of the predefined trigger functions directly with a side effect
        original_trigger = agent.predefined_triggers["churn_risk"]
        side_effect_func = lambda customer_data: (
            {"matches": True, "evidence": {"interactions": ["threatening to leave"]}}
            if customer_data["id"] == "U124" else
            {"matches": True, "evidence": {"billing": {"payment_history": [{"status": "late"}]}}}
            if customer_data["id"] == "U125" else
            None  # No match for U123
        )
        agent.predefined_triggers["churn_risk"] = MagicMock(side_effect=side_effect_func)
        
        try:
            result = agent.process({
                "type": "trigger_customers",
                "customer_ids": ["U123", "U124", "U125"],
                "trigger_type": "churn_risk"
            })
            
            # Verify the results
            assert result["status"] == "success"
            assert isinstance(result["matches"], list)
            # Should have 2 matches (U124 and U125)
            assert len(result["matches"]) == 2
            customer_ids = [match["customer_id"] for match in result["matches"]]
            assert set(customer_ids) == set(["U124", "U125"])
        finally:
            # Restore the original trigger function
            agent.predefined_triggers["churn_risk"] = original_trigger
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_high_value(self, mock_load_all_customer_data, mock_customer_data):
        """Test identifying high-value customers."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock one of the predefined trigger functions directly
        original_trigger = agent.predefined_triggers["high_value"]
        agent.predefined_triggers["high_value"] = MagicMock(return_value={
            "matches": True,
            "evidence": {
                "demographics": {"income_bracket": "high"},
                "billing": {"current_plan": "Premium", "monthly_spend": 89.99}
            }
        })
        
        try:
            result = agent.process({
                "type": "trigger_customers",
                "customer_ids": ["U123", "U124", "U125"],
                "trigger_type": "high_value"
            })
            
            # Verify the results
            assert result["status"] == "success"
            assert isinstance(result["matches"], list)
            assert len(result["matches"]) > 0
        finally:
            # Restore the original trigger function
            agent.predefined_triggers["high_value"] = original_trigger
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_custom_trigger_keywords(self, mock_load_all_customer_data, mock_customer_data):
        """Test custom trigger with keywords."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock the _analyze_with_llm method
        agent._analyze_with_llm = MagicMock(return_value={
            "matches": True,
            "reason": "Matches the search criteria",
            "evidence": ["Complained about slow internet"]
        })
        
        # Create a custom trigger
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124", "U125"],
            "trigger_type": "custom",
            "custom_trigger": "Customers with network problems"
        })
        
        # Verify the results
        assert result["status"] == "success"
        assert isinstance(result["matches"], list)
        assert agent._analyze_with_llm.call_count > 0
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_custom_trigger_llm(self, mock_load_all_customer_data, mock_customer_data):
        """Test custom trigger with LLM analysis."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock the _analyze_with_llm method
        agent._analyze_with_llm = MagicMock()
        agent._analyze_with_llm.return_value = {
            "matches": True,
            "reason": "Network issues detected in customer interactions and data"
        }
        
        # Create a custom trigger using description
        custom_trigger = {
            "description": "Customers with network connection problems"
        }
        
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124", "U125"],
            "trigger_type": "custom",
            "custom_trigger": custom_trigger
        })
        
        # Verify the results
        assert result["status"] == "success"
        assert isinstance(result["matches"], list)
        # LLM analyze method should be called
        agent._analyze_with_llm.assert_called()
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_invalid_trigger_type(self, mock_load_all_customer_data, mock_customer_data):
        """Test handling of invalid trigger type."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124", "U125"],
            "trigger_type": "invalid_trigger"
        })
        
        # Verify the results
        assert result["status"] == "error"
        assert "invalid trigger type" in result["message"].lower() or "unknown trigger type" in result["message"].lower()
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_no_matches(self, mock_load_all_customer_data, mock_customer_data):
        """Test case with no matching customers."""
        # Set up the mock to return empty data (no matches)
        mock_load_all_customer_data.return_value = {}
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U999"],  # Non-existent customer
            "trigger_type": "network_issues"
        })
        
        # Verify the results
        assert result["status"] == "success"
        assert len(result["matches"]) == 0
        assert result["total_matches"] == 0
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_custom_trigger_missing_parameters(self, mock_load_all_customer_data, mock_customer_data):
        """Test custom trigger with missing parameters."""
        # Set up the mock to return our test data
        mock_load_all_customer_data.return_value = mock_customer_data
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124", "U125"],
            "trigger_type": "custom",
            "custom_trigger": {}  # Empty custom trigger
        })
        
        # Verify the results
        assert result["status"] == "error"
        assert "missing required parameters" in result["message"].lower() or "invalid custom trigger" in result["message"].lower()
    
    def test_list_triggers(self):
        """Test listing available triggers."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process({"type": "list_triggers"})
        
        assert result["status"] == "success"
        assert "available_triggers" in result
        assert isinstance(result["available_triggers"], list)
        assert "network_issues" in result["available_triggers"]
        assert "custom" in result["available_triggers"]
    
    @patch('src.agents.trigger_agent.load_all_customer_data')
    def test_trigger_agent_error_handling(self, mock_load_all_customer_data):
        """Test error handling in TriggerAgent."""
        # Simulate an error in data loading
        mock_load_all_customer_data.side_effect = Exception("Test error")
        
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U123"],
            "trigger_type": "network_issues"
        })
        
        # Verify the error was handled properly
        assert result["status"] == "error"
        assert "error" in result["message"].lower()
        assert "test error" in result["message"].lower()
    
    def test_trigger_agent_invalid_message_type(self):
        """Test handling of invalid message types."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process({"type": "invalid_type"})
        
        assert result["status"] == "error"
        assert "unknown message type" in result["message"].lower()
    
    def test_trigger_agent_invalid_message_format(self):
        """Test handling of invalid message format."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent.process("not a dictionary")
        
        assert result["status"] == "error"
        assert "invalid message format" in result["message"].lower()
    
    def test_trigger_agent_analyze_with_llm(self):
        """Test the _analyze_with_llm method directly."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock the LLM completion method
        agent.llm.completion = MagicMock(return_value={
            "choices": [
                {"text": '{"matches": true, "reason": "Test reason", "evidence": ["Test evidence"]}'}
            ]
        })
        
        customer_data = {
            "call_transcripts": [
                {"date": "2023-01-01", "summary": "Test summary", "sentiment": "neutral"}
            ]
        }
        
        result = agent._analyze_with_llm(customer_data, "Test trigger")
        
        # Verify results
        assert result["matches"] is True
        assert result["reason"] == "Test reason"
        assert "evidence" in result
        assert agent.llm.completion.called
    
    def test_trigger_agent_analyze_with_llm_error_handling(self):
        """Test error handling in _analyze_with_llm method."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Mock the LLM completion method to raise an exception
        agent.llm.completion = MagicMock(side_effect=Exception("Test exception"))
        
        customer_data = {
            "call_transcripts": [
                {"date": "2023-01-01", "summary": "Test summary", "sentiment": "neutral"}
            ]
        }
        
        result = agent._analyze_with_llm(customer_data, "Test trigger")
        
        # Verify the error was handled properly
        assert result["matches"] is False
    
    def test_network_issues_trigger_direct(self, mock_network_data):
        """Test the network issues trigger function directly."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent._trigger_network_issues(mock_network_data)
        
        # Verify the result
        assert result is not None
        assert "network issues" in result.lower() or "connection" in result.lower()
    
    def test_billing_disputes_trigger_direct(self, mock_billing_data):
        """Test the billing disputes trigger function directly."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent._trigger_billing_disputes(mock_billing_data)
        
        # Verify the result
        assert result is not None
        assert "billing" in result.lower() or "charge" in result.lower() or "overdue" in result.lower()
    
    def test_churn_risk_trigger_direct(self, mock_churn_data):
        """Test the churn risk trigger function directly."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent._trigger_churn_risk(mock_churn_data)
        
        # Verify the result
        assert result is not None
        assert "churn" in result.lower() or "probability" in result.lower()
    
    def test_high_value_trigger_direct(self, mock_high_value_data):
        """Test the high value trigger function directly."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent._trigger_high_value(mock_high_value_data)
        
        # Verify the result
        assert result is not None
        assert "high" in result.lower() or "usage" in result.lower() or "charge" in result.lower()
    
    def test_roaming_issues_trigger_direct(self, mock_roaming_data):
        """Test the roaming issues trigger function directly."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        result = agent._trigger_roaming_issues(mock_roaming_data)
        
        # Verify the result
        assert result is not None
        assert "roaming" in result.lower() or "international" in result.lower()
    
    def test_get_snippet_function(self):
        """Test the _get_snippet helper function."""
        config = MagicMock()
        config.model = {"id": "gpt-4"}
        agent = TriggerAgent(config=config)
        
        # Test normal case
        text = "This is a sample text with the keyword in the middle"
        snippet = agent._get_snippet(text, "keyword", context_chars=10)
        assert "keyword" in snippet
        assert len(snippet) <= len("keyword") + 2*10 + 6  # keyword + context + ellipsis
        
        # Test with keyword at the beginning
        text = "keyword is at the beginning of this text"
        snippet = agent._get_snippet(text, "keyword", context_chars=10)
        assert "keyword" in snippet
        assert not snippet.startswith("...")
        
        # Test with keyword at the end
        text = "This text ends with the keyword"
        snippet = agent._get_snippet(text, "keyword", context_chars=10)
        assert "keyword" in snippet
        assert not snippet.endswith("...")
        
        # Test with missing keyword
        text = "This text does not contain the search term"
        snippet = agent._get_snippet(text, "keyword", context_chars=10)
        assert snippet == ""
        
        # Test with empty inputs
        assert agent._get_snippet("", "keyword") == ""
        assert agent._get_snippet(None, "keyword") == ""
        assert agent._get_snippet("text", "") == ""
        assert agent._get_snippet("text", None) == ""

    def test_litellm_model_initialization(self):
        """Test the LiteLLMModel initialization."""
        model = LiteLLMModel("gpt-4")
        assert model.model_id == "gpt-4"
        assert model.client is not None 