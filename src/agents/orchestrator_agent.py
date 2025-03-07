"""
Orchestration Agent for the CVM multi-agent system.
Coordinates the workflow between specialized agents.
"""
from src.agents.base_agent import BaseAgent
from src.agents.data_agent import DataAgent
from src.agents.journey_agent import JourneyAgent
from src.agents.treatment_agent import TreatmentAgent
from src.agents.allocation_agent import AllocationAgent
from src.utils.config import load_config

import os
import json
import logging
from datetime import datetime

class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for coordinating the workflow between specialized agents.
    
    This agent manages the overall processing pipeline, coordinates
    the flow of information between agents, and handles error recovery.
    """
    def __init__(self, config=None):
        super().__init__("orchestrator_agent", config)
        
        # Load configuration
        self.config = config or {}
        self.system_config = load_config()
        
        # Initialize sub-agents
        self.data_agent = DataAgent(config)
        self.journey_agent = JourneyAgent(config)
        self.treatment_agent = TreatmentAgent(config)
        
        allocation_config = dict(config or {})
        allocation_config["constraints"] = self.system_config.constraints
        self.allocation_agent = AllocationAgent(allocation_config)
        
        self.log("info", "Orchestrator Agent initialized")
    
    def process(self, message):
        """
        Process orchestration requests.
        
        Supported message types:
        - process_customer: Process a single customer
        - process_batch: Process a batch of customers
        
        Args:
            message (dict): Request message
            
        Returns:
            dict: Processing results
        """
        msg_type = message.get("type")
        
        if msg_type == "process_customer":
            return self.process_customer(message.get("customer_id"))
        elif msg_type == "process_batch":
            return self.process_batch(message.get("customer_ids", []))
        else:
            self.log("warning", f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}
    
    def process_customer(self, customer_id):
        """
        Process a single customer through the entire agent workflow.
        
        Args:
            customer_id (str): The customer ID to process
            
        Returns:
            dict: Processing result
        """
        try:
            self.log("info", f"Processing customer {customer_id}")
            
            # Step 1: Get customer data
            data_response = self.data_agent.process({
                "type": "get_customer_data", 
                "customer_id": customer_id
            })
            
            if "error" in data_response:
                raise ValueError(f"Data agent error: {data_response['error']}")
                
            customer_data = data_response
                
            # Step 2: Build customer journey
            journey_response = self.journey_agent.process({
                "type": "build_journey",
                "customer_id": customer_id,
                "customer_data": customer_data
            })
            
            if "error" in journey_response:
                raise ValueError(f"Journey agent error: {journey_response['error']}")
                
            customer_journey = journey_response.get("journey", [])
            
            # Step 3: Get customer permissions
            permissions = self._get_customer_permissions(customer_id)
            
            # Step 4: Get treatment recommendation
            treatment_response = self.treatment_agent.process({
                "type": "recommend_treatment",
                "customer_journey": customer_journey,
                "treatments": self.system_config.treatments,
                "constraints": self.system_config.constraints,
                "permissions": permissions
            })
            
            if "error" in treatment_response:
                raise ValueError(f"Treatment agent error: {treatment_response['error']}")
                
            selected_treatment = treatment_response.get("selected_treatment")
            explanation = treatment_response.get("explanation", "")
            
            # Step 5: Allocate resources
            if selected_treatment and selected_treatment != "ignore":
                allocation_response = self.allocation_agent.process({
                    "type": "allocate_resource",
                    "treatment_key": selected_treatment,
                    "customer_id": customer_id
                })
                
                if allocation_response.get("status") == "error":
                    # Primary treatment not available, try alternative
                    self.log("warning", f"Primary treatment {selected_treatment} not available, finding alternative")
                    
                    alternative_response = self.treatment_agent.process({
                        "type": "find_alternative",
                        "customer_journey": customer_journey,
                        "excluded_treatment": selected_treatment,
                        "treatments": self.system_config.treatments,
                        "constraints": self.system_config.constraints,
                        "permissions": permissions
                    })
                    
                    if "error" in alternative_response:
                        raise ValueError(f"Treatment agent error: {alternative_response['error']}")
                    
                    selected_treatment = alternative_response.get("selected_treatment")
                    explanation = alternative_response.get("explanation", "")
                    
                    # Allocate alternative treatment
                    if selected_treatment and selected_treatment != "ignore":
                        allocation_response = self.allocation_agent.process({
                            "type": "allocate_resource",
                            "treatment_key": selected_treatment,
                            "customer_id": customer_id
                        })
                        
                        if allocation_response.get("status") == "error":
                            self.log("error", f"Failed to allocate alternative treatment: {allocation_response.get('message')}")
                            selected_treatment = "ignore"
                            explanation = f"Failed to allocate treatment: {allocation_response.get('message')}"
            
            # Step 6: Create result entry
            result = {
                "customer_id": customer_id,
                "timestamp": datetime.now().isoformat(),
                "selected_treatment": selected_treatment if selected_treatment else "ignore",
                "explanation": explanation,
                "processing_status": "success"
            }
            
            self.log("info", f"Successfully processed customer {customer_id}")
            return result
            
        except Exception as e:
            self.log("error", f"Error processing customer {customer_id}: {str(e)}")
            return {
                "customer_id": customer_id,
                "timestamp": datetime.now().isoformat(),
                "selected_treatment": "none",
                "explanation": str(e),
                "processing_status": "error"
            }
    
    def process_batch(self, customer_ids):
        """
        Process a batch of customers.
        
        Args:
            customer_ids (list): List of customer IDs to process
            
        Returns:
            dict: Batch processing results
        """
        results = []
        
        for customer_id in customer_ids:
            try:
                result = self.process_customer(customer_id)
                results.append(result)
            except Exception as e:
                self.log("error", f"Error processing customer {customer_id}: {str(e)}")
                results.append({
                    "customer_id": customer_id,
                    "timestamp": datetime.now().isoformat(),
                    "selected_treatment": "none",
                    "explanation": str(e),
                    "processing_status": "error"
                })
        
        # Get final constraints state
        constraints_response = self.allocation_agent.process({
            "type": "get_constraints"
        })
        constraints = constraints_response.get("constraints", {})
        
        # Create output data
        output_data = {
            "results": results,
            "summary": {
                "total_processed": len(results),
                "successful": sum(1 for r in results if r["processing_status"] == "success"),
                "failed": sum(1 for r in results if r["processing_status"] == "error"),
                "constraints_final_state": constraints,
                "optimization_method": "multi-agent"
            }
        }
        
        return output_data
            
    def _get_customer_permissions(self, customer_id):
        """
        Get customer permissions from permissions.json file.
        
        Args:
            customer_id (str): The customer ID
            
        Returns:
            dict: Customer permissions
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