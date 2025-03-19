"""
Unit tests for the BaseAgent class.
"""
import pytest
from unittest.mock import patch, MagicMock
import logging
from src.agents.base_agent import BaseAgent

# Create a concrete implementation of BaseAgent for testing
class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def process(self, message):
        """Process a message."""
        if not isinstance(message, dict) or "type" not in message:
            return {"status": "error", "message": "Invalid message format"}
            
        message_type = message.get("type")
        
        if message_type == "test_success":
            return {"status": "success", "result": "test_result"}
        elif message_type == "test_error":
            return {"status": "error", "message": "test_error_message"}
        else:
            return {"status": "error", "message": "Message type not implemented"}

class TestBaseAgent:
    """Tests for the BaseAgent class."""
    
    def test_base_agent_initialization(self):
        """Test that BaseAgent initializes correctly."""
        # Test with custom name
        agent = ConcreteAgent(name="test_agent")
        assert agent.name == "test_agent"
        assert agent.config is None
        assert isinstance(agent.logger, logging.Logger)
        
        # Test with custom name and config
        config = {"test": "config"}
        agent_with_config = ConcreteAgent(name="test_agent", config=config)
        assert agent_with_config.config == config
    
    @patch('logging.Logger.debug')
    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.error')
    @patch('logging.Logger.critical')
    def test_agent_logging(self, mock_critical, mock_error, mock_warning, mock_info, mock_debug):
        """Test the log method."""
        agent = ConcreteAgent(name="test_agent")
        
        # Test various log levels
        agent.log("debug", "Debug message")
        mock_debug.assert_called_once_with("[test_agent] Debug message")
        
        agent.log("info", "Info message")
        mock_info.assert_called_once_with("[test_agent] Info message")
        
        agent.log("warning", "Warning message")
        mock_warning.assert_called_once_with("[test_agent] Warning message")
        
        agent.log("error", "Error message")
        mock_error.assert_called_once_with("[test_agent] Error message")
        
        agent.log("critical", "Critical message")
        mock_critical.assert_called_once_with("[test_agent] Critical message")
        
        # Test unknown log level (should default to info)
        agent.log("unknown", "Unknown level message")
        mock_info.assert_called_with("[test_agent] Unknown level message (unknown level: unknown)")

class TestConcreteAgent:
    """Tests for the concrete implementation of BaseAgent."""
    
    def test_concrete_agent_success(self):
        """Test successful processing in the concrete agent."""
        agent = ConcreteAgent(name="test_agent")
        
        result = agent.process({"type": "test_success"})
        
        assert result["status"] == "success"
        assert result["result"] == "test_result"
    
    def test_concrete_agent_error(self):
        """Test error handling in the concrete agent."""
        agent = ConcreteAgent(name="test_agent")
        
        result = agent.process({"type": "test_error"})
        
        assert result["status"] == "error"
        assert result["message"] == "test_error_message"
    
    def test_concrete_agent_unknown_type(self):
        """Test handling of unknown message types."""
        agent = ConcreteAgent(name="test_agent")
        
        result = agent.process({"type": "unknown_type"})
        
        assert result["status"] == "error"
        assert "not implemented" in result["message"].lower()
    
    def test_concrete_agent_invalid_message(self):
        """Test handling of invalid messages."""
        agent = ConcreteAgent(name="test_agent")
        
        # Test with non-dict message
        result = agent.process("not a dict")
        assert result["status"] == "error"
        assert "invalid message format" in result["message"].lower()
        
        # Test with dict missing type
        result = agent.process({"not_type": "value"})
        assert result["status"] == "error"
        assert "invalid message format" in result["message"].lower() 