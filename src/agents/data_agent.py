"""
Data Agent for the CVM multi-agent system.
Responsible for all data access operations.
"""
from src.agents.base_agent import BaseAgent
from src.tools.api_v2 import load_customer_data

class DataAgent(BaseAgent):
    """
    Agent responsible for data access operations.
    
    This agent handles retrieving and caching customer data from various sources.
    """
    
    def __init__(self, config=None):
        """
        Initialize the DataAgent.
        
        Args:
            config: Configuration object
        """
        super().__init__("Data", config)
        
        # Initialize cache
        self.cache = {}
        
        # Check if config is a dictionary or a CVMConfig object
        if hasattr(config, 'settings') and isinstance(config.settings, dict):
            # It's a CVMConfig object
            self.cache_enabled = config.settings.get("enable_cache", True)
        elif isinstance(config, dict):
            # It's a dictionary
            self.cache_enabled = config.get("enable_cache", True)
        else:
            # Default
            self.cache_enabled = True
            
        self.log("INFO", f"DataAgent initialized with cache {'enabled' if self.cache_enabled else 'disabled'}")
    
    def process(self, message):
        """
        Process data-related requests.
        
        Supported message types:
        - get_customer_data: Fetch data for a specific customer
        - clear_cache: Clear the data cache
        
        Args:
            message (dict): Request message
            
        Returns:
            dict: Response with requested data or error
        """
        msg_type = message.get("type")
        
        if msg_type == "get_customer_data":
            return self.get_customer_data(message.get("customer_id"))
        elif msg_type == "clear_cache":
            return self.clear_cache()
        else:
            self.log("warning", f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}
    
    def get_customer_data(self, customer_id):
        """
        Retrieve customer data for a specific customer.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Customer data in a standardized format
        """
        if self.cache_enabled and customer_id in self.cache:
            self.log("info", f"Cache hit for customer {customer_id}")
            return {"customer_data": self.cache[customer_id]}
        
        self.log("info", f"Loading data for customer {customer_id}")
        data = load_customer_data(customer_id)
        
        if self.cache_enabled:
            self.cache[customer_id] = data
            
        return {"customer_data": data}
    
    def clear_cache(self):
        """
        Clear the data cache.
        
        Returns:
            dict: Status message
        """
        cache_size = len(self.cache)
        self.cache = {}
        self.log("info", f"Cache cleared ({cache_size} entries)")
        return {"status": "success", "message": f"Cache cleared ({cache_size} entries)"} 