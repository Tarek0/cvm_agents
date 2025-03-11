"""
Base agent class for the CVM multi-agent system.
All specialized agents will inherit from this class.
"""
from abc import ABC, abstractmethod
import logging

class BaseAgent(ABC):
    """
    Abstract base class for all CVM agents.
    
    This class defines the common interface and functionality that
    all specialized agents must implement.
    """
    
    def __init__(self, name, config=None):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name
            config: Configuration object
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"agent.{name.lower()}")
    
    @abstractmethod
    def process(self, message):
        """
        Process a message.
        
        This is the main entry point for all agent functionality.
        Each agent must implement this method to handle its specific
        responsibilities.
        
        Args:
            message: Message to process
            
        Returns:
            Processing result
        """
        pass
    
    def log(self, level, message):
        """
        Log a message with standard formatting.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Message to log
        """
        # Normalize the log level to lowercase
        level = level.lower()
        
        if level == "debug":
            self.logger.debug(f"[{self.name}] {message}")
        elif level == "info":
            self.logger.info(f"[{self.name}] {message}")
        elif level == "warning":
            self.logger.warning(f"[{self.name}] {message}")
        elif level == "error":
            self.logger.error(f"[{self.name}] {message}")
        elif level == "critical":
            self.logger.critical(f"[{self.name}] {message}")
        else:
            # Default to info
            self.logger.info(f"[{self.name}] {message} (unknown level: {level})") 