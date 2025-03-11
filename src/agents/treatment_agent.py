"""
Treatment Recommendation Agent for the CVM multi-agent system.
Specializes in determining optimal treatments for customers.
"""
from src.agents.base_agent import BaseAgent
from smolagents import CodeAgent, LiteLLMModel
import json
import os

# Check if there is a conditional for these imports or code to create fake classes for testing
try:
    from litellm import completion
    class LiteLLMModel:
        def __init__(self, model_id):
            self.model_id = model_id
            
        def completion(self, prompt):
            return completion(model=self.model_id, messages=[{"role": "user", "content": prompt}])
    
    class CodeAgent:
        def __init__(self, config=None):
            self.config = config
            
        def generate_recommendation(self, customer_journey, treatments, constraints, permissions):
            import json
            
            # In a real implementation, this would use an actual LLM to generate recommendations
            # For now, just return a simple recommendation based on journey data
            if not customer_journey:
                return "ignore", "No journey data available"
            
            # Find the customer with highest churn risk as an example
            churn_data = next((item for item in customer_journey if isinstance(item, dict) and item.get("churn_probability")), None)
            if churn_data and churn_data.get("churn_probability", 0) > 0.6:
                # High churn risk, recommend call_back if available
                if "call_back" in treatments and treatments["call_back"].get("enabled", True):
                    return "call_back", "High churn risk detected, recommend immediate callback to prevent churn."
                
            # Find network issues
            network_data = next((item for item in customer_journey if isinstance(item, dict) and "connection_quality" in item), None)
            if network_data and network_data.get("connection_quality") == "poor":
                # Network issues, send service message
                if "service_sms" in treatments and treatments["service_sms"].get("enabled", True):
                    return "service_sms", "Poor network connectivity detected, recommend service update message."
            
            # Default to loyalty app if available
            if "loyalty_app" in treatments and treatments["loyalty_app"].get("enabled", True):
                return "loyalty_app", "Recommend loyalty app update with personalized offers."
            
            # Default fallback
            return "ignore", "No specific treatment recommended based on available data."
            
        def find_alternative_recommendation(self, customer_journey, excluded_treatment, treatments, constraints, permissions):
            # Simple implementation that just picks another treatment
            all_enabled = [id for id, t in treatments.items() if t.get("enabled", True) and id != excluded_treatment]
            if not all_enabled:
                return "ignore", "No alternative treatments available."
                
            # Pick treatment with next highest priority
            sorted_treatments = sorted(
                [(tid, constraints.get(tid, {}).get("priority", 100)) for tid in all_enabled],
                key=lambda x: x[1]
            )
            
            if sorted_treatments:
                return sorted_treatments[0][0], f"Alternative to {excluded_treatment}."
            
            return "ignore", "No suitable alternative treatments found."
except ImportError:
    # For testing or environments without LiteLLM
    class LiteLLMModel:
        def __init__(self, model_id):
            self.model_id = model_id
            
        def completion(self, prompt):
            return {"choices": [{"message": {"content": "This is a mock response."}}]}
    
    class CodeAgent:
        def __init__(self, config=None):
            self.config = config
            
        def generate_recommendation(self, customer_journey, treatments, constraints, permissions):
            return "ignore", "This is a mock recommendation."
            
        def find_alternative_recommendation(self, customer_journey, excluded_treatment, treatments, constraints, permissions):
            return "ignore", "This is a mock alternative recommendation."

class TreatmentAgent(BaseAgent):
    """
    Agent responsible for determining optimal treatments for customers.
    
    This agent analyzes customer journeys and recommends the most appropriate
    treatment based on business rules and customer information.
    """
    
    def __init__(self, config=None):
        """
        Initialize the TreatmentAgent.
        
        Args:
            config: Configuration object
        """
        super().__init__("Treatment", config)
        
        # Initialize cache
        self.cache = {}
        self.recommendation_cache = {}
        
        # Check if config is a dictionary or a CVMConfig object
        if hasattr(config, 'settings') and isinstance(config.settings, dict):
            # It's a CVMConfig object
            self.cache_enabled = config.settings.get("enable_cache", True)
            self.model_config = config.model
        elif isinstance(config, dict):
            # It's a dictionary
            self.cache_enabled = config.get("enable_cache", True)
            self.model_config = config.get("model", {})
        else:
            # Default
            self.cache_enabled = True
            self.model_config = {}
            
        # Get model ID from config or environment
        model_id = (
            self.model_config.get("id") if hasattr(self.model_config, "get") else None
        ) or os.environ.get("MODEL_ID", "gpt-4o")
        
        # Initialize model and agent
        self.model = LiteLLMModel(model_id=model_id)
        self.agent = CodeAgent()
        
        self.log("INFO", f"TreatmentAgent initialized with model {model_id}")

    def process(self, message):
        """
        Process treatment-related requests.
        
        Args:
            message: Request message
            
        Returns:
            Treatment recommendation or error
        """
        if isinstance(message, dict):
            message_type = message.get("type", "")
            
            if message_type == "recommend_treatment":
                return self.recommend_treatment(
                    message.get("journey", []),
                    message.get("treatments", {}),
                    message.get("constraints", {}),
                    message.get("permissions", {})
                )
            
            elif message_type == "find_alternative":
                return self.find_alternative_treatment(
                    message.get("journey", []),
                    message.get("excluded_treatment", ""),
                    message.get("treatments", {}),
                    message.get("constraints", {}),
                    message.get("permissions", {})
                )
            
            else:
                self.log("WARNING", f"Unknown message type: {message_type}")
                return {"status": "error", "message": f"Unknown message type: {message_type}"}
        else:
            self.log("ERROR", f"Invalid message format: {type(message)}")
            return {"status": "error", "message": "Invalid message format"}

    def recommend_treatment(self, customer_journey, treatments, constraints, permissions):
        """
        Recommend the optimal treatment for a customer.
        
        Args:
            customer_journey: Customer journey data
            treatments: Available treatments
            constraints: Treatment constraints
            permissions: Customer permissions
            
        Returns:
            Treatment recommendation
        """
        self.log("INFO", "Recommending treatment based on customer journey")
        
        # Check cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(customer_journey, treatments, constraints)
            if cache_key in self.recommendation_cache:
                self.log("INFO", "Using cached treatment recommendation")
                return self.recommendation_cache[cache_key]
        
        # Generate treatment recommendation using the agent
        selected_treatment, explanation = self.agent.generate_recommendation(
            customer_journey, 
            treatments, 
            constraints, 
            permissions
        )
        
        # Apply permission filters
        permission_explanation = ""
        if permissions:
            # Simple permission check (would be more sophisticated in production)
            if selected_treatment in ["retention_email", "service_sms", "retention_sms"]:
                channel = "email" if selected_treatment == "retention_email" else "sms"
                
                # Check if the customer allows marketing messages in this channel
                if not self._check_permission(permissions, channel, "marketing"):
                    self.log("INFO", f"Customer doesn't allow {channel} marketing, choosing alternative")
                    selected_treatment = "loyalty_app"  # Use app instead
                    permission_explanation = f"\nCustomer doesn't allow {channel} marketing, using loyalty app instead."
        
        # Final recommendation
        result = {
            "selected_treatment": selected_treatment,
            "explanation": explanation + permission_explanation
        }
        
        # Cache the result if caching is enabled
        if self.cache_enabled:
            self.recommendation_cache[cache_key] = result
        
        return result

    def find_alternative_treatment(self, customer_journey, excluded_treatment, treatments, constraints, permissions):
        """
        Find an alternative treatment when the primary treatment is unavailable.
        
        Args:
            customer_journey: Customer journey data
            excluded_treatment: Treatment to exclude
            treatments: Available treatments
            constraints: Treatment constraints
            permissions: Customer permissions
            
        Returns:
            Alternative treatment recommendation
        """
        self.log("INFO", f"Finding alternative to {excluded_treatment}")
        
        # Remove the excluded treatment
        available_treatments = {k: v for k, v in treatments.items() if k != excluded_treatment}
        
        # Use the agent to find an alternative
        selected_treatment, explanation = self.agent.find_alternative_recommendation(
            customer_journey,
            excluded_treatment,
            available_treatments,
            constraints,
            permissions
        )
        
        return {
            "selected_treatment": selected_treatment,
            "explanation": explanation
        }

    def _format_permissions(self, permissions):
        """Format permissions for prompt."""
        if not permissions:
            return "No specific permission data available."
            
        # Format permissions for the prompt
        channels = []
        for channel, perms in permissions.get("permissions", {}).items():
            allowed = [k for k, v in perms.items() if v == "Y"]
            if allowed:
                channels.append(f"{channel}: allows {', '.join(allowed)}")
            
        if channels:
            return "Customer permissions:\n" + "\n".join(channels)
        else:
            return "Customer has not provided specific permissions."

    def _check_permission(self, permissions, channel, permission_type):
        """Check if a specific permission is granted."""
        try:
            return permissions.get("permissions", {}).get(channel, {}).get(permission_type, "N") == "Y"
        except (KeyError, AttributeError):
            return False
            
    def _get_cache_key(self, customer_journey, treatments, constraints):
        """Generate a cache key for treatment recommendations."""
        # Simple implementation - in production would use a more sophisticated approach
        journey_hash = hash(str(customer_journey)[:1000])  # Limit size for hashing
        treatments_hash = hash(str(sorted(treatments.keys())))
        constraints_hash = hash(str(constraints)[:500])
        
        return f"{journey_hash}_{treatments_hash}_{constraints_hash}" 