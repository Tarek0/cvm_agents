"""
Unit tests for the TreatmentAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.agents.treatment_agent import TreatmentAgent, CodeAgent, LiteLLMModel

@pytest.fixture
def mock_customer_journey():
    """Return a mock customer journey for testing."""
    return [
        {
            "date": "2023-01-01",
            "type": "call",
            "channel": "support",
            "description": "Customer called about slow internet",
            "sentiment": "negative",
            "churn_probability": 0.7
        },
        {
            "date": "2023-01-05",
            "type": "chat",
            "channel": "website",
            "description": "Customer asked about upgrading plan",
            "sentiment": "neutral",
            "churn_probability": 0.5
        },
        {
            "connection_quality": "poor",
            "usage_pattern": "heavy_streaming",
            "frequent_locations": ["home", "work"]
        }
    ]

@pytest.fixture
def mock_treatments():
    """Return mock treatments for testing."""
    return {
        "call_back": {
            "enabled": True,
            "description": "Agent callback to discuss customer issues"
        },
        "service_sms": {
            "enabled": True,
            "description": "SMS notification about service improvements"
        },
        "loyalty_app": {
            "enabled": True,
            "description": "Notification in loyalty app with special offers"
        },
        "retention_email": {
            "enabled": True,
            "description": "Retention email with special offer"
        },
        "retention_sms": {
            "enabled": False,
            "description": "Retention SMS with special offer"
        }
    }

@pytest.fixture
def mock_constraints():
    """Return mock treatment constraints for testing."""
    return {
        "call_back": {
            "priority": 1,
            "max_per_day": 50
        },
        "service_sms": {
            "priority": 2,
            "max_per_day": 500
        },
        "loyalty_app": {
            "priority": 3,
            "max_per_day": 1000
        }
    }

@pytest.fixture
def mock_permissions():
    """Return mock customer permissions for testing."""
    return {
        "permissions": {
            "email": {
                "marketing": "Y",
                "service": "Y"
            },
            "sms": {
                "marketing": "N",
                "service": "Y"
            },
            "app": {
                "marketing": "Y",
                "service": "Y"
            }
        }
    }

@pytest.fixture
def code_agent():
    """Return a CodeAgent instance for testing."""
    model = MagicMock()
    model.completion.return_value = {
        "choices": [{"text": '{"treatment": "call_back", "reason": "Test reason"}'}]
    }
    return CodeAgent(model)

class TestTreatmentAgent:
    """Tests for the TreatmentAgent class."""
    
    def test_treatment_agent_initialization(self):
        """Test that TreatmentAgent initializes correctly."""
        # Default initialization
        agent = TreatmentAgent()
        assert agent.name == "Treatment"
        assert agent.cache_enabled is True
        assert hasattr(agent, "cache")
        assert hasattr(agent, "recommendation_cache")
        assert hasattr(agent, "model")
        assert hasattr(agent, "agent")
        
        # Test with config dictionary
        config_dict = {"enable_cache": False, "model": {"id": "gpt-3.5-turbo"}}
        agent_with_dict = TreatmentAgent(config=config_dict)
        assert agent_with_dict.cache_enabled is False
        
        # Test with config object
        config_obj = MagicMock()
        config_obj.settings = {"enable_cache": False}
        config_obj.model = {"id": "gpt-3.5-turbo"}
        agent_with_obj = TreatmentAgent(config=config_obj)
        assert agent_with_obj.cache_enabled is False
    
    @patch.object(CodeAgent, 'generate_recommendation')
    def test_recommend_treatment(self, mock_generate_recommendation, mock_customer_journey, mock_treatments, mock_constraints, mock_permissions):
        """Test recommending a treatment."""
        # Setup mock return value
        mock_generate_recommendation.return_value = ("call_back", "High churn risk detected")
        
        agent = TreatmentAgent()
        result = agent.process({
            "type": "recommend_treatment", 
            "journey": mock_customer_journey,
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": mock_permissions
        })
        
        # Verify the recommendation is as expected
        assert "selected_treatment" in result
        assert result["selected_treatment"] == "call_back"
        assert "explanation" in result
        assert "High churn risk detected" in result["explanation"]
        
        # Verify the mock was called with correct arguments
        mock_generate_recommendation.assert_called_once_with(
            mock_customer_journey, 
            mock_treatments, 
            mock_constraints, 
            mock_permissions
        )
    
    @patch.object(CodeAgent, 'generate_recommendation')
    def test_treatment_agent_caching(self, mock_generate_recommendation, mock_customer_journey, mock_treatments, mock_constraints, mock_permissions):
        """Test that the TreatmentAgent properly caches results."""
        # Setup mock return value
        mock_generate_recommendation.return_value = ("call_back", "High churn risk detected")
        
        agent = TreatmentAgent(config={"enable_cache": True})
        
        # First call should hit the mock
        first_result = agent.process({
            "type": "recommend_treatment", 
            "journey": mock_customer_journey,
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": mock_permissions
        })
        
        assert first_result["selected_treatment"] == "call_back"
        assert mock_generate_recommendation.call_count == 1
        
        # Second call with same inputs should use cache
        mock_generate_recommendation.reset_mock()
        second_result = agent.process({
            "type": "recommend_treatment", 
            "journey": mock_customer_journey,
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": mock_permissions
        })
        
        assert second_result["selected_treatment"] == "call_back"
        assert mock_generate_recommendation.call_count == 0  # Not called again
    
    @patch.object(CodeAgent, 'generate_recommendation')
    def test_treatment_agent_cache_disabled(self, mock_generate_recommendation, mock_customer_journey, mock_treatments, mock_constraints, mock_permissions):
        """Test behavior when cache is disabled."""
        # Setup mock return value
        mock_generate_recommendation.return_value = ("call_back", "High churn risk detected")
        
        agent = TreatmentAgent(config={"enable_cache": False})
        
        # First call should hit the mock
        first_result = agent.process({
            "type": "recommend_treatment", 
            "journey": mock_customer_journey,
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": mock_permissions
        })
        
        assert first_result["selected_treatment"] == "call_back"
        assert mock_generate_recommendation.call_count == 1
        
        # Second call should also hit the mock (no caching)
        mock_generate_recommendation.reset_mock()
        second_result = agent.process({
            "type": "recommend_treatment", 
            "journey": mock_customer_journey,
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": mock_permissions
        })
        
        assert second_result["selected_treatment"] == "call_back"
        assert mock_generate_recommendation.call_count == 1  # Called again
    
    @patch.object(CodeAgent, 'generate_recommendation')
    def test_permission_filtering(self, mock_generate_recommendation, mock_customer_journey, mock_treatments, mock_constraints):
        """Test that permissions correctly filter treatments."""
        # Setup mock return value - trying to use an SMS treatment
        mock_generate_recommendation.return_value = ("retention_sms", "Retention SMS recommended")
        
        # Set up permissions where SMS marketing is not allowed
        restricted_permissions = {
            "permissions": {
                "sms": {
                    "marketing": "N",
                    "service": "Y"
                }
            }
        }
        
        agent = TreatmentAgent()
        result = agent.process({
            "type": "recommend_treatment", 
            "journey": mock_customer_journey,
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": restricted_permissions
        })
        
        # The treatment should be changed due to permission restrictions
        assert result["selected_treatment"] == "loyalty_app"  # Fallback to loyalty app
        assert "doesn't allow sms marketing" in result["explanation"].lower()
    
    @patch.object(CodeAgent, 'find_alternative_recommendation')
    def test_find_alternative_treatment(self, mock_find_alternative, mock_customer_journey, mock_treatments, mock_constraints, mock_permissions):
        """Test finding an alternative treatment."""
        # Setup mock return value
        mock_find_alternative.return_value = ("service_sms", "Alternative to call_back")
        
        agent = TreatmentAgent()
        result = agent.process({
            "type": "find_alternative", 
            "journey": mock_customer_journey,
            "excluded_treatment": "call_back",
            "treatments": mock_treatments,
            "constraints": mock_constraints,
            "permissions": mock_permissions
        })
        
        # Verify the alternative treatment
        assert "selected_treatment" in result
        assert result["selected_treatment"] == "service_sms"
        assert "explanation" in result
        assert "Alternative to call_back" in result["explanation"]
        
        # Verify the mock was called correctly
        mock_find_alternative.assert_called_once_with(
            mock_customer_journey,
            "call_back",
            {k: v for k, v in mock_treatments.items() if k != "call_back"},
            mock_constraints,
            mock_permissions
        )
    
    def test_invalid_message_type(self):
        """Test handling of invalid message types."""
        agent = TreatmentAgent()
        result = agent.process({"type": "invalid_type"})
        
        assert "status" in result
        assert result["status"] == "error"
        assert "Unknown message type" in result["message"]
    
    def test_invalid_message_format(self):
        """Test handling of invalid message format."""
        agent = TreatmentAgent()
        result = agent.process("not a dictionary")
        
        assert "status" in result
        assert result["status"] == "error"
        assert "Invalid message format" in result["message"]
    
    def test_check_permission(self, mock_permissions):
        """Test the permission checking utility."""
        agent = TreatmentAgent()
        
        # Test permissions that should be allowed
        assert agent._check_permission(mock_permissions, "email", "marketing") is True
        assert agent._check_permission(mock_permissions, "sms", "service") is True
        
        # Test permissions that should be denied
        assert agent._check_permission(mock_permissions, "sms", "marketing") is False
        
        # Test missing permissions
        assert agent._check_permission(mock_permissions, "phone", "marketing") is False
        assert agent._check_permission({}, "email", "marketing") is False
    
    def test_get_cache_key(self, mock_customer_journey, mock_treatments, mock_constraints):
        """Test cache key generation."""
        agent = TreatmentAgent()
        
        # Generate a cache key
        key = agent._get_cache_key(mock_customer_journey, mock_treatments, mock_constraints)
        
        # Verify it's a string with the expected format
        assert isinstance(key, str)
        assert "_" in key  # Should contain underscores as separators
        
        # Generate another key with the same data - should be identical
        key2 = agent._get_cache_key(mock_customer_journey, mock_treatments, mock_constraints)
        assert key == key2
        
        # Generate a key with different data - should be different
        key3 = agent._get_cache_key(mock_customer_journey, {"different": "treatments"}, mock_constraints)
        assert key != key3 
    
    def test_litellm_model_initialization(self):
        """Test LiteLLMModel initialization in TreatmentAgent."""
        agent = TreatmentAgent()
        
        assert hasattr(agent, "model")
        assert isinstance(agent.model, LiteLLMModel)
        assert agent.model.model_id is not None
    
    @patch('src.agents.treatment_agent.os')
    def test_litellm_model_with_env_vars(self, mock_os):
        """Test LiteLLMModel using environment variables."""
        # Set up environment variable mock
        mock_os.getenv.return_value = "test-api-key"
        
        model = LiteLLMModel("gpt-4")
        assert model.model_id == "gpt-4"
        assert hasattr(model, "client")
        
        # Verify os.getenv was called to get API key
        mock_os.getenv.assert_called_with("OPENAI_API_KEY")
    
    def test_code_agent_direct(self, code_agent, mock_customer_journey, mock_treatments, mock_constraints, mock_permissions):
        """Test CodeAgent methods directly."""
        # Test generate_recommendation
        treatment, explanation = code_agent.generate_recommendation(
            mock_customer_journey, mock_treatments, mock_constraints, mock_permissions
        )
        
        assert treatment == "call_back"
        assert explanation == "Test reason"
        assert code_agent.model.completion.called
        
        # Test find_alternative_recommendation
        code_agent.model.completion.reset_mock()
        code_agent.model.completion.return_value = {
            "choices": [{"text": '{"treatment": "service_sms", "reason": "Alternative option"}'}]
        }
        
        treatment, explanation = code_agent.find_alternative_recommendation(
            mock_customer_journey, "call_back", mock_treatments, mock_constraints, mock_permissions
        )
        
        assert treatment == "service_sms"
        assert explanation == "Alternative option"
        assert code_agent.model.completion.called
    
    @patch('src.agents.treatment_agent.json.loads')
    def test_code_agent_error_handling(self, mock_json_loads, code_agent, mock_customer_journey, mock_treatments, mock_constraints, mock_permissions):
        """Test error handling in CodeAgent."""
        # Test JSON parsing error
        mock_json_loads.side_effect = Exception("Invalid JSON")
        
        # Should return a fallback treatment when JSON parsing fails
        treatment, explanation = code_agent.generate_recommendation(
            mock_customer_journey, mock_treatments, mock_constraints, mock_permissions
        )
        
        assert treatment == "ignore"  # Fallback option
        assert "Error parsing recommendation" in explanation
        
        # Test missing treatment in response
        mock_json_loads.side_effect = None
        mock_json_loads.return_value = {"reason": "Test reason"}  # Missing treatment key
        
        treatment, explanation = code_agent.generate_recommendation(
            mock_customer_journey, mock_treatments, mock_constraints, mock_permissions
        )
        
        assert treatment == "ignore"  # Fallback option
        assert "Missing treatment in recommendation" in explanation
    
    @patch('src.agents.treatment_agent.OpenAI')
    def test_litellm_completion(self, mock_openai_class, mock_customer_journey):
        """Test the completion method of LiteLLMModel."""
        # Set up mock response
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='{"result": "test"}'))]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        model = LiteLLMModel("gpt-4")
        result = model.completion("Test prompt")
        
        # Verify the result format
        assert "choices" in result
        assert len(result["choices"]) == 1
        assert "text" in result["choices"][0]
        
        # Verify the OpenAI client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4"
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][1]["role"] == "user"
    
    @patch('src.agents.treatment_agent.OpenAI')
    @patch('src.agents.treatment_agent.logging')
    def test_litellm_completion_error_handling(self, mock_logging, mock_openai_class):
        """Test error handling in LiteLLMModel completion."""
        # Set up client to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client
        
        model = LiteLLMModel("gpt-4")
        
        # The method should raise the exception
        with pytest.raises(Exception) as excinfo:
            model.completion("Test prompt")
        
        assert "API error" in str(excinfo.value)
        
        # Verify error was logged
        mock_logging.error.assert_called()
    
    @patch('src.agents.treatment_agent.OpenAI')
    @patch('src.agents.treatment_agent.json')
    @patch('src.agents.treatment_agent.logging')
    def test_litellm_completion_invalid_json(self, mock_logging, mock_json, mock_openai_class):
        """Test handling of invalid JSON in LiteLLMModel completion."""
        # Set up mock response with invalid JSON
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='invalid json'))]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        # Set up JSON loads to raise exception
        mock_json.loads.side_effect = Exception("Invalid JSON")
        
        model = LiteLLMModel("gpt-4")
        result = model.completion("Test prompt")
        
        # Verify error handling result
        assert "choices" in result
        assert len(result["choices"]) == 1
        assert "text" in result["choices"][0]
        assert "matches" in result["choices"][0]["text"]
        assert "False" in result["choices"][0]["text"]
        
        # Verify error was logged
        mock_logging.error.assert_called() 