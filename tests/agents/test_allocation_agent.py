"""
Unit tests for the AllocationAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
import threading
import copy
from src.agents.allocation_agent import AllocationAgent

@pytest.fixture
def sample_constraints():
    """Return a sample constraints dictionary for testing."""
    return {
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
        },
        "zero_remaining": {
            "max_per_day": 5,
            "remaining_availability": 0,
            "cost_per_contact_pounds": 1.0,
            "priority": 4
        }
    }

class TestAllocationAgent:
    """Tests for the AllocationAgent class."""
    
    def test_allocation_agent_initialization(self, sample_constraints):
        """Test that AllocationAgent initializes correctly."""
        # Default initialization
        agent = AllocationAgent()
        assert agent.name == "Allocation"
        assert agent.constraints == {}
        assert hasattr(agent, "lock")
        assert hasattr(agent, "allocation_history")
        
        # Test with config dictionary
        config_dict = {"constraints": copy.deepcopy(sample_constraints)}
        agent_with_dict = AllocationAgent(config=config_dict)
        assert agent_with_dict.constraints == sample_constraints
        
        # Test with config object
        config_obj = MagicMock()
        config_obj.constraints = copy.deepcopy(sample_constraints)
        agent_with_obj = AllocationAgent(config=config_obj)
        assert agent_with_obj.constraints == sample_constraints
    
    def test_allocate_resource(self, sample_constraints):
        """Test allocating a resource."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        # Allocate a valid treatment
        result = agent.process({
            "type": "allocate_resource", 
            "treatment_key": "call_back", 
            "customer_id": "U123",
            "priority": 0.8
        })
        
        # Verify the allocation was successful
        assert result["status"] == "success"
        assert result["treatment_key"] == "call_back"
        assert result["allocated"] is True
        assert result["remaining"] == 9  # Original 10 - 1
        
        # Verify the constraint was updated
        assert agent.constraints["call_back"]["remaining_availability"] == 9
        
        # Verify allocation was recorded in history
        assert len(agent.allocation_history) == 1
        assert agent.allocation_history[0]["treatment_key"] == "call_back"
        assert agent.allocation_history[0]["customer_id"] == "U123"
        assert agent.allocation_history[0]["priority"] == 0.8
    
    def test_allocate_ignore_treatment(self):
        """Test allocating the 'ignore' treatment which doesn't require resources."""
        agent = AllocationAgent()
        
        result = agent.process({
            "type": "allocate_resource", 
            "treatment_key": "ignore", 
            "customer_id": "U123"
        })
        
        assert result["status"] == "success"
        assert result["treatment_key"] == "ignore"
        assert result["allocated"] is True
    
    def test_allocate_nonexistent_treatment(self, sample_constraints):
        """Test allocating a treatment that doesn't exist in constraints."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        result = agent.process({
            "type": "allocate_resource", 
            "treatment_key": "nonexistent_treatment", 
            "customer_id": "U123"
        })
        
        assert result["status"] == "error"
        assert "not found in constraints" in result["message"]
    
    def test_allocate_zero_availability(self, sample_constraints):
        """Test allocating a treatment with zero remaining availability."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        result = agent.process({
            "type": "allocate_resource", 
            "treatment_key": "zero_remaining", 
            "customer_id": "U123"
        })
        
        assert result["status"] == "error"
        assert "No availability left" in result["message"]
        assert result["allocated"] is False
    
    def test_allocate_no_treatment_key(self):
        """Test allocating without specifying a treatment key."""
        agent = AllocationAgent()
        
        result = agent.process({
            "type": "allocate_resource", 
            "customer_id": "U123"
        })
        
        assert result["status"] == "error"
        assert "No treatment key provided" in result["message"]
    
    def test_check_availability(self, sample_constraints):
        """Test checking resource availability."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        # Check a treatment with availability
        result = agent.process({
            "type": "check_availability", 
            "treatment_key": "call_back"
        })
        
        assert result["status"] == "success"
        assert result["treatment_key"] == "call_back"
        assert result["available"] is True
        assert result["remaining"] == 10
        assert result["max_per_day"] == 10
        assert result["usage_percentage"] == 0.0  # 0% used
        
        # Check a treatment with no availability
        result = agent.process({
            "type": "check_availability", 
            "treatment_key": "zero_remaining"
        })
        
        assert result["status"] == "success"
        assert result["treatment_key"] == "zero_remaining"
        assert result["available"] is False
        assert result["remaining"] == 0
        assert result["max_per_day"] == 5
        assert result["usage_percentage"] == 100.0  # 100% used
    
    def test_check_nonexistent_treatment(self):
        """Test checking availability for a treatment that doesn't exist."""
        agent = AllocationAgent()
        
        result = agent.process({
            "type": "check_availability", 
            "treatment_key": "nonexistent_treatment"
        })
        
        assert result["status"] == "error"
        assert "not found in constraints" in result["message"]
    
    def test_check_no_treatment_key(self):
        """Test checking availability without specifying a treatment key."""
        agent = AllocationAgent()
        
        result = agent.process({
            "type": "check_availability"
        })
        
        assert result["status"] == "error"
        assert "No treatment key provided" in result["message"]
    
    def test_get_constraints(self, sample_constraints):
        """Test getting all constraints."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        result = agent.process({
            "type": "get_constraints"
        })
        
        assert result["status"] == "success"
        assert "constraints" in result
        assert result["constraints"] == sample_constraints
    
    def test_reset_constraints(self, sample_constraints):
        """Test resetting constraints to initial values."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        # Allocate some resources to reduce availability
        agent.process({
            "type": "allocate_resource", 
            "treatment_key": "call_back", 
            "customer_id": "U123"
        })
        agent.process({
            "type": "allocate_resource", 
            "treatment_key": "email_offer", 
            "customer_id": "U124"
        })
        
        # Verify availability was reduced
        assert agent.constraints["call_back"]["remaining_availability"] == 9
        assert agent.constraints["email_offer"]["remaining_availability"] == 49
        
        # Reset constraints
        result = agent.process({
            "type": "reset_constraints"
        })
        
        assert result["status"] == "success"
        assert "Constraints reset" in result["message"]
        
        # Verify availability was reset
        assert agent.constraints["call_back"]["remaining_availability"] == 10
        assert agent.constraints["email_offer"]["remaining_availability"] == 50
        assert agent.constraints["zero_remaining"]["remaining_availability"] == 5  # Also reset
    
    def test_update_constraints(self, sample_constraints):
        """Test updating constraints with new values."""
        agent = AllocationAgent()
        
        # Update constraints using the method directly (not exposed via process)
        result = agent.update_constraints(copy.deepcopy(sample_constraints))
        
        assert result["status"] == "success"
        assert "Constraints updated" in result["message"]
        assert agent.constraints == sample_constraints
    
    def test_unknown_message_type(self):
        """Test handling of unknown message types."""
        agent = AllocationAgent()
        
        result = agent.process({
            "type": "unknown_type"
        })
        
        assert "error" in result
        assert "Unknown message type" in result["error"]
    
    def test_thread_safety(self, sample_constraints):
        """Test thread safety for concurrent allocations."""
        agent = AllocationAgent(config={"constraints": copy.deepcopy(sample_constraints)})
        
        # Function for threads to call
        def allocate_service_sms(customer_id):
            return agent.process({
                "type": "allocate_resource",
                "treatment_key": "service_sms",
                "customer_id": customer_id
            })
        
        # Create and start threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=allocate_service_sms, args=(f"U{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to finish
        for thread in threads:
            thread.join()
        
        # Check that all allocations were recorded correctly
        assert len(agent.allocation_history) == 10
        
        # Check that the remaining availability was reduced correctly
        assert agent.constraints["service_sms"]["remaining_availability"] == 90  # 100 - 10 