"""
Unit tests for the OrchestratorAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.agents.orchestrator_agent import OrchestratorAgent

@pytest.fixture
def mock_config():
    """Return a mock configuration object for testing."""
    config = MagicMock()
    config.settings = {"enable_cache": True}
    return config

@pytest.fixture
def mock_treatment_manager():
    """Return a mock TreatmentManager for testing."""
    manager = MagicMock()
    
    # Setup mock treatments
    treatments = {
        "call_back": {
            "enabled": True,
            "display_name": "Call Back",
            "description": "Agent callback to discuss customer issues"
        },
        "service_sms": {
            "enabled": True,
            "display_name": "Service SMS",
            "description": "SMS notification about service improvements"
        },
        "email_offer": {
            "enabled": True, 
            "display_name": "Email Offer",
            "description": "Email with special offer"
        },
        "ignore": {
            "enabled": True,
            "display_name": "No Action",
            "description": "No action required"
        }
    }
    
    # Setup mock constraints
    constraints = {
        "call_back": {
            "max_per_day": 10,
            "remaining_availability": 10,
            "cost_per_contact_pounds": 2.0,
            "priority": 1
        },
        "service_sms": {
            "max_per_day": 100,
            "remaining_availability": 100,
            "cost_per_contact_pounds": 0.1,
            "priority": 3
        },
        "email_offer": {
            "max_per_day": 50,
            "remaining_availability": 50,
            "cost_per_contact_pounds": 0.5,
            "priority": 2
        }
    }
    
    # Setup mock methods
    manager.get_enabled_treatments.return_value = {k: v for k, v in treatments.items() if v["enabled"]}
    manager.get_all_treatments.return_value = treatments
    manager.get_all_constraints.return_value = constraints
    manager.add_custom_treatment.return_value = ("custom_treatment", {"description": "A custom treatment"})
    manager.update_custom_treatment.return_value = ("custom_treatment", {"description": "Updated custom treatment"})
    manager.remove_custom_treatment.return_value = True
    manager.list_custom_treatments.return_value = [{"id": "custom_treatment", "description": "A custom treatment"}]
    manager.get_treatment_help.return_value = "Treatment help documentation"
    
    return manager

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
        }
    ]

class TestOrchestratorAgent:
    """Tests for the OrchestratorAgent class."""
    
    @patch('src.agents.orchestrator_agent.DataAgent')
    @patch('src.agents.orchestrator_agent.JourneyAgent')
    @patch('src.agents.orchestrator_agent.TreatmentAgent')
    @patch('src.agents.orchestrator_agent.AllocationAgent')
    @patch('src.agents.orchestrator_agent.TriggerAgent')
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    @patch('src.agents.orchestrator_agent.load_config')
    def test_orchestrator_agent_initialization(self, mock_load_config, mock_treatment_manager_class, 
                                             mock_trigger_agent_class, mock_allocation_agent_class, 
                                             mock_treatment_agent_class, mock_journey_agent_class, 
                                             mock_data_agent_class):
        """Test that OrchestratorAgent initializes correctly."""
        # Setup mocks
        mock_load_config.return_value = MagicMock()
        mock_treatment_manager_class.return_value = MagicMock()
        mock_trigger_agent_class.return_value = MagicMock()
        mock_allocation_agent_class.return_value = MagicMock()
        mock_treatment_agent_class.return_value = MagicMock()
        mock_journey_agent_class.return_value = MagicMock()
        mock_data_agent_class.return_value = MagicMock()
        
        # Initialize agent
        agent = OrchestratorAgent()
        
        # Verify initialization
        assert agent.name == "Orchestrator"
        assert agent.config is not None
        assert agent.treatment_manager is not None
        assert agent.data_agent is not None
        assert agent.journey_agent is not None
        assert agent.treatment_agent is not None
        assert agent.allocation_agent is not None
        assert agent.trigger_agent is not None
        
        # Verify all agent classes were initialized
        mock_data_agent_class.assert_called_once()
        mock_journey_agent_class.assert_called_once()
        mock_treatment_agent_class.assert_called_once()
        mock_allocation_agent_class.assert_called_once()
        mock_trigger_agent_class.assert_called_once()
        mock_treatment_manager_class.assert_called_once()
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_process_customer(self, mock_treatment_manager_class, mock_config, mock_treatment_manager, 
                           mock_customer_data, mock_journey):
        """Test processing a single customer."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent with mocks for sub-agents
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock data agent
        agent.data_agent = MagicMock()
        agent.data_agent.process.return_value = {"customer_data": mock_customer_data}
        
        # Mock journey agent
        agent.journey_agent = MagicMock()
        agent.journey_agent.process.return_value = {"journey": mock_journey}
        
        # Mock treatment agent
        agent.treatment_agent = MagicMock()
        agent.treatment_agent.process.return_value = {
            "selected_treatment": "call_back",
            "explanation": "Call back recommended due to network issues"
        }
        
        # Mock allocation agent
        agent.allocation_agent = MagicMock()
        agent.allocation_agent.process.return_value = {
            "status": "success",
            "allocated": True,
            "treatment_key": "call_back"
        }
        
        # Mock customer permissions
        agent._get_customer_permissions = MagicMock()
        agent._get_customer_permissions.return_value = {"permissions": {"email": {"marketing": "Y"}}}
        
        # Process a customer
        result = agent.process({"type": "process_customer", "customer_id": "U123"})
        
        # Verify the result
        assert result["status"] == "success"
        assert result["customer_id"] == "U123"
        assert result["selected_treatment"] == "call_back"
        assert "explanation" in result
        assert "timestamp" in result
        
        # Verify the sub-agent calls
        agent.data_agent.process.assert_called_once_with({
            "type": "get_customer_data",
            "customer_id": "U123"
        })
        
        agent.journey_agent.process.assert_called_once_with({
            "type": "build_journey",
            "customer_id": "U123",
            "customer_data": mock_customer_data
        })
        
        agent.treatment_agent.process.assert_called_once()
        agent._get_customer_permissions.assert_called_once_with("U123")
        agent.allocation_agent.process.assert_called_once()
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_process_customer_with_treatment(self, mock_treatment_manager_class, mock_config, mock_treatment_manager, 
                                          mock_customer_data, mock_journey):
        """Test processing a customer with a specific treatment."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent with mocks for sub-agents
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock data agent
        agent.data_agent = MagicMock()
        agent.data_agent.process.return_value = {"customer_data": mock_customer_data}
        
        # Mock journey agent
        agent.journey_agent = MagicMock()
        agent.journey_agent.process.return_value = {"journey": mock_journey}
        
        # Mock allocation agent
        agent.allocation_agent = MagicMock()
        agent.allocation_agent.process.return_value = {
            "status": "success",
            "allocated": True,
            "treatment_key": "service_sms"
        }
        
        # Process a customer with a specific treatment
        result = agent.process({
            "type": "process_customer_with_treatment", 
            "customer_id": "U123",
            "treatment_id": "service_sms"
        })
        
        # Verify the result
        assert result["status"] == "success"
        assert result["customer_id"] == "U123"
        assert result["selected_treatment"] == mock_treatment_manager.get_all_treatments.return_value["service_sms"]
        assert "explanation" in result
        assert "direct selection" in result["explanation"]
        assert "timestamp" in result
        
        # Verify the sub-agent calls
        agent.data_agent.process.assert_called_once_with({
            "type": "get_customer_data",
            "customer_id": "U123"
        })
        
        agent.journey_agent.process.assert_called_once_with({
            "type": "build_journey",
            "customer_id": "U123",
            "customer_data": mock_customer_data
        })
        
        agent.allocation_agent.process.assert_called_once_with({
            "type": "allocate_resource",
            "treatment_key": "service_sms",
            "customer_id": "U123"
        })
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_process_batch(self, mock_treatment_manager_class, mock_config, mock_treatment_manager, 
                         mock_customer_data, mock_journey):
        """Test processing a batch of customers."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent with mocks for sub-agents
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock data agent
        agent.data_agent = MagicMock()
        agent.data_agent.process.return_value = {"customer_data": mock_customer_data}
        
        # Mock journey agent
        agent.journey_agent = MagicMock()
        agent.journey_agent.process.return_value = {"journey": mock_journey}
        
        # Mock treatment agent
        agent.treatment_agent = MagicMock()
        agent.treatment_agent.process.return_value = {
            "selected_treatment": "email_offer",
            "explanation": "Email offer recommended due to customer profile"
        }
        
        # Mock allocation agent
        agent.allocation_agent = MagicMock()
        agent.allocation_agent.process.return_value = {
            "status": "success",
            "allocated": True,
            "treatment_key": "email_offer"
        }
        
        # Mock customer permissions
        agent._get_customer_permissions = MagicMock()
        agent._get_customer_permissions.return_value = {"permissions": {"email": {"marketing": "Y"}}}
        
        # Process a batch of customers
        result = agent.process({
            "type": "process_batch", 
            "customer_ids": ["U123", "U124"]
        })
        
        # Verify the result structure
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verify each customer result
        for customer_result in result:
            assert customer_result["status"] == "success"
            assert customer_result["customer_id"] in ["U123", "U124"]
            assert customer_result["selected_treatment"] == "email_offer"
            assert "explanation" in customer_result
            assert "timestamp" in customer_result
        
        # Verify the data agent was called for each customer
        assert agent.data_agent.process.call_count == 2
        # Verify the journey agent was called for each customer
        assert agent.journey_agent.process.call_count == 2
        # Verify the treatment agent was called for each customer
        assert agent.treatment_agent.process.call_count == 2
        # Verify the allocation agent was called for each customer
        assert agent.allocation_agent.process.call_count == 2
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_process_customer_resource_allocation_failure(self, mock_treatment_manager_class, mock_config, 
                                                       mock_treatment_manager, mock_customer_data, mock_journey):
        """Test handling resource allocation failure with finding an alternative treatment."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent with mocks for sub-agents
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock data agent
        agent.data_agent = MagicMock()
        agent.data_agent.process.return_value = {"customer_data": mock_customer_data}
        
        # Mock journey agent
        agent.journey_agent = MagicMock()
        agent.journey_agent.process.return_value = {"journey": mock_journey}
        
        # Mock treatment agent for initial recommendation
        agent.treatment_agent = MagicMock()
        agent.treatment_agent.process.side_effect = [
            # First call - initial recommendation
            {
                "selected_treatment": "call_back",
                "explanation": "Call back recommended due to network issues"
            },
            # Second call - alternative recommendation
            {
                "selected_treatment": "service_sms",
                "explanation": "Service SMS as alternative to call back"
            }
        ]
        
        # Mock allocation agent to fail first allocation but succeed on alternative
        agent.allocation_agent = MagicMock()
        agent.allocation_agent.process.side_effect = [
            # First call - allocation failure
            {
                "status": "error",
                "message": "No availability left for call_back"
            },
            # Second call - allocation success
            {
                "status": "success",
                "allocated": True,
                "treatment_key": "service_sms"
            }
        ]
        
        # Mock customer permissions
        agent._get_customer_permissions = MagicMock()
        agent._get_customer_permissions.return_value = {"permissions": {"email": {"marketing": "Y"}}}
        
        # Process a customer
        result = agent.process({"type": "process_customer", "customer_id": "U123"})
        
        # Verify the result
        assert result["status"] == "success"
        assert result["customer_id"] == "U123"
        assert result["selected_treatment"] == "service_sms"
        assert "explanation" in result
        assert "Alternative" in result["explanation"]
        
        # Verify the treatment agent was called twice
        assert agent.treatment_agent.process.call_count == 2
        
        # Verify alternative recommendation was requested
        alternative_call = agent.treatment_agent.process.call_args_list[1][0][0]
        assert alternative_call["type"] == "find_alternative"
        assert alternative_call["excluded_treatment"] == "call_back"
        
        # Verify allocation agent was called twice
        assert agent.allocation_agent.process.call_count == 2
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_trigger_and_process(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test triggering customers and processing them with a specific treatment."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent with mocks for sub-agents
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock trigger agent
        agent.trigger_agent = MagicMock()
        agent.trigger_agent.process.return_value = {
            "status": "success",
            "matches": [
                {"customer_id": "U123", "evidence": {"reason": "Network issues"}},
                {"customer_id": "U124", "evidence": {"reason": "Network issues"}}
            ]
        }
        
        # Mock process_customer_with_treatment method
        agent.process_customer_with_treatment = MagicMock()
        agent.process_customer_with_treatment.return_value = {
            "status": "success",
            "customer_id": "U123",
            "selected_treatment": {"display_name": "Service SMS"}
        }
        
        # Trigger and process customers
        result = agent.process({
            "type": "trigger_and_process",
            "customer_ids": ["U123", "U124", "U125"],
            "trigger_type": "network_issues",
            "treatment_id": "service_sms"
        })
        
        # Verify the result
        assert result["status"] == "success"
        assert result["matches"] == 2
        assert result["processed"] == 2
        assert "trigger_results" in result
        assert "process_results" in result
        
        # Verify trigger agent was called
        agent.trigger_agent.process.assert_called_once_with({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124", "U125"],
            "trigger_type": "network_issues",
            "custom_trigger": {}
        })
        
        # Verify process_customer_with_treatment was called for each match
        assert agent.process_customer_with_treatment.call_count == 2
        agent.process_customer_with_treatment.assert_any_call("U123", "service_sms")
        agent.process_customer_with_treatment.assert_any_call("U124", "service_sms")
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_treatment_management(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test treatment management operations."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Test add_treatment
        add_result = agent.process({
            "type": "add_treatment",
            "description": "A new treatment to send a personalized offer",
            "treatment_id": "custom_treatment"
        })
        
        assert add_result["status"] == "success"
        assert add_result["treatment_id"] == "custom_treatment"
        mock_treatment_manager.add_custom_treatment.assert_called_once()
        
        # Test update_treatment
        update_result = agent.process({
            "type": "update_treatment",
            "treatment_id": "custom_treatment",
            "description": "Updated treatment description"
        })
        
        assert update_result["status"] == "success"
        assert update_result["treatment_id"] == "custom_treatment"
        mock_treatment_manager.update_custom_treatment.assert_called_once()
        
        # Test remove_treatment
        remove_result = agent.process({
            "type": "remove_treatment",
            "treatment_id": "custom_treatment"
        })
        
        assert remove_result["status"] == "success"
        assert "Treatment custom_treatment removed" in remove_result["message"]
        mock_treatment_manager.remove_custom_treatment.assert_called_once_with("custom_treatment")
        
        # Test list_treatments
        list_result = agent.process({
            "type": "list_treatments",
            "custom_only": True
        })
        
        assert list_result["status"] == "success"
        assert "treatments" in list_result
        mock_treatment_manager.list_custom_treatments.assert_called_once()
        
        # Test get_treatment_help
        help_result = agent.process({
            "type": "get_treatment_help"
        })
        
        assert help_result["status"] == "success"
        assert "help_text" in help_result
        mock_treatment_manager.get_treatment_help.assert_called_once()
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_trigger_customers(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test forwarding trigger_customers to the trigger agent."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock trigger agent
        agent.trigger_agent = MagicMock()
        agent.trigger_agent.process.return_value = {
            "status": "success",
            "matches": [
                {"customer_id": "U123", "evidence": {"reason": "Churn risk"}}
            ]
        }
        
        # Test trigger_customers delegation
        result = agent.process({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124"],
            "trigger_type": "churn_risk"
        })
        
        assert result["status"] == "success"
        assert "matches" in result
        agent.trigger_agent.process.assert_called_once_with({
            "type": "trigger_customers",
            "customer_ids": ["U123", "U124"],
            "trigger_type": "churn_risk"
        })
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_list_triggers(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test forwarding list_triggers to the trigger agent."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock trigger agent
        agent.trigger_agent = MagicMock()
        agent.trigger_agent.process.return_value = {
            "status": "success",
            "triggers": ["network_issues", "billing_disputes", "churn_risk"]
        }
        
        # Test list_triggers delegation
        result = agent.process({
            "type": "list_triggers"
        })
        
        assert result["status"] == "success"
        assert "triggers" in result
        agent.trigger_agent.process.assert_called_once_with({
            "type": "list_triggers"
        })
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_error_handling(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test error handling in different scenarios."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Test missing customer_id
        result = agent.process({
            "type": "process_customer"
        })
        
        assert result["status"] == "error"
        assert "Missing customer_id" in result["message"]
        
        # Test missing customer_ids in batch
        result = agent.process({
            "type": "process_batch"
        })
        
        assert result["status"] == "error"
        assert "Missing customer_ids" in result["message"]
        
        # Test invalid message type
        result = agent.process({
            "type": "invalid_type"
        })
        
        assert result["status"] == "error"
        assert "Unknown message type" in result["message"]
        
        # Test invalid message format
        result = agent.process("not a dictionary")
        
        assert result["status"] == "error"
        assert "Invalid message format" in result["message"]
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_customer_data_retrieval_failure(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test handling of customer data retrieval failure."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock data agent to return failure
        agent.data_agent = MagicMock()
        agent.data_agent.process.return_value = {"status": "error", "message": "Customer not found"}
        
        # Process a customer
        result = agent.process({
            "type": "process_customer",
            "customer_id": "U999"  # Non-existent customer
        })
        
        # Verify result indicates failure
        assert result["status"] == "error"
        assert "Failed to retrieve customer data" in result["message"]
        assert result["customer_id"] == "U999"
        assert "timestamp" in result
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_treatment_not_found(self, mock_treatment_manager_class, mock_config, mock_treatment_manager, 
                              mock_customer_data, mock_journey):
        """Test handling of treatment not found error."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock data agent
        agent.data_agent = MagicMock()
        agent.data_agent.process.return_value = {"customer_data": mock_customer_data}
        
        # Mock journey agent
        agent.journey_agent = MagicMock()
        agent.journey_agent.process.return_value = {"journey": mock_journey}
        
        # Process a customer with a non-existent treatment
        result = agent.process({
            "type": "process_customer_with_treatment",
            "customer_id": "U123",
            "treatment_id": "nonexistent_treatment"
        })
        
        # Verify result indicates failure
        assert result["status"] == "error"
        assert "Treatment nonexistent_treatment not found" in result["message"]
        assert result["customer_id"] == "U123"
        assert "timestamp" in result
    
    @patch('src.agents.orchestrator_agent.TreatmentManager')
    def test_customer_permissions(self, mock_treatment_manager_class, mock_config, mock_treatment_manager):
        """Test the _get_customer_permissions method."""
        # Setup mocks
        mock_treatment_manager_class.return_value = mock_treatment_manager
        
        # Setup agent
        agent = OrchestratorAgent(config=mock_config)
        
        # Mock the json module to avoid actual file operations
        mock_permissions_data = [
            {
                "customer_id": "U123",
                "permissions": {
                    "email": {"marketing": "Y", "service": "Y"},
                    "sms": {"marketing": "N", "service": "Y"}
                }
            }
        ]
        
        with patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_permissions_data), \
             patch('builtins.open', MagicMock()):
            
            # Test permissions retrieval for existing customer
            permissions = agent._get_customer_permissions("U123")
            
            assert permissions is not None
            assert permissions["customer_id"] == "U123"
            assert permissions["permissions"]["email"]["marketing"] == "Y"
            assert permissions["permissions"]["sms"]["marketing"] == "N"
            
            # Test permissions retrieval for non-existent customer
            permissions = agent._get_customer_permissions("U999")
            
            assert permissions == {} 