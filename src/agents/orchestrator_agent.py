"""
Orchestration Agent for the CVM multi-agent system.
Coordinates the workflow between specialized agents.
"""
from src.agents.base_agent import BaseAgent
from src.agents.data_agent import DataAgent
from src.agents.journey_agent import JourneyAgent
from src.agents.treatment_agent import TreatmentAgent
from src.agents.allocation_agent import AllocationAgent
from src.agents.trigger_agent import TriggerAgent
from src.utils.config import load_config
from src.utils.treatment_manager import TreatmentManager

import os
import json
import logging
from datetime import datetime

class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for orchestrating the entire CVM workflow.
    
    This agent coordinates the data flow between specialized agents
    and manages the overall treatment selection process.
    """
    
    def __init__(self, config=None):
        """
        Initialize the OrchestratorAgent.
        
        Args:
            config: Configuration object, loaded from default if not provided
        """
        super().__init__("Orchestrator", config)
        
        # Load config
        self.config = config or load_config()
        
        # Initialize treatment manager
        self.treatment_manager = TreatmentManager(self.config)
        
        # Initialize sub-agents
        self.data_agent = DataAgent(self.config)
        self.journey_agent = JourneyAgent(self.config)
        self.treatment_agent = TreatmentAgent(self.config)
        self.allocation_agent = AllocationAgent(self.config)
        self.trigger_agent = TriggerAgent(self.config)
        
        self.log("INFO", "OrchestratorAgent initialized with all sub-agents")

    def process(self, message):
        """
        Process orchestration requests.
        
        Supported message types:
        - process_customer: Process a single customer
        - process_customer_with_treatment: Process a customer with a specific treatment
        - process_batch: Process multiple customers
        - trigger_customers: Trigger customers based on criteria
        - add_treatment: Add a new custom treatment
        - update_treatment: Update an existing custom treatment
        - remove_treatment: Remove a custom treatment
        - list_treatments: List all custom treatments
        - list_triggers: List all triggers
        
        Args:
            message: Message containing the request details
            
        Returns:
            Processing result based on message type
        """
        if isinstance(message, dict):
            message_type = message.get("type", "")
            
            if message_type == "process_customer":
                customer_id = message.get("customer_id")
                # Get optional allowed_treatments parameter
                allowed_treatments = message.get("allowed_treatments", None)
                if customer_id:
                    return self.process_customer(customer_id, allowed_treatments=allowed_treatments)
                else:
                    self.log("ERROR", "Missing customer_id in process_customer request")
                    return {"status": "error", "message": "Missing customer_id"}
            
            elif message_type == "process_customer_with_treatment":
                customer_id = message.get("customer_id")
                treatment_id = message.get("treatment_id")
                if customer_id and treatment_id:
                    return self.process_customer_with_treatment(customer_id, treatment_id)
                else:
                    self.log("ERROR", "Missing customer_id or treatment_id in process_customer_with_treatment request")
                    return {"status": "error", "message": "Missing customer_id or treatment_id"}
            
            elif message_type == "process_batch":
                customer_ids = message.get("customer_ids")
                treatment_id = message.get("treatment_id")
                # Get optional allowed_treatments parameter
                allowed_treatments = message.get("allowed_treatments", None)
                if customer_ids:
                    return self.process_batch(customer_ids, treatment_id, allowed_treatments=allowed_treatments)
                else:
                    self.log("ERROR", "Missing customer_ids in process_batch request")
                    return {"status": "error", "message": "Missing customer_ids"}
            
            elif message_type == "trigger_customers":
                # Delegate to trigger agent
                return self.trigger_agent.process(message)
            
            elif message_type == "trigger_and_process":
                # Trigger customers and then process them with a specific treatment
                customer_ids = message.get("customer_ids")
                trigger_type = message.get("trigger_type")
                custom_trigger = message.get("custom_trigger", {})
                treatment_id = message.get("treatment_id")
                
                if not all([customer_ids, trigger_type, treatment_id]):
                    self.log("ERROR", "Missing required parameters in trigger_and_process request")
                    return {"status": "error", "message": "Missing customer_ids, trigger_type, or treatment_id"}
                
                # First trigger the customers
                trigger_result = self.trigger_agent.process({
                    "type": "trigger_customers",
                    "customer_ids": customer_ids,
                    "trigger_type": trigger_type,
                    "custom_trigger": custom_trigger
                })
                
                if trigger_result.get("status") != "success":
                    return trigger_result
                
                # Get matching customer IDs
                matching_ids = [match.get("customer_id") for match in trigger_result.get("matches", [])]
                
                if not matching_ids:
                    return {
                        "status": "success",
                        "message": "No customers matched the trigger criteria",
                        "matches": 0,
                        "processed": 0,
                        "trigger_results": trigger_result
                    }
                
                # Process each matching customer with the specified treatment
                process_results = []
                for customer_id in matching_ids:
                    result = self.process_customer_with_treatment(customer_id, treatment_id)
                    process_results.append(result)
                
                # Return combined results
                return {
                    "status": "success",
                    "matches": len(matching_ids),
                    "processed": len(process_results),
                    "trigger_results": trigger_result,
                    "process_results": process_results
                }
            
            elif message_type == "add_treatment":
                text_input = message.get("description")
                treatment_id = message.get("treatment_id")
                if text_input:
                    try:
                        treatment_id, treatment = self.treatment_manager.add_custom_treatment(
                            text_input, treatment_id
                        )
                        return {
                            "status": "success", 
                            "treatment_id": treatment_id,
                            "treatment": treatment
                        }
                    except Exception as e:
                        self.log("ERROR", f"Failed to add custom treatment: {e}")
                        return {"status": "error", "message": str(e)}
                else:
                    self.log("ERROR", "Missing description in add_treatment request")
                    return {"status": "error", "message": "Missing treatment description"}
            
            elif message_type == "update_treatment":
                treatment_id = message.get("treatment_id")
                text_input = message.get("description")
                if treatment_id and text_input:
                    try:
                        treatment_id, treatment = self.treatment_manager.update_custom_treatment(
                            treatment_id, text_input
                        )
                        return {
                            "status": "success", 
                            "treatment_id": treatment_id,
                            "treatment": treatment
                        }
                    except Exception as e:
                        self.log("ERROR", f"Failed to update custom treatment: {e}")
                        return {"status": "error", "message": str(e)}
                else:
                    self.log("ERROR", "Missing treatment_id or description in update_treatment request")
                    return {"status": "error", "message": "Missing treatment_id or description"}
            
            elif message_type == "remove_treatment":
                treatment_id = message.get("treatment_id")
                if treatment_id:
                    success = self.treatment_manager.remove_custom_treatment(treatment_id)
                    if success:
                        return {"status": "success", "message": f"Treatment {treatment_id} removed"}
                    else:
                        return {"status": "error", "message": f"Treatment {treatment_id} not found"}
                else:
                    self.log("ERROR", "Missing treatment_id in remove_treatment request")
                    return {"status": "error", "message": "Missing treatment_id"}
            
            elif message_type == "list_treatments":
                custom_only = message.get("custom_only", False)
                if custom_only:
                    treatments = self.treatment_manager.list_custom_treatments()
                else:
                    treatments = [
                        {"id": k, **v} 
                        for k, v in self.treatment_manager.get_all_treatments().items()
                    ]
                return {"status": "success", "treatments": treatments}
            
            elif message_type == "list_triggers":
                # Delegate to trigger agent
                return self.trigger_agent.process(message)
            
            elif message_type == "get_treatment_help":
                return {
                    "status": "success",
                    "help_text": self.treatment_manager.get_treatment_help()
                }
            
            elif message_type == "process_customers":
                return self._handle_batch_customers(message)
            
            else:
                self.log("WARNING", f"Unknown message type: {message_type}")
                return {"status": "error", "message": f"Unknown message type: {message_type}"}
        else:
            self.log("ERROR", f"Invalid message format: {type(message)}")
            return {"status": "error", "message": "Invalid message format"}

    def process_customer(self, customer_id, treatment_id=None, allowed_treatments=None):
        """
        Process a single customer through the multi-agent workflow.
        
        Args:
            customer_id: ID of the customer to process
            treatment_id: Specific treatment ID to use (optional)
            allowed_treatments: Optional list of treatment IDs to limit selection to
            
        Returns:
            Processing result
        """
        try:
            self.log("INFO", f"Processing customer {customer_id}")
            
            # 1. Data Collection
            # Get customer data using the data agent
            data_response = self.data_agent.process({
                "type": "get_customer_data",
                "customer_id": customer_id
            })
            
            if "error" in data_response:
                return {
                    "customer_id": customer_id,
                    "status": "error",
                    "message": data_response["error"]
                }
                
            customer_data = data_response.get("customer_data", [])
            
            # 2. Journey Analysis
            # Use the journey agent to analyze the customer journey
            journey_response = self.journey_agent.process({
                "type": "build_journey",
                "customer_data": customer_data,
                "customer_id": customer_id
            })
            
            if "error" in journey_response:
                return {
                    "customer_id": customer_id,
                    "status": "error",
                    "message": journey_response["error"]
                }
                
            customer_journey = journey_response.get("journey", [])
            
            # 3. Get Customer Permissions
            # Get latest permissions
            permissions = self._get_customer_permissions(customer_id)
            
            # 4. Treatment Selection (Either recommended or specific)
            if treatment_id:
                # If a specific treatment was requested, use it (after filtering)
                available_treatments = self._get_treatments(allowed_treatments)
                
                # Ensure the requested treatment is available
                if treatment_id in available_treatments:
                    treatment = available_treatments[treatment_id]
                    if not treatment.get("enabled", True):
                        return {
                            "customer_id": customer_id,
                            "status": "error",
                            "message": f"Treatment {treatment_id} is disabled"
                        }
                        
                    treatment_result = {
                        "selected_treatment": treatment_id,
                        "explanation": f"Treatment {treatment_id} was specifically requested",
                        "confidence": 1.0,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "customer_id": customer_id,
                        "status": "error",
                        "message": f"Treatment {treatment_id} is not available"
                    }
            else:
                # Use the treatment agent to recommend an optimal treatment
                available_treatments = self._get_treatments(allowed_treatments)
                
                # Get the treatment constraints
                constraints = self.config.constraints
                
                # Find which treatments are available based on capacity
                available_after_capacity = {}
                for tid, details in available_treatments.items():
                    # Check allocation availability
                    check_response = self.allocation_agent.process({
                        "type": "check_availability",
                        "treatment_key": tid
                    })
                    
                    if check_response.get("status") == "success" and check_response.get("available", False):
                        # Treatment is available
                        available_after_capacity[tid] = details
                    else:
                        # Treatment is unavailable or at capacity
                        self.log("INFO", f"Treatment {tid} is unavailable or at capacity for today (max_per_day constraint)")
                    
                if not available_after_capacity:
                    return {
                        "customer_id": customer_id,
                        "status": "error",
                        "message": "No treatments available (all at capacity or disabled)"
                    }
                    
                # Get treatment recommendation
                recommendation_response = self.treatment_agent.process({
                    "type": "recommend_treatment",
                    "journey": customer_journey,
                    "treatments": available_after_capacity,
                    "constraints": constraints,
                    "permissions": permissions
                })
                
                # Check if the recommended treatment is permitted based on permissions
                recommended_treatment = recommendation_response.get("selected_treatment")
                treatment_result = recommendation_response
                
                # Verify treatment permissions
                needs_alternative = False
                if recommended_treatment != "ignore":
                    # Get the treatment's channel and type
                    channel, msg_type = self._get_treatment_channel_type(recommended_treatment)
                    
                    # Check if permission is granted
                    permission_granted = self._check_permission(
                        customer_id, permissions, channel, msg_type, 
                        treatment_id=recommended_treatment
                    )
                    
                    if not permission_granted:
                        needs_alternative = True
                
                # Find alternative if needed
                if needs_alternative:
                    self.log("INFO", f"Finding alternative to {recommended_treatment}")
                    
                    alternative_response = self.treatment_agent.process({
                        "type": "find_alternative",
                        "journey": customer_journey,
                        "excluded_treatment": recommended_treatment,
                        "treatments": available_after_capacity,
                        "constraints": constraints,
                        "permissions": permissions
                    })
                    
                    treatment_result = alternative_response
            
            # 5. Treatment Allocation
            selected_treatment = treatment_result.get("selected_treatment")
            
            # Skip allocation for "ignore" treatment
            if selected_treatment != "ignore":
                # Allocate the selected treatment
                allocation_response = self.allocation_agent.process({
                    "type": "allocate_resource",
                    "treatment_key": selected_treatment,
                    "customer_id": customer_id
                })
                
                if allocation_response.get("status") != "success":
                    # If allocation fails, try to fall back to "ignore"
                    return {
                        "customer_id": customer_id,
                        "status": "error",
                        "message": f"Failed to allocate treatment: {allocation_response.get('message', 'Unknown error')}"
                    }
                    
                # Add allocation details to the result
                treatment_result["allocation"] = {
                    "timestamp": allocation_response.get("timestamp"),
                    "remaining": allocation_response.get("remaining"),
                    "max_per_day": allocation_response.get("max_per_day")
                }
            
            # 6. Prepare result
            # Create the final result with full details from treatment_result
            result = {
                "customer_id": customer_id,
                "selected_treatment": selected_treatment,
                "explanation": treatment_result.get("explanation", ""),
                "timestamp": treatment_result.get("timestamp", datetime.now().isoformat()),
                "status": "success"
            }
            
            # Include additional explainability fields if available
            if "journey_insights" in treatment_result:
                result["journey_insights"] = treatment_result["journey_insights"]
                
            if "customer_journey_summary" in treatment_result:
                result["journey_summary"] = treatment_result["customer_journey_summary"]
                
            if "confidence" in treatment_result:
                result["confidence"] = treatment_result["confidence"]
                
            if "alternative_treatments" in treatment_result:
                result["alternative_treatments"] = treatment_result["alternative_treatments"]
                
            if "exclusion_reason" in treatment_result:
                result["exclusion_reason"] = treatment_result["exclusion_reason"]
            
            return result
                
        except Exception as e:
            self.log("ERROR", f"Error processing customer {customer_id}: {str(e)}")
            return {
                "customer_id": customer_id,
                "status": "error",
                "message": str(e)
            }

    def process_customer_with_treatment(self, customer_id, treatment_id):
        """
        Process a customer with a specific treatment, bypassing recommendation logic.
        
        Args:
            customer_id: ID of the customer to process
            treatment_id: ID of the treatment to apply
            
        Returns:
            Processing result
        """
        self.log("INFO", f"Processing customer {customer_id} with forced treatment {treatment_id}")
        
        # Step 1: Get customer data from Data Agent
        customer_data_response = self.data_agent.process({
            "type": "get_customer_data",
            "customer_id": customer_id
        })
        
        if not customer_data_response or "customer_data" not in customer_data_response:
            self.log("ERROR", f"Failed to get data for customer {customer_id}")
            return {
                "customer_id": customer_id,
                "status": "error",
                "message": "Failed to retrieve customer data",
                "timestamp": datetime.now().isoformat()
            }
        
        customer_data = customer_data_response["customer_data"]
        
        # Step 2: Build customer journey using Journey Agent (still needed for context)
        journey_response = self.journey_agent.process({
            "type": "build_journey",
            "customer_id": customer_id,
            "customer_data": customer_data
        })
        
        if not journey_response or "journey" not in journey_response:
            self.log("ERROR", f"Failed to build journey for customer {customer_id}")
            return {
                "customer_id": customer_id,
                "status": "error",
                "message": "Failed to build customer journey",
                "timestamp": datetime.now().isoformat()
            }
        
        # Step 3: Get customer permissions 
        permissions = self._get_customer_permissions(customer_id)
        
        # Get treatment details
        treatments = self.treatment_manager.get_all_treatments()
        if treatment_id not in treatments:
            self.log("ERROR", f"Treatment {treatment_id} not found")
            return {
                "customer_id": customer_id,
                "status": "error",
                "message": f"Treatment {treatment_id} not found",
                "timestamp": datetime.now().isoformat()
            }
        
        selected_treatment = treatments[treatment_id]
        
        # Step 4: Check if the customer has the necessary permissions for this treatment
        has_permission = self._validate_treatment_permission(customer_id, treatment_id, selected_treatment, permissions)
        
        if not has_permission:
            self.log("WARNING", f"Customer {customer_id} does not have permission for treatment {treatment_id}")
            return {
                "customer_id": customer_id,
                "status": "error",
                "selected_treatment": selected_treatment,
                "explanation": f"Customer does not have permission for treatment {treatment_id} ({selected_treatment.get('display_name', 'Unknown')})",
                "timestamp": datetime.now().isoformat()
            }
        
        # Step 5: Allocate resources
        allocation_response = self.allocation_agent.process({
            "type": "allocate_resource",
            "treatment_key": treatment_id,
            "customer_id": customer_id
        })
        
        if not allocation_response or allocation_response.get("status") != "success":
            return {
                "customer_id": customer_id,
                "selected_treatment": selected_treatment,
                "status": "error",
                "explanation": f"Unable to allocate resources for treatment {treatment_id}",
                "allocation_error": allocation_response.get("message", "Resource allocation failed"),
                "timestamp": datetime.now().isoformat()
            }
        
        # Step 6: Return the result
        return {
            "customer_id": customer_id,
            "selected_treatment": selected_treatment,
            "explanation": f"Treatment {treatment_id} ({selected_treatment.get('display_name', 'Unknown')}) applied by direct selection",
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    def _validate_treatment_permission(self, customer_id, treatment_id, treatment, permissions):
        """
        Validate if a customer has permission for a specific treatment.
        
        Args:
            customer_id: ID of the customer
            treatment_id: ID of the treatment
            treatment: Treatment details
            permissions: Customer permissions
            
        Returns:
            Boolean indicating if the customer has permission
        """
        # Default channel and type values based on treatment ID patterns
        channel = treatment.get("channel", "unknown")
        treatment_type = treatment.get("type", "unknown")
        
        # Extract channel and type from treatment if not explicitly defined
        if "email" in treatment_id or any(term in treatment.get("description", "").lower() for term in ["email", "mail"]):
            channel = "email"
        elif "sms" in treatment_id or any(term in treatment.get("description", "").lower() for term in ["sms", "text", "message"]):
            channel = "sms"
        elif "call" in treatment_id or any(term in treatment.get("description", "").lower() for term in ["call", "phone", "callback"]):
            channel = "call"
            
        if "offer" in treatment_id or any(term in treatment.get("description", "").lower() for term in ["offer", "promotion", "discount", "marketing"]):
            treatment_type = "marketing"
        elif "service" in treatment_id or any(term in treatment.get("description", "").lower() for term in ["service", "support", "help"]):
            treatment_type = "service"
        
        # Log for debugging
        self.log("INFO", f"Checking permissions for customer {customer_id}: treatment={treatment_id}, channel={channel}, type={treatment_type}")
        
        # Get permissions
        customer_permissions = permissions.get("permissions", {})
        
        # Special case for "ignore" treatment - always allowed
        if treatment_id == "ignore":
            return True
            
        # Check permission based on channel and type
        if channel == "email":
            if treatment_type == "marketing" and customer_permissions.get("email", {}).get("marketing") != "Y":
                return False
            if treatment_type == "service" and customer_permissions.get("email", {}).get("service") != "Y":
                return False
        elif channel == "sms":
            if treatment_type == "marketing" and customer_permissions.get("sms", {}).get("marketing") != "Y":
                return False
            if treatment_type == "service" and customer_permissions.get("sms", {}).get("service") != "Y":
                return False
        elif channel == "call":
            if treatment_type == "marketing" and customer_permissions.get("call", {}).get("marketing") != "Y":
                return False
            if treatment_type == "service" and customer_permissions.get("call", {}).get("service") != "Y":
                return False
                
        # If no specific permission check failed, and we have at least basic permissions, allow the treatment
        if not customer_permissions:
            self.log("WARNING", f"No permissions found for customer {customer_id}, defaulting to restricted")
            return False
            
        return True

    def process_batch(self, customer_ids, treatment_id=None, allowed_treatments=None):
        """
        Process a batch of customers.
        
        Args:
            customer_ids: List of customer IDs to process
            treatment_id: Optional treatment ID to apply to all customers
            allowed_treatments: Optional list of treatment IDs to limit selection to
            
        Returns:
            Dictionary of results keyed by customer ID
        """
        self.log("INFO", f"Processing batch of {len(customer_ids)} customers" + 
                (f" with treatment {treatment_id}" if treatment_id else ""))
        if allowed_treatments:
            self.log("INFO", f"Limiting treatment selection to: {allowed_treatments}")
        
        results = []
        for customer_id in customer_ids:
            try:
                if treatment_id:
                    # Use the specified treatment
                    result = self.process_customer_with_treatment(customer_id, treatment_id)
                else:
                    # Use automatic treatment selection with allowed treatments
                    result = self.process_customer(customer_id, allowed_treatments=allowed_treatments)
                results.append(result)
            except Exception as e:
                self.log("ERROR", f"Error processing customer {customer_id}: {str(e)}")
                results.append({
                    "customer_id": customer_id,
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # Return summary with results
        return results
            
    def _get_customer_permissions(self, customer_id):
        """
        Get latest customer permissions from the data agent.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Permissions dictionary or empty dict if not found
        """
        try:
            # Use data agent to get latest permissions
            permissions_response = self.data_agent.process({
                "type": "get_customer_permissions",
                "customer_id": customer_id
            })
            
            if permissions_response and "permissions" in permissions_response:
                return permissions_response
                
            self.log("warning", f"No permissions found for customer {customer_id}")
            return {}
            
        except Exception as e:
            self.log("error", f"Error loading permissions for customer {customer_id}: {str(e)}")
            return {}

    def _handle_batch_customers(self, message):
        """Handle batch processing of multiple customers"""
        customer_ids = message.get("customer_ids", "").split(",")
        # Get allowed_treatments if provided
        allowed_treatments = message.get("allowed_treatments", None)
        results = []

        for customer_id in customer_ids:
            try:
                # Process each customer using the process_customer method with allowed_treatments
                result = self.process_customer(
                    customer_id.strip(), 
                    allowed_treatments=allowed_treatments
                )
                
                # Add customer_id to the result for tracking if not already there
                if isinstance(result, dict) and "customer_id" not in result:
                    result["customer_id"] = customer_id
                
                results.append(result)

            except Exception as e:
                results.append({
                    "customer_id": customer_id,
                    "status": "error",
                    "message": str(e)
                })

        return results 

    def _get_treatments(self, allowed_treatments=None):
        """
        Get available treatments, filtered by the allowed_treatments parameter if provided.
        
        Args:
            allowed_treatments: Optional list of treatment IDs to limit selection to
            
        Returns:
            Dictionary of available treatments
        """
        # Get all treatments from the configuration
        all_treatments = self.config.treatments
        
        # Filter by allowed_treatments if provided
        if allowed_treatments:
            # Only include treatments that are in the allowed list and are enabled
            filtered_treatments = {
                tid: treatment for tid, treatment in all_treatments.items()
                if tid in allowed_treatments and treatment.get("enabled", True)
            }
            return filtered_treatments
        else:
            # Include all enabled treatments
            return {
                tid: treatment for tid, treatment in all_treatments.items()
                if treatment.get("enabled", True)
            } 

    def _get_treatment_channel_type(self, treatment_id):
        """
        Determine the channel and message type of a treatment.
        
        Args:
            treatment_id: Treatment ID
            
        Returns:
            Tuple of (channel, message_type)
        """
        # Map treatments to their channels and types
        treatment_mapping = {
            "call_back": ("call", "marketing"),
            "retention_email": ("email", "marketing"),
            "retention_sms": ("sms", "marketing"),
            "service_sms": ("sms", "service"),
            "loyalty_app": ("app", "marketing"),
            "ignore": (None, None)
        }
        
        # Look up the treatment or default to None, None
        return treatment_mapping.get(treatment_id, (None, None))
        
    def _check_permission(self, customer_id, permissions, channel, msg_type, treatment_id=None):
        """
        Check if a customer has granted permission for a certain type of communication.
        
        Args:
            customer_id: Customer ID
            permissions: Permissions dictionary
            channel: Communication channel (email, sms, call)
            msg_type: Message type (marketing, service)
            treatment_id: Optional treatment ID for logging
            
        Returns:
            Boolean indicating if permission is granted
        """
        if not permissions or not channel or not msg_type:
            return True  # Default to allowing if no permission data
            
        # Check if the channel permission exists
        if channel in permissions:
            # Check if the specific message type permission exists
            if msg_type in permissions[channel]:
                # Check if permission is granted (Y) or denied (N)
                has_permission = permissions[channel][msg_type] == "Y"
                
                if not has_permission:
                    self.log("WARNING", f"Customer {customer_id} does not have permission for recommended treatment {treatment_id}")
                
                return has_permission
                
        # Default to allowing if permission isn't specified
        return True 