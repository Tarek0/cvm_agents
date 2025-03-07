"""
Unit tests for the configuration module.
"""
import os
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any
from src.utils.config import CVMConfig, load_config, reset_daily_constraints, save_config

# Test data
VALID_CONFIG = {
    "treatments": {
        "test_treatment": {
            "description": "Test treatment",
            "display_name": "Test",
            "enabled": True
        },
        "disabled_treatment": {
            "description": "Disabled treatment",
            "display_name": "Disabled",
            "enabled": False
        }
    },
    "constraints": {
        "test_treatment": {
            "max_per_day": 10,
            "remaining_availability": 5,
            "cost_per_contact_pounds": 1.0,
            "priority": 1
        },
        "disabled_treatment": {
            "max_per_day": 20,
            "remaining_availability": 15,
            "cost_per_contact_pounds": 2.0,
            "priority": 2
        }
    },
    "settings": {
        "reset_constraints_daily": True,
        "default_output_file": "test_results.json",
        "logging": {
            "default_level": "INFO"
        }
    },
    "model": {
        "id": "test-model",
        "temperature": 0.7
    },
    "validation": {
        "customer_id_pattern": "^T\\d{3}$"
    }
}

@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file for testing."""
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(VALID_CONFIG, f)
    return config_path

@pytest.fixture
def config_object() -> CVMConfig:
    """Create a CVMConfig object for testing."""
    return CVMConfig(**VALID_CONFIG)

def test_load_config_valid(temp_config_file: Path):
    """Test loading a valid configuration file."""
    config = load_config(str(temp_config_file))
    assert isinstance(config, CVMConfig)
    assert config.treatments["test_treatment"]["display_name"] == "Test"
    assert config.constraints["test_treatment"]["max_per_day"] == 10
    assert config.settings["reset_constraints_daily"] is True

def test_load_config_file_not_found():
    """Test loading a non-existent configuration file."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")

def test_load_config_invalid_yaml(tmp_path: Path):
    """Test loading an invalid YAML file."""
    invalid_yaml_path = tmp_path / "invalid_config.yaml"
    with open(invalid_yaml_path, "w") as f:
        f.write("invalid: yaml: content:")  # Invalid YAML syntax

    with pytest.raises(yaml.YAMLError):
        load_config(str(invalid_yaml_path))

def test_load_config_missing_sections(tmp_path: Path):
    """Test loading config with missing required sections."""
    incomplete_config = {
        "treatments": {},
        "constraints": {}
        # Missing other required sections
    }
    config_path = tmp_path / "incomplete_config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(incomplete_config, f)

    with pytest.raises(ValueError) as exc_info:
        load_config(str(config_path))
    assert "Missing required sections" in str(exc_info.value)

def test_enabled_treatments(config_object: CVMConfig):
    """Test the enabled_treatments property."""
    enabled = config_object.enabled_treatments
    assert "test_treatment" in enabled
    assert "disabled_treatment" not in enabled
    assert len(enabled) == 1

def test_active_constraints(config_object: CVMConfig):
    """Test the active_constraints property."""
    active = config_object.active_constraints
    assert "test_treatment" in active
    assert "disabled_treatment" not in active
    assert len(active) == 1

def test_reset_daily_constraints(config_object: CVMConfig):
    """Test resetting daily constraints."""
    # Modify some constraints
    config_object.constraints["test_treatment"]["remaining_availability"] = 2
    
    # Reset constraints
    reset_daily_constraints(config_object)
    
    # Check if constraints were reset
    assert config_object.constraints["test_treatment"]["remaining_availability"] == \
           config_object.constraints["test_treatment"]["max_per_day"]

def test_save_config(config_object: CVMConfig, tmp_path: Path):
    """Test saving configuration to file."""
    save_path = tmp_path / "saved_config.yaml"
    save_config(config_object, str(save_path))
    
    # Load the saved config and verify contents
    with open(save_path, "r") as f:
        saved_data = yaml.safe_load(f)
    
    assert saved_data["treatments"] == config_object.treatments
    assert saved_data["constraints"] == config_object.constraints
    assert saved_data["settings"] == config_object.settings

def test_save_config_permission_error(config_object: CVMConfig, tmp_path: Path):
    """Test saving config with insufficient permissions."""
    save_path = tmp_path / "readonly_config.yaml"
    save_path.touch(mode=0o444)  # Read-only file
    
    with pytest.raises(Exception):
        save_config(config_object, str(save_path))

def test_config_immutability(config_object: CVMConfig):
    """Test that config modifications don't affect original data."""
    original_max = config_object.constraints["test_treatment"]["max_per_day"]
    config_object.constraints["test_treatment"]["max_per_day"] = 100
    
    # Save and reload the config
    temp_path = Path("temp_config.yaml")
    save_config(config_object, str(temp_path))
    reloaded_config = load_config(str(temp_path))
    
    # Clean up
    os.remove(temp_path)
    
    assert reloaded_config.constraints["test_treatment"]["max_per_day"] == 100
    assert original_max == 10  # Original test data unchanged

def test_config_validation_rules(config_object: CVMConfig):
    """Test validation rules in config."""
    assert "customer_id_pattern" in config_object.validation
    assert config_object.validation["customer_id_pattern"] == "^T\\d{3}$"

def test_model_settings(config_object: CVMConfig):
    """Test model settings in config."""
    assert config_object.model["id"] == "test-model"
    assert config_object.model["temperature"] == 0.7 