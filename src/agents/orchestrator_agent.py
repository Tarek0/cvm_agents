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
                if customer_id:
                    return self.process_customer(customer_id)
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
                if customer_ids:
                    return self.process_batch(customer_ids)
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
            
            else:
                self.log("WARNING", f"Unknown message type: {message_type}")
                return {"status": "error", "message": f"Unknown message type: {message_type}"}
        else:
            self.log("ERROR", f"Invalid message format: {type(message)}")
            return {"status": "error", "message": "Invalid message format"}

    def process_customer(self, customer_id):
        """
        Process a single customer through the multi-agent workflow.
        
        Args:
            customer_id: ID of the customer to process
            
        Returns:
            Processing result
        """
        self.log("INFO", f"Processing customer {customer_id}")
        
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
        
        # Step 2: Build customer journey using Journey Agent
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
        
        customer_journey = journey_response["journey"]
        
        # Step 3: Get customer permissions
        permissions = self._get_customer_permissions(customer_id)
        
        # Step 4: Get enabled treatments and constraints
        enabled_treatments = self.treatment_manager.get_enabled_treatments()
        constraints = self.treatment_manager.get_all_constraints()
        
        # Step 5: Get treatment recommendation
        treatment_response = self.treatment_agent.process({
            "type": "recommend_treatment",
            "journey": customer_journey,
            "treatments": enabled_treatments,
            "constraints": constraints,
            "permissions": permissions
        })
        
        if not treatment_response or "selected_treatment" not in treatment_response:
            self.log("ERROR", f"Failed to get treatment recommendation for customer {customer_id}")
            return {
                "customer_id": customer_id,
                "status": "error",
                "message": "Failed to determine optimal treatment",
                "timestamp": datetime.now().isoformat()
            }
        
        selected_treatment = treatment_response["selected_treatment"]
        explanation = treatment_response.get("explanation", "")
        
        # Step 6: Allocate resources if needed
        if selected_treatment != "ignore":
            allocation_response = self.allocation_agent.process({
                "type": "allocate_resource",
                "treatment_key": selected_treatment,
                "customer_id": customer_id
            })
            
            # If allocation failed, try to find an alternative treatment
            if not allocation_response or allocation_response.get("status") != "success":
                self.log("WARNING", f"Failed to allocate {selected_treatment} for customer {customer_id}, finding alternative")
                
                # Get alternative treatment
                alternative_response = self.treatment_agent.process({
                    "type": "find_alternative",
                    "journey": customer_journey,
                    "excluded_treatment": selected_treatment,
                    "treatments": enabled_treatments,
                    "constraints": constraints,
                    "permissions": permissions
                })
                
                if alternative_response and "selected_treatment" in alternative_response:
                    selected_treatment = alternative_response["selected_treatment"]
                    explanation = f"{explanation}\n\nOriginal treatment unavailable. Alternative: {alternative_response.get('explanation', '')}"
                    
                    # Try to allocate the alternative
                    if selected_treatment != "ignore":
                        allocation_response = self.allocation_agent.process({
                            "type": "allocate_resource",
                            "treatment_key": selected_treatment,
                            "customer_id": customer_id
                        })
        
        # Step 7: Return the result
        return {
            "customer_id": customer_id,
            "selected_treatment": selected_treatment,
            "explanation": explanation,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
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
        
        # Step 3: Allocate resources
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
        
        # Step 4: Return the result
        return {
            "customer_id": customer_id,
            "selected_treatment": selected_treatment,
            "explanation": f"Treatment {treatment_id} ({selected_treatment.get('display_name', 'Unknown')}) applied by direct selection",
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

    def process_batch(self, customer_ids):
        """
        Process a batch of customers.
        
        Args:
            customer_ids: List of customer IDs to process
            
        Returns:
            Dictionary of results keyed by customer ID
        """
        self.log("INFO", f"Processing batch of {len(customer_ids)} customers")
        
        results = []
        for customer_id in customer_ids:
            try:
                result = self.process_customer(customer_id)
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
        Get customer permissions from the permissions file.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Permissions dictionary or None if not found
        """
        try:
            from src.tools.api_v2 import data_root
            
            permissions_path = os.path.join(data_root, 'permissions.json')
            if not os.path.exists(permissions_path):
                self.log("warning", f"Permissions file not found: {permissions_path}")
                return {}
                
            with open(permissions_path, 'r') as f:
                permissions_data = json.load(f)
                
            for record in permissions_data:
                if record.get("customer_id") == customer_id:
                    return record
                    
            self.log("warning", f"No permissions found for customer {customer_id}")
            return {}
            
        except Exception as e:
            self.log("error", f"Error loading permissions for customer {customer_id}: {str(e)}")
            return {} 