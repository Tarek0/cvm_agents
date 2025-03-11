"""
Treatment Manager Module

This module provides functionality to manage treatments, including standard and custom treatments.
"""

import os
import json
import datetime
import re
import uuid
from typing import Dict, Any, List, Optional, Tuple
import logging
from copy import deepcopy

from src.utils.treatment_parser import TreatmentParser
from src.utils.config import CVMConfig, load_config, save_config

logger = logging.getLogger(__name__)

class TreatmentManager:
    """Manager for handling treatments in the CVM system."""
    
    def __init__(self, config: Optional[CVMConfig] = None, custom_treatments_path: Optional[str] = None):
        """
        Initialize the treatment manager.
        
        Args:
            config: Configuration object, loaded from default if not provided
            custom_treatments_path: Path to store custom treatments, defaults to 'config/custom_treatments.json'
        """
        self.config = config or load_config()
        self.custom_treatments_path = custom_treatments_path or 'config/custom_treatments.json'
        self.custom_treatments = {}
        self.custom_constraints = {}
        self._load_custom_treatments()
    
    def _load_custom_treatments(self) -> None:
        """Load custom treatments from storage."""
        if not os.path.exists(self.custom_treatments_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.custom_treatments_path), exist_ok=True)
            # Create empty file
            with open(self.custom_treatments_path, 'w') as f:
                json.dump({"treatments": {}, "constraints": {}}, f, indent=2)
            return
        
        try:
            with open(self.custom_treatments_path, 'r') as f:
                data = json.load(f)
                self.custom_treatments = data.get("treatments", {})
                self.custom_constraints = data.get("constraints", {})
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load custom treatments: {e}")
            self.custom_treatments = {}
            self.custom_constraints = {}
    
    def _save_custom_treatments(self) -> None:
        """Save custom treatments to storage."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.custom_treatments_path), exist_ok=True)
            
            with open(self.custom_treatments_path, 'w') as f:
                json.dump({
                    "treatments": self.custom_treatments,
                    "constraints": self.custom_constraints
                }, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save custom treatments: {e}")
    
    def get_all_treatments(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available treatments (standard + custom).
        
        Returns:
            Dictionary of all treatments
        """
        # Create a copy to avoid modifying the original
        all_treatments = deepcopy(self.config.treatments)
        
        # Add custom treatments
        for treatment_id, treatment in self.custom_treatments.items():
            all_treatments[treatment_id] = treatment
        
        return all_treatments
    
    def get_all_constraints(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all constraints (standard + custom).
        
        Returns:
            Dictionary of all constraints
        """
        # Create a copy to avoid modifying the original
        all_constraints = deepcopy(self.config.constraints)
        
        # Add custom constraints
        for treatment_id, constraint in self.custom_constraints.items():
            all_constraints[treatment_id] = constraint
        
        return all_constraints
    
    def get_enabled_treatments(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enabled treatments (standard + custom).
        
        Returns:
            Dictionary of enabled treatments
        """
        all_treatments = self.get_all_treatments()
        return {k: v for k, v in all_treatments.items() if v.get('enabled', True)}
    
    def add_custom_treatment(
        self, 
        text_input: str,
        treatment_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Add a custom treatment based on text description.
        
        Args:
            text_input: Text description of the treatment
            treatment_id: Optional custom ID, generated if not provided
            
        Returns:
            Tuple of (treatment_id, treatment_definition)
        """
        # Parse the treatment text
        treatment, constraints = TreatmentParser.parse_treatment_text(text_input, treatment_id)
        
        # Add creation timestamp
        treatment["created_at"] = datetime.datetime.now().isoformat()
        
        # If treatment_id was not provided, generate one based on the text
        if not treatment_id:
            # Create a base from the description (first 20 chars, alphanumeric only)
            base_id = re.sub(r'[^a-z0-9_]', '_', text_input.lower()[:20])
            # Add a unique suffix
            unique_id = str(uuid.uuid4())[:8]
            treatment_id = f"custom_{base_id}_{unique_id}"
        
        # Ensure the treatment has an ID field
        treatment["id"] = treatment_id
        
        # Add to custom treatments
        self.custom_treatments[treatment_id] = treatment
        self.custom_constraints[treatment_id] = constraints
        
        # Save to storage
        self._save_custom_treatments()
        
        return treatment_id, treatment
    
    def update_custom_treatment(
        self,
        treatment_id: str,
        text_input: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Update an existing custom treatment.
        
        Args:
            treatment_id: ID of the treatment to update
            text_input: New text description
            
        Returns:
            Tuple of (treatment_id, updated_treatment)
            
        Raises:
            ValueError: If treatment_id is not found
        """
        if treatment_id not in self.custom_treatments:
            raise ValueError(f"Treatment with ID '{treatment_id}' not found")
        
        # Parse the treatment text
        treatment, constraints = TreatmentParser.parse_treatment_text(
            text_input, treatment_id
        )
        
        # Preserve creation timestamp
        treatment["created_at"] = self.custom_treatments[treatment_id].get("created_at")
        treatment["updated_at"] = datetime.datetime.now().isoformat()
        
        # Update the treatment
        self.custom_treatments[treatment_id] = treatment
        self.custom_constraints[treatment_id] = constraints
        
        # Save to storage
        self._save_custom_treatments()
        
        return treatment_id, treatment
    
    def remove_custom_treatment(self, treatment_id: str) -> bool:
        """
        Remove a custom treatment.
        
        Args:
            treatment_id: ID of the treatment to remove
            
        Returns:
            True if successful, False if treatment not found
        """
        if treatment_id not in self.custom_treatments:
            logger.warning(f"Treatment with ID '{treatment_id}' not found")
            return False
        
        # Remove the treatment
        del self.custom_treatments[treatment_id]
        
        # Remove constraints if they exist
        if treatment_id in self.custom_constraints:
            del self.custom_constraints[treatment_id]
        
        # Save to storage
        self._save_custom_treatments()
        
        return True
    
    def get_treatment_by_id(self, treatment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a treatment by its ID.
        
        Args:
            treatment_id: ID of the treatment
            
        Returns:
            Treatment definition or None if not found
        """
        # Check custom treatments first
        if treatment_id in self.custom_treatments:
            return self.custom_treatments[treatment_id]
        
        # Then check standard treatments
        if treatment_id in self.config.treatments:
            return self.config.treatments[treatment_id]
        
        return None
    
    def list_custom_treatments(self) -> List[Dict[str, Any]]:
        """
        List all custom treatments.
        
        Returns:
            List of custom treatments with their IDs
        """
        return [
            {"id": treatment_id, **treatment}
            for treatment_id, treatment in self.custom_treatments.items()
        ]
    
    def get_treatment_help(self) -> str:
        """Get help text for defining treatments."""
        return TreatmentParser.format_treatment_help() 