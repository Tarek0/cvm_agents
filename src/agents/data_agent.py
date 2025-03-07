"""
Data Agent for the CVM multi-agent system.
Responsible for all data access operations.
"""
from src.agents.base_agent import BaseAgent
from src.tools.api_v2 import load_customer_data

class DataAgent(BaseAgent):
    """
    Agent responsible for all data access operations.
    
    This agent handles loading customer data from various sources
    and provides caching capabilities for improved performance.
    """
    def __init__(self, config=None):
        super().__init__("data_agent", config)
        self.data_cache = {}  # Simple in-memory cache
        self.cache_enabled = config.get("enable_cache", True)
        self.log("info", "Data Agent initialized")
    
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
        Fetch customer data, using cache if available.
        
        Args:
            customer_id (str): The customer ID to fetch data for
            
        Returns:
            dict: Customer data
        """
        if self.cache_enabled and customer_id in self.data_cache:
            self.log("info", f"Cache hit for customer {customer_id}")
            return self.data_cache[customer_id]
        
        self.log("info", f"Loading data for customer {customer_id}")
        data = load_customer_data(customer_id)
        
        if self.cache_enabled:
            self.data_cache[customer_id] = data
            
        return data
    
    def clear_cache(self):
        """
        Clear the data cache.
        
        Returns:
            dict: Status message
        """
        cache_size = len(self.data_cache)
        self.data_cache = {}
        self.log("info", f"Cache cleared ({cache_size} entries)")
        return {"status": "success", "message": f"Cache cleared ({cache_size} entries)"} 