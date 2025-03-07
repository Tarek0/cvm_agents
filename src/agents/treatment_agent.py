"""
Treatment Recommendation Agent for the CVM multi-agent system.
Specializes in determining optimal treatments for customers.
"""
from src.agents.base_agent import BaseAgent
from smolagents import CodeAgent, LiteLLMModel
import json
import os

class TreatmentAgent(BaseAgent):
    """
    Agent responsible for recommending customer treatments.
    
    This agent uses LLMs to analyze customer data and recommend
    the most appropriate treatment based on business rules and constraints.
    """
    def __init__(self, config=None):
        super().__init__("treatment_agent", config)
        config = config or {}
        model_id = config.get("model_id", os.environ.get("MODEL_ID", "gpt-4o"))
        self.model = LiteLLMModel(model_id=model_id)
        self.agent = CodeAgent(
            tools=[], 
            model=self.model,
            additional_authorized_imports=['datetime'],
            planning_interval=3
        )
        self.recommendation_cache = {}
        self.cache_enabled = config.get("enable_cache", True)
        self.log("info", f"Treatment Agent initialized with model {model_id}")
    
    def process(self, message):
        """
        Process treatment-related requests.
        
        Supported message types:
        - recommend_treatment: Recommend treatment based on customer journey
        - find_alternative: Find alternative treatment when primary is unavailable
        
        Args:
            message (dict): Request message
            
        Returns:
            dict: Response with treatment recommendation or error
        """
        msg_type = message.get("type")
        
        if msg_type == "recommend_treatment":
            return self.recommend_treatment(
                message.get("customer_journey"),
                message.get("treatments"),
                message.get("constraints"),
                message.get("permissions", {})
            )
        elif msg_type == "find_alternative":
            return self.find_alternative_treatment(
                message.get("customer_journey"),
                message.get("excluded_treatment"),
                message.get("treatments"),
                message.get("constraints"),
                message.get("permissions", {})
            )
        else:
            self.log("warning", f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}
    
    def recommend_treatment(self, customer_journey, treatments, constraints, permissions):
        """
        Recommend treatment based on customer journey.
        
        Args:
            customer_journey (list): Customer journey data
            treatments (dict): Available treatments
            constraints (dict): Treatment constraints
            permissions (dict): Customer permissions
            
        Returns:
            dict: Treatment recommendation
        """
        # Check required inputs
        if not customer_journey:
            self.log("error", "No customer journey data provided")
            return {"error": "No customer journey data provided"}
            
        if not treatments:
            self.log("error", "No treatments provided")
            return {"error": "No treatments provided"}
            
        # Check cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(customer_journey, treatments, constraints)
            if cache_key in self.recommendation_cache:
                self.log("info", "Using cached recommendation")
                return self.recommendation_cache[cache_key]
        
        # Format customer journey for prompt
        journey_str = json.dumps(customer_journey, indent=2)
        
        # Format permissions for prompt
        permission_rules = self._format_permissions(permissions)
        
        # Create prompt
        prompt = f"""
        You are a Marketing Manager for a telecom company.
        Based on this customer's profile and interactions:
        {journey_str}
        
        {permission_rules}
        
        IMPORTANT BUSINESS RULES:
        1. You MUST NOT recommend treatments that violate the customer's contact permissions
        2. You MUST NOT recommend email treatments if email marketing is not allowed
        3. You MUST NOT recommend SMS treatments if SMS marketing is not allowed
        4. You MUST NOT recommend call treatments if call marketing is not allowed
        5. You MUST respect the customer's preferred contact time and do not disturb hours
        6. You MUST use the customer's preferred language for communications
        7. If a channel's marketing permission is "N", you cannot use that channel for marketing communications
        
        What is the best CVM treatment out of the below options to improve the customer's Life Time Value?

        Available CVM Treatments: {json.dumps(treatments, indent=2)}
        CVM Treatments are subject to the following constraints: {json.dumps(constraints, indent=2)}.

        Your response MUST be a valid JSON object with exactly the following schema:
        {{
            "selected_treatment": <treatment_key>,
            "explanation": <explanation>
        }}
        
        In your explanation, explicitly state how the selected treatment complies with the customer's permissions.
        If no compliant treatments are available, return "ignore" as the selected_treatment.
        """
        
        # Get recommendation from LLM
        self.log("info", "Requesting treatment recommendation from LLM")
        response = self.agent.run(prompt)
        self.log("debug", f"LLM response: {response}")
        
        try:
            if isinstance(response, str):
                response = json.loads(response)
            if not isinstance(response, dict) or 'selected_treatment' not in response:
                raise ValueError("Invalid response format from agent")
                
            # Store in cache if enabled
            if self.cache_enabled:
                cache_key = self._get_cache_key(customer_journey, treatments, constraints)
                self.recommendation_cache[cache_key] = response
                
            return response
            
        except json.JSONDecodeError as e:
            self.log("error", f"Failed to parse agent response as JSON: {str(e)}")
            return {"error": f"Invalid JSON response from agent: {str(e)}"}
        except Exception as e:
            self.log("error", f"Error processing recommendation: {str(e)}")
            return {"error": f"Error processing recommendation: {str(e)}"}
    
    def find_alternative_treatment(self, customer_journey, excluded_treatment, treatments, constraints, permissions):
        """
        Find an alternative treatment when the primary choice is not available.
        
        Args:
            customer_journey (list): Customer journey data
            excluded_treatment (str): Treatment to exclude
            treatments (dict): Available treatments
            constraints (dict): Treatment constraints
            permissions (dict): Customer permissions
            
        Returns:
            dict: Alternative treatment recommendation
        """
        if not customer_journey:
            self.log("error", "No customer journey data provided")
            return {"error": "No customer journey data provided"}
        
        # Filter available treatments
        filtered_treatments = {
            k: v for k, v in treatments.items() 
            if k != excluded_treatment and constraints.get(k, {}).get("remaining_availability", 0) > 0
        }
        
        if not filtered_treatments:
            self.log("info", "No alternative treatments available")
            return {
                "selected_treatment": "ignore",
                "explanation": "No alternative treatments available, defaulting to no action"
            }
        
        # Format customer journey for prompt
        journey_str = json.dumps(customer_journey, indent=2)
        
        # Format permissions for prompt
        permission_rules = self._format_permissions(permissions)
        
        # Create prompt for alternative treatment
        prompt = f"""
        You are a Marketing Manager for a telecom company.
        Based on this customer's profile and interactions:
        {journey_str}
        
        {permission_rules}
        
        The originally recommended treatment "{excluded_treatment}" is not available.
        
        IMPORTANT BUSINESS RULES:
        1. You MUST NOT recommend treatments that violate the customer's contact permissions
        2. You MUST NOT recommend email treatments if email marketing is not allowed
        3. You MUST NOT recommend SMS treatments if SMS marketing is not allowed
        4. You MUST NOT recommend call treatments if call marketing is not allowed
        5. You MUST respect the customer's preferred contact time and do not disturb hours
        6. You MUST use the customer's preferred language for communications
        7. If a channel's marketing permission is "N", you cannot use that channel for marketing communications
        
        What is the best ALTERNATIVE CVM treatment out of the below options?

        Available CVM Treatments: {json.dumps(filtered_treatments, indent=2)}
        CVM Treatments are subject to the following constraints: {json.dumps(constraints, indent=2)}.

        Your response MUST be a valid JSON object with exactly the following schema:
        {{
            "selected_treatment": <treatment_key>,
            "explanation": <explanation>
        }}
        
        In your explanation, explicitly state how the selected treatment complies with the customer's permissions and why it's a good alternative.
        If no compliant treatments are available, return "ignore" as the selected_treatment.
        """
        
        # Get recommendation from LLM
        self.log("info", "Requesting alternative treatment recommendation from LLM")
        response = self.agent.run(prompt)
        self.log("debug", f"LLM response: {response}")
        
        try:
            if isinstance(response, str):
                response = json.loads(response)
            if not isinstance(response, dict) or 'selected_treatment' not in response:
                raise ValueError("Invalid response format from agent")
                
            return response
            
        except json.JSONDecodeError as e:
            self.log("error", f"Failed to parse agent response as JSON: {str(e)}")
            return {"error": f"Invalid JSON response from agent: {str(e)}"}
        except Exception as e:
            self.log("error", f"Error processing recommendation: {str(e)}")
            return {"error": f"Error processing recommendation: {str(e)}"}
    
    def _format_permissions(self, permissions):
        """
        Convert permissions to business rules format.
        
        Args:
            permissions (dict): Customer permissions
            
        Returns:
            str: Formatted permissions rules
        """
        if not permissions:
            return ""
        
        return f"""
        CUSTOMER PERMISSIONS:
        - Preferred contact time: {permissions.get('preferred_contact_time', 'any')}
        - Preferred language: {permissions.get('preferred_language', 'en')}
        - Do not disturb hours: {permissions.get('do_not_disturb', 'none')}
        - Email marketing allowed: {permissions.get('permissions', {}).get('email', {}).get('marketing', 'Y')}
        - SMS marketing allowed: {permissions.get('permissions', {}).get('sms', {}).get('marketing', 'Y')}
        - Call marketing allowed: {permissions.get('permissions', {}).get('call', {}).get('marketing', 'Y')}
        """
    
    def _get_cache_key(self, customer_journey, treatments, constraints):
        """
        Generate a cache key for a recommendation request.
        
        Args:
            customer_journey (list): Customer journey data
            treatments (dict): Available treatments
            constraints (dict): Treatment constraints
            
        Returns:
            str: Cache key
        """
        # Extract customer ID
        customer_id = None
        if customer_journey and isinstance(customer_journey, list) and customer_journey:
            for event in customer_journey:
                if isinstance(event, dict) and 'customer_id' in event:
                    customer_id = event['customer_id']
                    break
        
        # Get constraint availability snapshot
        avail_snapshot = {k: v.get('remaining_availability', 0) for k, v in constraints.items()}
        
        # Create a deterministic string representation
        key_components = [
            f"cid:{customer_id}",
            f"journey_len:{len(customer_journey)}",
            f"avail:{json.dumps(avail_snapshot, sort_keys=True)}"
        ]
        
        return "_".join(key_components) 