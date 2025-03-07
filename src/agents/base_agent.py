"""
Base agent class for the CVM multi-agent system.
All specialized agents will inherit from this class.
"""
from abc import ABC, abstractmethod
import logging

class BaseAgent(ABC):
    """
    Abstract base class for all CVM agents.
    
    Attributes:
        name (str): The name of the agent
        config (dict): Configuration settings for the agent
        logger: Logger instance for the agent
    """
    def __init__(self, name, config=None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    def process(self, message):
        """
        Process an incoming message and return a response.
        
        Args:
            message (dict): The message to process
            
        Returns:
            dict: The response message
        """
        pass
    
    def log(self, level, message):
        """
        Standardized logging for all agents.
        
        Args:
            level (str): Logging level (debug, info, warning, error, critical)
            message (str): Log message
        """
        getattr(self.logger, level)(f"[{self.name}] {message}") 