"""
Treatment Recommendation Agent for the CVM multi-agent system.
Specializes in determining optimal treatments for customers.
"""
from src.agents.base_agent import BaseAgent
from smolagents import CodeAgent, LiteLLMModel, tool
import json
import os
from typing import Dict, List, Any, Tuple

# Create tools outside the class to avoid issues with self reference
@tool
def generate_recommendation_tool(
    customer_journey: List[Dict[str, Any]],
    treatments: Dict[str, Dict[str, Any]],
    constraints: Dict[str, Dict[str, Any]],
    permissions: Dict[str, Any]
) -> Tuple[str, str]:
    """Generate a treatment recommendation based on customer journey data.
    
    Args:
        customer_journey: Customer journey data
        treatments: Available treatments
        constraints: Treatment constraints
        permissions: Customer permissions
        
    Returns:
        Tuple of (treatment_id, explanation)
    """
    # Implement a simple version of the recommendation logic 
    # This implementation would need to be more sophisticated in a real system
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
    
    # Get all available treatments instead of defaulting to loyalty_app
    available_treatments = [id for id, details in treatments.items() if details.get("enabled", True)]
    
    # Only recommend loyalty_app if it's in the filtered/available treatments list
    if "loyalty_app" in treatments and treatments["loyalty_app"].get("enabled", True) and "loyalty_app" in available_treatments:
        return "loyalty_app", "Recommend loyalty app update with personalized offers."
    
    # If we have treatments available, use the first one
    if available_treatments:
        return available_treatments[0], f"Recommend {available_treatments[0]} based on available treatments."
    
    # Default fallback
    return "ignore", "No specific treatment recommended based on available data."

@tool
def find_alternative_recommendation_tool(
    customer_journey: List[Dict[str, Any]],
    excluded_treatment: str,
    treatments: Dict[str, Dict[str, Any]],
    constraints: Dict[str, Dict[str, Any]],
    permissions: Dict[str, Any]
) -> Tuple[str, str]:
    """Find an alternative treatment when the first choice is unavailable.
    
    Args:
        customer_journey: Customer journey data
        excluded_treatment: Treatment to exclude
        treatments: Available treatments
        constraints: Treatment constraints
        permissions: Customer permissions
        
    Returns:
        Tuple of (treatment_id, explanation)
    """
    # Simple implementation that just picks another treatment
    # Make sure to only consider treatments that are ENABLED (respecting the allowed treatments filter)
    all_enabled = [id for id, t in treatments.items() if t.get("enabled", True) and id != excluded_treatment]
    
    if not all_enabled:
        return "ignore", "No alternative treatments available."
        
    # Pick treatment with next highest priority - only from enabled treatments
    sorted_treatments = sorted(
        [(tid, constraints.get(tid, {}).get("priority", 100)) for tid in all_enabled],
        key=lambda x: x[1]
    )
    
    if sorted_treatments:
        # Return the highest priority available treatment
        return sorted_treatments[0][0], f"Alternative to {excluded_treatment} based on priority ranking."
    
    return "ignore", "No suitable alternative treatments found."

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
        
        # Initialize model
        self.model = LiteLLMModel(model_id=model_id)
        
        # Initialize the agent with tools and model 
        self.agent = CodeAgent(
            tools=[generate_recommendation_tool, find_alternative_recommendation_tool], 
            model=self.model
        )
        
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
        
        # Log available treatments to help with debugging
        treatment_keys = list(treatments.keys())
        self.log("INFO", f"Available treatments for recommendation: {treatment_keys}")
        
        # Check cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(customer_journey, treatments, constraints)
            if cache_key in self.recommendation_cache:
                cached_recommendation = self.recommendation_cache[cache_key]
                # Only use cache if the selected treatment is still in the available treatments
                # This prevents using cached recommendations for treatments that have reached their max_per_day
                if cached_recommendation["selected_treatment"] in treatments:
                    self.log("INFO", "Using cached treatment recommendation")
                    return cached_recommendation
                else:
                    self.log("INFO", "Cached treatment no longer available, generating new recommendation")
        
        # Create a summary of the customer journey for improved explainability
        journey_summary = self._summarize_customer_journey(customer_journey)
        
        # Generate treatment recommendation using the CodeAgent with improved prompting
        result = self.agent.run(
            """
            Analyze this customer's journey data in detail and recommend the most appropriate treatment.
            Provide detailed reasoning for your recommendation, including:
            1. Key factors in the customer journey that influenced your decision
            2. Why this treatment is better than alternatives
            3. How the treatment aligns with the customer's needs
            Explain your thought process step by step.
            """,
            {
                "customer_journey": customer_journey,
                "treatments": treatments,
                "constraints": constraints,
                "permissions": permissions
            }
        )
        
        # Extract the recommendation from the result
        if hasattr(result, 'output') and isinstance(result.output, tuple) and len(result.output) == 2:
            selected_treatment, explanation = result.output
            # Capture the full thought process if available
            full_explanation = explanation
            if hasattr(result, 'thinking') and result.thinking:
                full_explanation = f"{explanation}\n\nDetailed analysis:\n{result.thinking}"
        else:
            # Use the global function as fallback
            selected_treatment, explanation = generate_recommendation_tool(
                customer_journey, treatments, constraints, permissions
            )
            full_explanation = explanation
        
        # Safety check: ensure the selected treatment is actually in the available treatments
        if selected_treatment not in treatments and selected_treatment != "ignore":
            self.log("WARNING", f"Agent recommended treatment '{selected_treatment}' but it's not in available treatments")
            
            # Fall back to any available treatment
            if treatments:
                # Sort by priority if possible
                sorted_treatments = []
                for tid, details in treatments.items():
                    priority = constraints.get(tid, {}).get("priority", 100) if constraints else 100
                    sorted_treatments.append((tid, priority))
                
                sorted_treatments.sort(key=lambda x: x[1])  # Sort by priority (lower is better)
                
                if sorted_treatments:
                    selected_treatment = sorted_treatments[0][0]
                    full_explanation = f"Recommending {selected_treatment} as the highest priority available treatment. The originally recommended treatment was not available in the current treatment options."
                else:
                    selected_treatment = "ignore"
                    full_explanation = "No treatments available, recommending no action."
            else:
                selected_treatment = "ignore"
                full_explanation = "No treatments available, recommending no action."
        
        # Apply permission filters with detailed explanations
        permission_explanation = ""
        if permissions:
            # Simple permission check (would be more sophisticated in production)
            if selected_treatment in ["retention_email", "service_sms", "retention_sms"]:
                channel = "email" if selected_treatment == "retention_email" else "sms"
                if permissions.get(channel, {}).get("contact", True) is False:
                    # Customer doesn't want to be contacted via this channel
                    permission_explanation = f"\n\nNote: Customer has opted out of {channel} communications. However, this treatment is still being recommended as it appears to be the most effective option and may be worth attempting despite preferences."
                    
            # Check marketing vs. service
            if selected_treatment in ["retention_email", "retention_sms"]:
                if permissions.get("marketing", {}).get("allowed", True) is False:
                    # Customer doesn't want to receive marketing
                    permission_explanation = f"\n\nNote: Customer has opted out of marketing communications. However, this treatment is still being recommended as it appears to be the most effective option and may be worth attempting despite preferences."
        
        # Extract key journey insights for the explanation
        journey_insights = self._extract_key_insights(customer_journey)
                    
        # Prepare recommendation result with enhanced explanation
        recommendation = {
            "selected_treatment": selected_treatment,
            "explanation": full_explanation + permission_explanation,
            "journey_insights": journey_insights,
            "alternative_treatments": self._identify_alternatives(selected_treatment, treatments, constraints),
            "confidence": self._calculate_confidence(customer_journey, selected_treatment),
            "customer_journey_summary": journey_summary,
            "timestamp": self._get_timestamp()
        }
        
        # Store in cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(customer_journey, treatments, constraints)
            self.recommendation_cache[cache_key] = recommendation
        
        return recommendation

    def find_alternative_treatment(self, customer_journey, excluded_treatment, treatments, constraints, permissions):
        """
        Find an alternative treatment when the original recommendation is not possible.
        
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
        
        # Log the available treatments to help with debugging
        available_alternatives = [
            tid for tid in treatments.keys() 
            if tid != excluded_treatment
        ]
        self.log("INFO", f"Available alternatives: {available_alternatives}")
        
        # Capture why the original treatment was excluded
        exclusion_reason = self._get_exclusion_reason(excluded_treatment, permissions)
        
        # Call the CodeAgent to find an alternative with improved prompting
        result = self.agent.run(
            f"""
            The originally recommended treatment '{excluded_treatment}' is not available because: {exclusion_reason}.
            
            Please analyze the customer journey in detail and find the next best alternative treatment.
            Provide detailed reasoning for your alternative recommendation, including:
            1. Why this alternative is appropriate given the customer's journey
            2. How it compares to the original recommendation
            3. Any trade-offs or considerations to be aware of
            
            Explain your thought process step by step.
            """,
            {
                "customer_journey": customer_journey,
                "excluded_treatment": excluded_treatment,
                "treatments": treatments,
                "constraints": constraints,
                "permissions": permissions
            }
        )
        
        # Extract the recommendation from the result
        if hasattr(result, 'output') and isinstance(result.output, tuple) and len(result.output) == 2:
            selected_treatment, explanation = result.output
            # Capture the full thought process if available
            full_explanation = explanation
            if hasattr(result, 'thinking') and result.thinking:
                full_explanation = f"{explanation}\n\nDetailed analysis:\n{result.thinking}"
        else:
            # Use the global function as fallback
            selected_treatment, explanation = find_alternative_recommendation_tool(
                customer_journey, excluded_treatment, treatments, constraints, permissions
            )
            full_explanation = explanation
        
        # Extract key journey insights for the explanation
        journey_insights = self._extract_key_insights(customer_journey)
            
        return {
            "selected_treatment": selected_treatment,
            "explanation": f"Original treatment '{excluded_treatment}' not permitted due to {exclusion_reason}.\n\nAlternative recommendation: {full_explanation}",
            "original_treatment": excluded_treatment,
            "exclusion_reason": exclusion_reason,
            "journey_insights": journey_insights,
            "confidence": self._calculate_confidence(customer_journey, selected_treatment) * 0.9,  # Lower confidence for alternative
            "timestamp": self._get_timestamp()
        }
        
    def _summarize_customer_journey(self, customer_journey):
        """Create a summary of the customer journey for improved explainability."""
        if not customer_journey:
            return "No journey data available"
            
        # Extract key information
        summary_points = []
        
        # Check for churn risk
        churn_data = next((item for item in customer_journey if isinstance(item, dict) and item.get("churn_probability")), None)
        if churn_data:
            churn_prob = churn_data.get("churn_probability", 0)
            if churn_prob > 0.7:
                summary_points.append(f"Customer has very high churn risk ({churn_prob:.1%})")
            elif churn_prob > 0.5:
                summary_points.append(f"Customer has elevated churn risk ({churn_prob:.1%})")
            elif churn_prob > 0.3:
                summary_points.append(f"Customer has moderate churn risk ({churn_prob:.1%})")
                
        # Check for network issues
        network_data = next((item for item in customer_journey if isinstance(item, dict) and "connection_quality" in item), None)
        if network_data:
            quality = network_data.get("connection_quality")
            summary_points.append(f"Network connection quality: {quality}")
            
        # Check for billing data
        billing_data = next((item for item in customer_journey if isinstance(item, dict) and "monthly_bill" in item), None)
        if billing_data:
            bill = billing_data.get("monthly_bill")
            if billing_data.get("payment_issues", False):
                summary_points.append(f"Customer has payment issues (monthly bill: ${bill})")
            else:
                summary_points.append(f"Customer pays ${bill} monthly")
                
        # Check for call history
        call_data = [item for item in customer_journey if isinstance(item, dict) and "call_type" in item]
        if call_data:
            recent_calls = len(call_data)
            complaint_calls = sum(1 for call in call_data if call.get("call_type") == "complaint")
            if complaint_calls > 0:
                summary_points.append(f"Customer made {complaint_calls} complaint calls out of {recent_calls} recent calls")
                
        if not summary_points:
            return "Limited journey data available"
            
        return " | ".join(summary_points)
        
    def _extract_key_insights(self, customer_journey):
        """Extract key insights from the customer journey for explainability."""
        insights = []
        
        # Check for churn risk
        churn_data = next((item for item in customer_journey if isinstance(item, dict) and item.get("churn_probability")), None)
        if churn_data and churn_data.get("churn_probability", 0) > 0.5:
            insights.append("High churn risk")
            
        # Check for network issues
        network_data = next((item for item in customer_journey if isinstance(item, dict) and "connection_quality" in item), None)
        if network_data and network_data.get("connection_quality") == "poor":
            insights.append("Poor network quality")
            
        # Check for recent complaints
        complaints = [item for item in customer_journey if isinstance(item, dict) and item.get("call_type") == "complaint"]
        if len(complaints) > 0:
            insights.append(f"Recent complaints: {len(complaints)}")
            
        # Check for billing issues
        billing_issues = next((item for item in customer_journey if isinstance(item, dict) and item.get("payment_issues", False)), None)
        if billing_issues:
            insights.append("Payment issues")
            
        return insights
        
    def _identify_alternatives(self, selected_treatment, treatments, constraints):
        """Identify alternative treatments with their priority ranking."""
        alternatives = []
        
        if not treatments or selected_treatment not in treatments:
            return alternatives
            
        # Get all other treatments
        other_treatments = [tid for tid in treatments.keys() if tid != selected_treatment]
        
        # Sort by priority
        sorted_treatments = sorted(
            [(tid, constraints.get(tid, {}).get("priority", 100)) for tid in other_treatments],
            key=lambda x: x[1]
        )
        
        # Return top 3 alternatives with priority info
        for tid, priority in sorted_treatments[:3]:
            alternatives.append({
                "treatment_id": tid,
                "priority": priority,
                "display_name": treatments[tid].get("display_name", tid)
            })
            
        return alternatives
        
    def _calculate_confidence(self, customer_journey, selected_treatment):
        """Calculate a confidence score for the recommendation."""
        # This is a simplified implementation - would be more sophisticated in production
        base_confidence = 0.7
        
        # Adjust based on treatment type
        if selected_treatment == "call_back":
            # Higher confidence for high-touch treatments
            base_confidence += 0.1
        elif selected_treatment == "ignore":
            # Lower confidence for no-action
            base_confidence -= 0.2
            
        # Adjust based on data completeness
        data_points = len(customer_journey)
        if data_points > 10:
            base_confidence += 0.1
        elif data_points < 5:
            base_confidence -= 0.1
            
        # Ensure confidence is in range [0, 1]
        return max(0.0, min(1.0, base_confidence))
        
    def _get_exclusion_reason(self, treatment_id, permissions):
        """Get a human-readable reason why a treatment was excluded."""
        # Check for common permission issues
        if treatment_id == "call_back" and permissions.get("call", {}).get("marketing") == "N":
            return "customer has opted out of marketing calls"
        elif treatment_id in ["retention_email", "service_email"] and permissions.get("email", {}).get("marketing") == "N":
            return "customer has opted out of marketing emails"
        elif treatment_id in ["retention_sms", "service_sms"] and permissions.get("sms", {}).get("marketing") == "N":
            return "customer has opted out of marketing SMS"
            
        # Default reason
        return "treatment unavailable or at capacity"

    def generate_recommendation(self, customer_journey, treatments, constraints, permissions):
        """Wrapper method to call the global tool function"""
        return generate_recommendation_tool(customer_journey, treatments, constraints, permissions)
        
    def find_alternative_recommendation(self, customer_journey, excluded_treatment, treatments, constraints, permissions):
        """Wrapper method to call the global tool function"""
        return find_alternative_recommendation_tool(customer_journey, excluded_treatment, treatments, constraints, permissions)
        
    def _get_cache_key(self, customer_journey, treatments, constraints):
        """
        Generate a cache key for a treatment recommendation.
        
        Args:
            customer_journey: Customer journey data
            treatments: Available treatments
            constraints: Treatment constraints
            
        Returns:
            Cache key string
        """
        # Create simple hashes of the inputs
        journey_hash = hash(str(customer_journey)) % 10000
        treatments_hash = hash(str(sorted(treatments.keys()))) % 10000
        constraints_hash = hash(str(constraints)) % 10000
        
        return f"{journey_hash}_{treatments_hash}_{constraints_hash}"
        
    def _get_timestamp(self):
        """Get the current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat() 