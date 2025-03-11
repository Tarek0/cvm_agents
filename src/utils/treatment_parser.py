"""
Treatment Parser Module

This module provides functionality to parse text descriptions into treatment definitions.
"""

import re
import json
import uuid
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TreatmentParser:
    """Parser for converting text descriptions into treatment definitions."""
    
    @staticmethod
    def parse_treatment_text(
        text_input: str,
        treatment_id: Optional[str] = None,
        default_constraints: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Parse a text description into a treatment definition.
        
        Args:
            text_input: Text description of the treatment
            treatment_id: Optional custom treatment ID, generated if not provided
            default_constraints: Default constraint values to use if not specified
            
        Returns:
            A tuple with (treatment_definition, treatment_constraints)
        """
        # Generate a treatment ID if not provided
        if not treatment_id:
            # Create a treatment ID based on text content with a unique suffix
            base_id = re.sub(r'[^a-z0-9_]', '_', text_input.lower()[:20])
            unique_id = str(uuid.uuid4())[:8]
            treatment_id = f"custom_{base_id}_{unique_id}"
        
        # Initialize with defaults
        treatment = {
            "description": text_input,
            "display_name": treatment_id.replace('_', ' ').title(),
            "enabled": True,
            "is_custom": True,
            "created_at": None  # Will be set when added to the system
        }
        
        # Default constraints
        constraints = {
            "max_per_day": 100,
            "remaining_availability": 100,
            "cost_per_contact_pounds": 1.0,
            "priority": 10  # Lower priority than standard treatments
        }
        
        # If default constraints provided, update with those
        if default_constraints:
            constraints.update(default_constraints)
        
        # Check if the input is in JSON format
        if text_input.strip().startswith('{') and text_input.strip().endswith('}'):
            try:
                # Try to parse as JSON
                json_data = json.loads(text_input)
                
                # If successful, extract treatment details
                if "description" in json_data:
                    treatment["description"] = json_data["description"]
                
                if "display_name" in json_data:
                    treatment["display_name"] = json_data["display_name"]
                
                if "enabled" in json_data:
                    treatment["enabled"] = json_data["enabled"]
                
                # Extract constraint values if provided
                if "constraints" in json_data:
                    for key, value in json_data["constraints"].items():
                        if key in constraints:
                            constraints[key] = value
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON input: {e}. Using text as description.")
        else:
            # Try to extract structured information from free text using patterns
            
            # Look for display name in quotes or brackets
            display_name_match = re.search(r'\"([^\"]+)\"|\'([^\']+)\'|\[([^\]]+)\]', text_input)
            if display_name_match:
                # Use the first non-None group
                groups = display_name_match.groups()
                display_name = next((g for g in groups if g is not None), None)
                if display_name:
                    treatment["display_name"] = display_name
            
            # Look for keywords like "max" or "limit" followed by numbers for constraints
            max_per_day_match = re.search(r'(max|limit)[^\d]*(\d+)', text_input, re.IGNORECASE)
            if max_per_day_match:
                try:
                    constraints["max_per_day"] = int(max_per_day_match.group(2))
                    constraints["remaining_availability"] = int(max_per_day_match.group(2))
                except (ValueError, IndexError):
                    pass
            
            # Look for cost information
            cost_match = re.search(r'(cost|price)[^\d]*(\d+\.?\d*)', text_input, re.IGNORECASE)
            if cost_match:
                try:
                    constraints["cost_per_contact_pounds"] = float(cost_match.group(2))
                except (ValueError, IndexError):
                    pass
            
            # Look for priority information
            priority_match = re.search(r'(priority|importance)[^\d]*(\d+)', text_input, re.IGNORECASE)
            if priority_match:
                try:
                    constraints["priority"] = int(priority_match.group(2))
                except (ValueError, IndexError):
                    pass
        
        return treatment, constraints

    @staticmethod
    def format_treatment_help() -> str:
        """
        Return help text explaining how to format treatment descriptions.
        """
        return """
        You can define a custom treatment in two ways:
        
        1. Free text description:
           Example: "Send a personalized gift basket to high-value customers with limit 10 and priority 1"
           
        2. Structured JSON:
           Example: {
               "display_name": "Gift Basket",
               "description": "Send a personalized gift basket to high-value customers",
               "enabled": true,
               "constraints": {
                   "max_per_day": 10,
                   "cost_per_contact_pounds": 50.0,
                   "priority": 1
               }
           }
        
        The system will extract as much information as possible from your description.
        """ 