"""
CVM (Customer Value Management) System for Telecommunications.
Main module for determining customer treatments.
"""
import os
import json
import argparse
import re
import logging
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from smolagents import CodeAgent, LiteLLMModel
from dotenv import load_dotenv
from datetime import datetime

from tools.api_v2 import build_customer_journey, load_all_customer_data
from utils.config import load_config, CVMConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load configuration
config = load_config()
cvm_treatments = config.treatments
cvm_constraints = config.constraints

# Global lock for constraint updates
constraint_lock = Lock()

def update_constraints(selected_treatment_key: str, constraints: Dict[str, Dict[str, Union[int, float]]]) -> bool:
    """
    Update the constraints for the selected treatment.

    Args:
        selected_treatment_key (str): The key of the selected treatment
        constraints (Dict): The constraints dictionary to update

    Returns:
        bool: True if update was successful, False if no availability

    Raises:
        KeyError: If the treatment key is not found in constraints
    """
    with constraint_lock:
        try:
            if selected_treatment_key not in constraints:
                raise KeyError(f"Treatment key '{selected_treatment_key}' not found in constraints")

            if constraints[selected_treatment_key]["remaining_availability"] <= 0:
                logger.warning(f"No availability left for {selected_treatment_key}")
                return False

            constraints[selected_treatment_key]["remaining_availability"] -= 1
            logger.info(
                "Updated %s remaining_availability to %d",
                selected_treatment_key,
                constraints[selected_treatment_key]["remaining_availability"]
            )
            return True
        except KeyError as e:
            logger.error(str(e))
            raise

def create_result_entry(customer_id: str, selected_treatment: str = "None", 
                       explanation: str = "", status: str = "error", 
                       priority_score: float = 0.0) -> Dict[str, Any]:
    """
    Create a standardized result entry for a customer.
    
    Args:
        customer_id: The customer's ID
        selected_treatment: The selected treatment or "None"
        explanation: Explanation or error message
        status: Processing status ("success" or "error")
        priority_score: Priority score for the treatment
        
    Returns:
        Dict containing the result entry
    """
    return {
        "customer_id": customer_id,
        "timestamp": datetime.now().isoformat(),
        "selected_treatment": selected_treatment,
        "explanation": explanation,
        "processing_status": status,
        "priority_score": priority_score
    }

def process_customer(customer_id: str, customer_data: Dict[str, Any], shared_constraints: Dict[str, Dict[str, Union[int, float]]], model_id: str = "gpt-4o") -> Dict[str, Any]:
    """
    Process a single customer and determine their best treatment.

    Args:
        customer_id: The customer's ID
        customer_data: Pre-loaded customer data
        shared_constraints: Shared constraints dictionary
        model_id: The model ID to use

    Returns:
        Dict containing the processing results
    """
    try:
        logger.info("Processing Customer: %s", customer_id)
        cvm_journey = build_customer_journey(customer_id, customer_data)
        
        # First attempt with original treatment
        response = cvm_expert(cvm_journey, cvm_treatments=cvm_treatments, cvm_constraints=shared_constraints)
        selected_treatment_key = parse_treatment_key(response)
        
        if selected_treatment_key:
            # Try to update constraints
            if not update_constraints(selected_treatment_key, shared_constraints):
                # If primary treatment not available, try alternative
                logger.info("Primary treatment %s not available, finding alternative", selected_treatment_key)
                response = find_alternative_treatment(cvm_journey, selected_treatment_key, shared_constraints)
                selected_treatment_key = parse_treatment_key(response)
                
                if selected_treatment_key:
                    update_constraints(selected_treatment_key, shared_constraints)
        
        return create_result_entry(
            customer_id=customer_id,
            selected_treatment=selected_treatment_key if selected_treatment_key else "None",
            explanation=response,
            status="success"
        )
        
    except Exception as e:
        logger.error("Error processing customer %s: %s", customer_id, str(e))
        return create_result_entry(customer_id=customer_id, explanation=str(e))

def get_customer_permissions(customer_id: str) -> Dict[str, Any]:
    """
    Load customer permissions from permissions.json.
    
    Args:
        customer_id: The customer's ID
        
    Returns:
        Dict containing the customer's permissions
    """
    try:
        permissions_file = os.path.join(os.path.dirname(__file__), 'tools', 'data', 'permissions.json')
        with open(permissions_file, 'r') as f:
            permissions_data = json.load(f)
            
        customer_permissions = next(
            (item for item in permissions_data if item["customer_id"] == customer_id),
            None
        )
        
        if customer_permissions is None:
            logger.warning(f"No permissions found for customer {customer_id}")
            return {}
            
        return customer_permissions
    except Exception as e:
        logger.error(f"Error loading permissions for customer {customer_id}: {str(e)}")
        return {}

def get_permission_rules(permissions: Dict[str, Any]) -> str:
    """
    Generate permission rules text for the LLM prompt.
    
    Args:
        permissions: Customer permissions dictionary
        
    Returns:
        String containing formatted permission rules
    """
    if not permissions:
        return "WARNING: Customer permissions not found. Assume all channels are restricted."
        
    rules = ["Contact Permission Rules:"]
    
    # Add channel-specific rules
    for channel, perms in permissions.get("permissions", {}).items():
        channel_rules = []
        for perm_type, value in perms.items():
            if perm_type != "last_updated":
                status = "allowed" if value == "Y" else "not allowed"
                channel_rules.append(f"- {perm_type}: {status}")
        
        if channel_rules:
            rules.append(f"\n{channel.upper()} Channel:")
            rules.extend(channel_rules)
    
    # Add time-based rules
    rules.extend([
        f"\nContact Time Preferences:",
        f"- Preferred time: {permissions.get('preferred_contact_time', 'unknown')}",
        f"- Do not disturb: {permissions.get('do_not_disturb', 'unknown')}",
        f"- Preferred language: {permissions.get('preferred_language', 'unknown')}"
    ])
    
    return "\n".join(rules)

def find_alternative_treatment(cvm_journey: Union[str, Dict[str, Any]], excluded_treatment: str, constraints: Dict[str, Dict[str, Union[int, float]]]) -> Dict[str, str]:
    """
    Find an alternative treatment when the primary choice is not available.
    """
    available_treatments = {
        k: v for k, v in cvm_treatments.items() 
        if k != excluded_treatment and constraints[k]["remaining_availability"] > 0
    }
    
    if not available_treatments:
        return {
            "selected_treatment": "ignore",
            "explanation": "No treatments available, defaulting to no action"
        }
    
    # Get customer ID from journey for permissions check
    customer_id = None
    if isinstance(cvm_journey, dict):
        customer_events = cvm_journey if isinstance(cvm_journey, list) else [cvm_journey]
        customer_ids = {event.get("customer_id") for event in customer_events if isinstance(event, dict)}
        customer_id = next(iter(customer_ids)) if customer_ids else None
    
    # Get permissions if customer_id found
    permissions = get_customer_permissions(customer_id) if customer_id else {}
    permission_rules = get_permission_rules(permissions)
    
    model = LiteLLMModel(model_id="gpt-4o")
    agent = CodeAgent(
        tools=[], 
        model=model,
        additional_authorized_imports=['datetime'],
        planning_interval=3
    )
    
    prompt = f"""
    You are a Marketing Manager for a telecom company.
    The preferred treatment for this customer is not available.
    Based on this customer's profile and interactions:
    {cvm_journey}
    
    {permission_rules}
    
    IMPORTANT BUSINESS RULES:
    1. You MUST NOT recommend treatments that violate the customer's contact permissions
    2. You MUST NOT recommend email treatments if email marketing is not allowed
    3. You MUST NOT recommend SMS treatments if SMS marketing is not allowed
    4. You MUST NOT recommend call treatments if call marketing is not allowed
    5. You MUST respect the customer's preferred contact time and do not disturb hours
    6. You MUST use the customer's preferred language for communications
    7. If a channel's marketing permission is "N", you cannot use that channel for marketing communications
    
    What is the best alternative CVM treatment out of the below options to improve the customer's Life Time Value?
    Note that the following treatment is NOT available: {excluded_treatment}

    Available CVM Treatments: {json.dumps(available_treatments, indent=2)}
    Current Constraints: {json.dumps(constraints, indent=2)}

    Your response MUST be a valid JSON object with exactly the following schema:
    {{
        "selected_treatment": <treatment_key>,
        "explanation": <explanation>
    }}
    
    In your explanation, explicitly state how the selected treatment complies with the customer's permissions.
    If no compliant treatments are available, return "ignore" as the selected_treatment.
    """
    
    response = agent.run(prompt)
    logger.info("Alternative treatment response: %s", response)
    
    try:
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict) or 'selected_treatment' not in response:
            raise ValueError("Invalid response format from agent")
    except json.JSONDecodeError as e:
        logger.error("Failed to parse agent response as JSON: %s", str(e))
        raise ValueError("Invalid JSON response from agent") from e
    
    return response

def cvm_expert(
    cvm_journey: Union[str, Dict[str, Any]], 
    cvm_treatments: Optional[List[Dict[str, str]]] = None, 
    cvm_constraints: Optional[Dict[str, Dict[str, Union[int, float]]]] = None,
    verbose: bool = False
) -> Dict[str, str]:
    """
    Determines the best CVM treatment for a customer.
    """
    if isinstance(cvm_journey, dict):
        cvm_journey = json.dumps(cvm_journey, indent=2)
        if verbose:
            logger.debug('CVM Journey: %s', cvm_journey)
    
    # Get customer ID from journey for permissions check
    customer_id = None
    try:
        journey_data = json.loads(cvm_journey) if isinstance(cvm_journey, str) else cvm_journey
        if isinstance(journey_data, list):
            customer_ids = {event.get("customer_id") for event in journey_data if isinstance(event, dict)}
            customer_id = next(iter(customer_ids)) if customer_ids else None
        elif isinstance(journey_data, dict):
            customer_id = journey_data.get("customer_id")
    except:
        pass
    
    # Get permissions if customer_id found
    permissions = get_customer_permissions(customer_id) if customer_id else {}
    permission_rules = get_permission_rules(permissions)
    
    logger.info('Possible CVM Actions: %s', json.dumps(cvm_treatments, indent=2))
    logger.info('CVM Constraints: %s', json.dumps(cvm_constraints, indent=2))
    
    model = LiteLLMModel(model_id="gpt-4o")
    agent = CodeAgent(
        tools=[], 
        model=model, 
        additional_authorized_imports=['datetime'], 
        planning_interval=3
    )
    
    prompt = f"""
    You are a Marketing Manager for a telecom company.
    Based on this customer's profile and interactions:
    {cvm_journey}
    
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

    Available CVM Treatments: {json.dumps(cvm_treatments, indent=2)}
    CVM Treatments are subject to the following constraints: {json.dumps(cvm_constraints, indent=2)}.

    Your response MUST be a valid JSON object with exactly the following schema:
    {{
        "selected_treatment": <treatment_key>,
        "explanation": <explanation>
    }}
    
    In your explanation, explicitly state how the selected treatment complies with the customer's permissions.
    If no compliant treatments are available, return "ignore" as the selected_treatment.
    """
    
    response = agent.run(prompt)
    logger.info("Agent response: %s", response)
    
    try:
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict) or 'selected_treatment' not in response:
            raise ValueError("Invalid response format from agent")
    except json.JSONDecodeError as e:
        logger.error("Failed to parse agent response as JSON: %s", str(e))
        raise ValueError("Invalid JSON response from agent") from e
    
    return response

def parse_treatment_key(response: Union[Dict[str, Any], str]) -> Optional[str]:
    """
    Parse the selected treatment key from the response.

    Args:
        response: The response from the agent, either as dictionary or string

    Returns:
        Optional[str]: The parsed treatment key or None if not found
    """
    if isinstance(response, dict):
        if 'treatment_key' in response:
            return response['treatment_key']
        elif 'treatment' in response:
            treatment = response['treatment']
            if isinstance(treatment, (list, tuple)):
                return treatment[0]
            elif isinstance(treatment, str):
                return treatment
        elif 'selected_treatment' in response:
            return response['selected_treatment']

    # Get possible keys from the configuration
    possible_keys = [k for k in config.treatments.keys()]
    
    # If response is a string, search for treatment keys in it
    response_str = str(response).lower()
    for key in possible_keys:
        # Convert spaces to underscores in the key for matching
        display_name = config.treatments[key].get('display_name', '').lower()
        if display_name in response_str or key.lower() in response_str:
            return key
            
    return None

def batch_optimize_treatments(customer_journeys: Dict[str, List[Dict[str, Any]]], cvm_treatments: Dict[str, Dict[str, Any]], cvm_constraints: Dict[str, Dict[str, Union[int, float]]]) -> Dict[str, Dict[str, Any]]:
    """
    Optimize treatment selection for all customers together.
    
    Args:
        customer_journeys: Dictionary of customer journeys keyed by customer_id
        cvm_treatments: Available treatments
        cvm_constraints: Treatment constraints
        
    Returns:
        Dictionary of optimized treatments for each customer
    """
    model = LiteLLMModel(model_id="gpt-4o")
    agent = CodeAgent(
        tools=[], 
        model=model,
        additional_authorized_imports=['datetime'],
        planning_interval=3
    )
    
    # Prepare a summary of available resources
    total_resources = {
        treatment: constraint["remaining_availability"]
        for treatment, constraint in cvm_constraints.items()
    }
    
    # Create a summary of each customer's situation
    customer_summaries = {}
    for customer_id, journey in customer_journeys.items():
        # Extract key metrics
        recent_interactions = sorted(journey, key=lambda x: x.get('date', ''))[-5:]  # Last 5 interactions
        churn_data = [x for x in journey if x.get('churn_probability') is not None]
        latest_churn = churn_data[-1] if churn_data else None
        
        customer_summaries[customer_id] = {
            "recent_interactions": recent_interactions,
            "churn_probability": latest_churn.get('churn_probability') if latest_churn else None,
            "risk_factors": latest_churn.get('risk_factors', []) if latest_churn else [],
            "recent_sentiment": [x.get('sentiment') for x in recent_interactions if 'sentiment' in x]
        }
    
    prompt = f"""
    You are a Marketing Manager for a telecom company.
    You need to optimize the allocation of treatments across multiple customers to maximize overall customer retention and value.
    
    Available Resources:
    {json.dumps(total_resources, indent=2)}
    
    Available Treatments:
    {json.dumps(cvm_treatments, indent=2)}
    
    Customer Situations:
    {json.dumps(customer_summaries, indent=2)}
    
    Full Customer Journeys:
    {json.dumps(customer_journeys, indent=2)}
    
    Task:
    1. Analyze each customer's situation, risk level, and needs
    2. Consider the limited availability of treatments
    3. Optimize treatment allocation to maximize overall impact
    4. Prioritize high-risk customers while ensuring efficient resource use
    
    Your response MUST be a valid JSON object with the following schema:
    {{
        "customer_id": {{
            "selected_treatment": <treatment_key>,
            "explanation": <explanation>,
            "priority": <priority_score>
        }},
        ...
    }}
    
    The priority_score should be between 0 and 1, indicating the urgency of the treatment.
    """
    
    response = agent.run(prompt)
    logger.info("Batch optimization response: %s", response)
    
    try:
        if isinstance(response, str):
            response = json.loads(response)
        
        # Validate response format
        if not isinstance(response, dict):
            raise ValueError("Invalid response format from agent")
            
        for customer_id, treatment_info in response.items():
            if not isinstance(treatment_info, dict) or 'selected_treatment' not in treatment_info:
                raise ValueError(f"Invalid treatment info for customer {customer_id}")
                
        return response
        
    except json.JSONDecodeError as e:
        logger.error("Failed to parse agent response as JSON: %s", str(e))
        raise ValueError("Invalid JSON response from agent") from e

def main() -> None:
    """
    Main function to process customer journey data.
    """
    parser = argparse.ArgumentParser(description="Process customer journey data.")
    parser.add_argument("--customer_ids", help="Comma separated list of Customer IDs", default="U123")
    parser.add_argument("--output_file", help="Output JSON file", default="results.json")
    parser.add_argument("--log_level", help="Logging level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--max_workers", help="Maximum number of parallel workers", type=int, default=4)
    parser.add_argument("--batch_optimize", help="Use batch optimization for treatment selection", 
                       action="store_true", default=True)
    args = parser.parse_args()

    # Set logging level from command line argument
    logging.getLogger().setLevel(args.log_level)

    customer_ids = [cid.strip() for cid in args.customer_ids.split(",")]
    results: List[Dict[str, Any]] = []
    
    try:
        # Load all customer data upfront
        all_customer_data = load_all_customer_data(customer_ids)
        logger.info("Loaded data for all customers")
        
        if args.batch_optimize:
            # Build journeys for all customers
            customer_journeys = {
                customer_id: build_customer_journey(customer_id, all_customer_data)
                for customer_id in customer_ids
            }
            
            # Perform batch optimization
            optimized_treatments = batch_optimize_treatments(
                customer_journeys,
                cvm_treatments,
                cvm_constraints
            )
            
            # Process optimized treatments
            for customer_id, treatment_info in optimized_treatments.items():
                try:
                    selected_treatment = treatment_info['selected_treatment']
                    if selected_treatment != 'ignore':
                        if update_constraints(selected_treatment, cvm_constraints):
                            status = "success"
                        else:
                            # If primary treatment not available, try alternative
                            response = find_alternative_treatment(
                                customer_journeys[customer_id],
                                selected_treatment,
                                cvm_constraints
                            )
                            selected_treatment = parse_treatment_key(response)
                            treatment_info = response
                            if selected_treatment:
                                update_constraints(selected_treatment, cvm_constraints)
                                status = "success"
                            else:
                                status = "error"
                    else:
                        status = "success"
                        
                    results.append(create_result_entry(
                        customer_id=customer_id,
                        selected_treatment=selected_treatment,
                        explanation=treatment_info,
                        status=status,
                        priority_score=treatment_info.get('priority', 0)
                    ))
                    
                except Exception as e:
                    logger.error("Error processing optimized treatment for customer %s: %s", customer_id, str(e))
                    results.append(create_result_entry(customer_id=customer_id, explanation=str(e)))
        else:
            # Original parallel processing logic
            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                future_to_customer = {
                    executor.submit(
                        process_customer, 
                        customer_id, 
                        all_customer_data,
                        cvm_constraints
                    ): customer_id for customer_id in customer_ids
                }
                
                for future in as_completed(future_to_customer):
                    customer_id = future_to_customer[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error("Error processing customer %s: %s", customer_id, str(e))
                        results.append(create_result_entry(customer_id=customer_id, explanation=str(e)))

        # Sort results by priority score (if available) then customer_id
        results.sort(key=lambda x: (-float(x.get('priority_score', 0)), x['customer_id']))
        
        output_data = {
            "results": results,
            "summary": {
                "total_processed": len(results),
                "successful": sum(1 for r in results if r["processing_status"] == "success"),
                "failed": sum(1 for r in results if r["processing_status"] == "error"),
                "constraints_final_state": cvm_constraints,
                "optimization_method": "batch" if args.batch_optimize else "individual"
            }
        }
        
        with open(args.output_file, "w") as outfile:
            json.dump(output_data, outfile, indent=2)
        logger.info("Results written to %s", args.output_file)
        
    except Exception as e:
        logger.error("Failed to process customers: %s", str(e))
        raise

if __name__ == "__main__":
    main()
