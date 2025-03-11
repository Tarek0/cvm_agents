"""
Customer Journey Agent for the CVM multi-agent system.
Specializes in building and analyzing customer journeys.
"""
from src.agents.base_agent import BaseAgent
from src.tools.api_v2 import build_customer_journey

class JourneyAgent(BaseAgent):
    """
    Agent responsible for building and analyzing customer journeys.
    
    This agent transforms raw customer data into structured journey
    representations and provides analysis capabilities.
    """
    def __init__(self, config=None):
        """
        Initialize the JourneyAgent.
        
        Args:
            config: Configuration object
        """
        super().__init__("Journey", config)
        
        # Initialize cache and settings
        self.journey_cache = {}
        
        # Check if config is a dictionary or a CVMConfig object
        if hasattr(config, 'settings') and isinstance(config.settings, dict):
            # It's a CVMConfig object
            self.cache_enabled = config.settings.get("enable_cache", True)
            self.max_journey_events = config.settings.get("max_journey_events", 50)
        elif isinstance(config, dict):
            # It's a dictionary
            self.cache_enabled = config.get("enable_cache", True)
            self.max_journey_events = config.get("max_journey_events", 50)
        else:
            # Default values
            self.cache_enabled = True
            self.max_journey_events = 50
        
        self.log("INFO", "JourneyAgent initialized")
    
    def process(self, message):
        """
        Process journey-related requests.
        
        Supported message types:
        - build_journey: Build a customer journey from raw data
        - analyze_journey: Extract key insights from a journey
        - get_journey_summary: Get a summarized version of a journey
        
        Args:
            message (dict): Request message
            
        Returns:
            dict: Response with journey data or error
        """
        msg_type = message.get("type")
        
        if msg_type == "build_journey":
            return self.build_journey(
                message.get("customer_id"),
                message.get("customer_data")
            )
        elif msg_type == "analyze_journey":
            return self.analyze_journey(message.get("journey"))
        elif msg_type == "get_journey_summary":
            return self.summarize_journey(
                message.get("journey"),
                message.get("max_events", 5)
            )
        else:
            self.log("warning", f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}
    
    def build_journey(self, customer_id, customer_data):
        """
        Build a customer journey from raw data.
        
        Args:
            customer_id (str): The customer ID
            customer_data (dict): Raw customer data
            
        Returns:
            dict: Built customer journey
        """
        if not customer_data:
            self.log("error", f"No data provided for customer {customer_id}")
            return {"error": f"No data provided for customer {customer_id}"}
            
        self.log("info", f"Building journey for customer {customer_id}")
        journey = build_customer_journey(customer_id, customer_data)
        
        # Store in cache if enabled
        if self.cache_enabled:
            cache_key = f"journey_{customer_id}"
            self.journey_cache[cache_key] = journey
            
        return {"customer_id": customer_id, "journey": journey}
    
    def analyze_journey(self, journey):
        """
        Analyze a customer journey to extract key insights.
        
        Args:
            journey (list): Customer journey data
            
        Returns:
            dict: Journey analysis results
        """
        if not journey:
            self.log("error", "No journey data provided for analysis")
            return {"error": "No journey data provided for analysis"}
            
        # Extract key metrics from journey
        metrics = self._extract_journey_metrics(journey)
        
        return {
            "journey_length": len(journey),
            "metrics": metrics,
            "status": "success"
        }
    
    def summarize_journey(self, journey, max_events=5):
        """
        Create a summarized version of a customer journey.
        
        Args:
            journey (list): Customer journey data
            max_events (int): Maximum number of events to include
            
        Returns:
            dict: Summarized journey
        """
        if not journey:
            self.log("error", "No journey data provided for summarization")
            return {"error": "No journey data provided for summarization"}
            
        # Sort events by date (most recent first)
        sorted_events = sorted(
            journey, 
            key=lambda x: x.get("date", ""),
            reverse=True
        )
        
        # Select the most recent events
        recent_events = sorted_events[:max_events]
        
        return {
            "total_events": len(journey),
            "events_included": len(recent_events),
            "recent_events": recent_events,
            "status": "success"
        }
    
    def _extract_journey_metrics(self, journey):
        """
        Extract key metrics from a customer journey.
        
        Args:
            journey (list): Customer journey data
            
        Returns:
            dict: Extracted metrics
        """
        metrics = {
            "sentiment": {
                "positive": 0,
                "neutral": 0,
                "negative": 0
            },
            "interactions_by_channel": {},
            "recent_activity": None,
            "churn_risk": None
        }
        
        # Extract sentiment
        for event in journey:
            sentiment = event.get("sentiment")
            if sentiment in metrics["sentiment"]:
                metrics["sentiment"][sentiment] += 1
                
            # Count interactions by channel
            channel = event.get("type") or event.get("channel")
            if channel:
                if channel not in metrics["interactions_by_channel"]:
                    metrics["interactions_by_channel"][channel] = 0
                metrics["interactions_by_channel"][channel] += 1
                
            # Get churn probability if available
            if "churn_probability" in event and event["churn_probability"] is not None:
                metrics["churn_risk"] = event["churn_probability"]
                
        # Get most recent activity date
        dates = [event.get("date") for event in journey if event.get("date")]
        if dates:
            metrics["recent_activity"] = max(dates)
            
        return metrics 