"""
Configuration loader for the CVM system.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CVMConfig:
    """Data class to hold CVM configuration."""
    treatments: Dict[str, Dict[str, Any]]
    constraints: Dict[str, Dict[str, Any]]
    settings: Dict[str, Any]
    model: Dict[str, Any]
    validation: Dict[str, Any]

    @property
    def enabled_treatments(self) -> Dict[str, Dict[str, Any]]:
        """Return only enabled treatments."""
        return {k: v for k, v in self.treatments.items() if v.get('enabled', True)}

    @property
    def active_constraints(self) -> Dict[str, Dict[str, Any]]:
        """Return constraints for enabled treatments."""
        return {k: v for k, v in self.constraints.items() if k in self.enabled_treatments}

def load_config(config_path: Optional[str] = None) -> CVMConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file. If None, uses default path.

    Returns:
        CVMConfig: Configuration object

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If configuration file is invalid
    """
    if config_path is None:
        config_path = os.path.join(
            Path(__file__).parent.parent.parent,
            'config',
            'cvm_config.yaml'
        )

    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        # Validate required sections
        required_sections = ['treatments', 'constraints', 'settings', 'model', 'validation']
        missing_sections = [section for section in required_sections if section not in config_data]
        if missing_sections:
            raise ValueError(f"Missing required sections in config: {missing_sections}")

        return CVMConfig(**config_data)

    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

def reset_daily_constraints(config: CVMConfig) -> None:
    """
    Reset the remaining availability for all constraints to their max_per_day value.

    Args:
        config: The current configuration object
    """
    for treatment, constraint in config.active_constraints.items():
        constraint['remaining_availability'] = constraint['max_per_day']
        logger.info(f"Reset remaining availability for {treatment} to {constraint['max_per_day']}")

def save_config(config: CVMConfig, config_path: Optional[str] = None) -> None:
    """
    Save the current configuration state back to the YAML file.

    Args:
        config: Configuration object to save
        config_path: Path to save to. If None, uses default path.

    Raises:
        IOError: If unable to write to file
    """
    if config_path is None:
        config_path = os.path.join(
            Path(__file__).parent.parent.parent,
            'config',
            'cvm_config.yaml'
        )

    try:
        # Convert dataclass to dictionary
        config_dict = {
            'treatments': config.treatments,
            'constraints': config.constraints,
            'settings': config.settings,
            'model': config.model,
            'validation': config.validation
        }

        with open(config_path, 'w') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False)
            logger.info(f"Configuration saved to {config_path}")

    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        raise 