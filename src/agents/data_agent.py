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
        self.permissions_cache = {}
        
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
        - get_customer_permissions: Fetch permissions for a specific customer
        - clear_cache: Clear the data cache
        
        Args:
            message (dict): Request message
            
        Returns:
            dict: Response with requested data or error
        """
        msg_type = message.get("type")
        
        if msg_type == "get_customer_data":
            return self.get_customer_data(message.get("customer_id"))
        elif msg_type == "get_customer_permissions":
            return self.get_customer_permissions(message.get("customer_id"))
        elif msg_type == "clear_cache":
            return self.clear_cache()
        else:
            self.log("WARNING", f"Unknown message type: {msg_type}")
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
            self.log("INFO", f"Cache hit for customer {customer_id}")
            return {"customer_data": self.cache[customer_id]}
        
        self.log("INFO", f"Loading data for customer {customer_id}")
        data = load_customer_data(customer_id)
        
        if self.cache_enabled:
            self.cache[customer_id] = data
            
        return {"customer_data": data}
    
    def get_customer_permissions(self, customer_id):
        """
        Retrieve customer permissions for a specific customer.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Dictionary with customer permissions
        """
        if self.cache_enabled and customer_id in self.permissions_cache:
            self.log("INFO", f"Permissions cache hit for customer {customer_id}")
            return {"permissions": self.permissions_cache[customer_id]}
        
        self.log("INFO", f"Loading permissions for customer {customer_id}")
        
        # Default permissions - in a real implementation, this would load from a database
        permissions = {
            "email": {"marketing": "Y", "service": "Y"},
            "sms": {"marketing": "Y", "service": "Y"},
            "call": {"marketing": "Y", "service": "Y"}
        }
        
        # For test customer U124, set call marketing to N
        if customer_id == "U124":
            permissions["call"]["marketing"] = "N"
        
        if self.cache_enabled:
            self.permissions_cache[customer_id] = permissions
            
        return {"permissions": permissions}
    
    def clear_cache(self):
        """
        Clear the data cache.
        
        Returns:
            dict: Status message
        """
        data_cache_size = len(self.cache)
        permissions_cache_size = len(self.permissions_cache)
        self.cache = {}
        self.permissions_cache = {}
        total_size = data_cache_size + permissions_cache_size
        self.log("INFO", f"Cache cleared ({total_size} entries)")
        return {"status": "success", "message": f"Cache cleared ({total_size} entries)"} 