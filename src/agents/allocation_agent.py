"""
Resource Allocation Agent for the CVM multi-agent system.
Manages constraints and resource availability.
"""
from src.agents.base_agent import BaseAgent
import threading
import json
import logging
import copy

class AllocationAgent(BaseAgent):
    """
    Agent responsible for resource allocation and constraint management.
    
    This agent manages the allocation of limited resources, ensures
    thread-safety, and enforces constraint limits.
    """
    
    def __init__(self, config=None):
        """
        Initialize the AllocationAgent.
        
        Args:
            config: Configuration object
        """
        super().__init__("Allocation", config)
        
        # Initialize constraints
        if hasattr(config, 'constraints') and config.constraints:
            # It's a CVMConfig object with constraints
            self.constraints = copy.deepcopy(config.constraints)
        elif isinstance(config, dict) and "constraints" in config:
            # It's a dictionary with constraints
            self.constraints = copy.deepcopy(config["constraints"])
        else:
            # Default empty constraints
            self.constraints = {}
        
        # Thread safety for resource allocation
        self.lock = threading.RLock()
        
        # Allocation history
        self.allocation_history = []
        
        self.log("INFO", "AllocationAgent initialized")
    
    def process(self, message):
        """
        Process allocation-related requests.
        
        Supported message types:
        - allocate_resource: Allocate a resource for a treatment
        - check_availability: Check if a resource is available
        - get_constraints: Get current constraint status
        - reset_constraints: Reset constraints to initial values
        
        Args:
            message (dict): Request message
            
        Returns:
            dict: Response with allocation results or error
        """
        msg_type = message.get("type")
        
        if msg_type == "allocate_resource":
            return self.allocate_resource(
                message.get("treatment_key"),
                message.get("customer_id"),
                message.get("priority", 0.0)
            )
        elif msg_type == "check_availability":
            return self.check_availability(message.get("treatment_key"))
        elif msg_type == "get_constraints":
            return self.get_constraints()
        elif msg_type == "reset_constraints":
            return self.reset_constraints()
        else:
            self.log("warning", f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}
    
    def allocate_resource(self, treatment_key, customer_id, priority=0.0):
        """
        Allocate a resource for a treatment.
        
        This method ensures thread-safe updates to constraints
        and handles priority-based allocation when resources are limited.
        
        Args:
            treatment_key (str): The treatment to allocate
            customer_id (str): The customer ID
            priority (float): Priority score (0.0 to 1.0)
            
        Returns:
            dict: Allocation result
        """
        if not treatment_key:
            self.log("error", "No treatment key provided")
            return {"status": "error", "message": "No treatment key provided"}
            
        if treatment_key == "ignore":
            # No need to allocate resources for "ignore" treatment
            return {"status": "success", "treatment_key": "ignore", "allocated": True}
            
        with self.lock:
            # Check if treatment exists in constraints
            if treatment_key not in self.constraints:
                self.log("error", f"Treatment key '{treatment_key}' not found in constraints")
                return {
                    "status": "error", 
                    "message": f"Treatment key '{treatment_key}' not found in constraints"
                }
                
            # Check availability
            if self.constraints[treatment_key]["remaining_availability"] <= 0:
                self.log("warning", f"No availability left for {treatment_key}")
                return {
                    "status": "error",
                    "message": f"No availability left for {treatment_key}",
                    "allocated": False
                }
                
            # Allocate the resource
            self.constraints[treatment_key]["remaining_availability"] -= 1
            
            # Record allocation
            allocation_record = {
                "treatment_key": treatment_key,
                "customer_id": customer_id,
                "priority": priority,
                "timestamp": None  # Can be filled with datetime.now().isoformat() if needed
            }
            self.allocation_history.append(allocation_record)
            
            self.log("info", 
                f"Allocated {treatment_key} for customer {customer_id} " +
                f"(remaining: {self.constraints[treatment_key]['remaining_availability']})"
            )
            
            return {
                "status": "success",
                "treatment_key": treatment_key,
                "allocated": True,
                "remaining": self.constraints[treatment_key]["remaining_availability"]
            }
    
    def check_availability(self, treatment_key):
        """
        Check if a treatment resource is available.
        
        Args:
            treatment_key (str): The treatment to check
            
        Returns:
            dict: Availability information
        """
        if not treatment_key:
            self.log("error", "No treatment key provided")
            return {"status": "error", "message": "No treatment key provided"}
            
        if treatment_key not in self.constraints:
            self.log("error", f"Treatment key '{treatment_key}' not found in constraints")
            return {
                "status": "error", 
                "message": f"Treatment key '{treatment_key}' not found in constraints"
            }
            
        with self.lock:
            availability = self.constraints[treatment_key]["remaining_availability"]
            max_per_day = self.constraints[treatment_key].get("max_per_day", 0)
            
            self.log("info", f"Checked availability for {treatment_key}: {availability} remaining")
            
            return {
                "status": "success",
                "treatment_key": treatment_key,
                "available": availability > 0,
                "remaining": availability,
                "max_per_day": max_per_day,
                "usage_percentage": (1 - (availability / max_per_day)) * 100 if max_per_day > 0 else 0
            }
    
    def get_constraints(self):
        """
        Get the current constraint status.
        
        Returns:
            dict: Current constraints
        """
        with self.lock:
            self.log("info", "Returning current constraints")
            return {
                "status": "success",
                "constraints": self.constraints
            }
    
    def reset_constraints(self):
        """
        Reset constraints to their initial values.
        
        Returns:
            dict: Reset status
        """
        with self.lock:
            # For each constraint, reset remaining_availability to max_per_day
            for treatment_key, constraint in self.constraints.items():
                if "max_per_day" in constraint:
                    constraint["remaining_availability"] = constraint["max_per_day"]
                    
            self.log("info", "Constraints reset to initial values")
            return {
                "status": "success",
                "message": "Constraints reset to initial values"
            }
    
    def update_constraints(self, new_constraints):
        """
        Update the constraints.
        
        Args:
            new_constraints (dict): New constraint values
            
        Returns:
            dict: Update status
        """
        with self.lock:
            self.constraints = new_constraints
            self.log("info", "Constraints updated")
            return {
                "status": "success",
                "message": "Constraints updated"
            } 