#!/usr/bin/env python3
"""
Test script to verify that max_per_day constraints are properly enforced.
This script processes multiple customers in sequence and tracks the treatments recommended.
"""

import argparse
import json
from datetime import datetime
import logging
import sys
from collections import Counter
from pathlib import Path

# Fix imports to use correct paths
from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config, reset_daily_constraints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/cvm.log')
    ]
)

logger = logging.getLogger("constraint_test")

def test_forced_allocations(num_customers):
    """
    Test that max_per_day constraints are enforced when directly allocating treatments.
    
    Args:
        num_customers: Number of customers to process with forced treatment
        
    Returns:
        Dictionary with results
    """
    # Load config
    config = load_config()
    
    # Reset constraints to start fresh
    logger.info("Resetting constraints to initial values")
    reset_daily_constraints(config)
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(config)
    
    # Patch the _get_customer_permissions method to always return permissions for call_back
    def patched_permissions(self, customer_id):
        return {
            "permissions": {
                "call": {
                    "marketing": "Y",
                    "service": "Y"
                },
                "email": {
                    "marketing": "Y",
                    "service": "Y"
                },
                "sms": {
                    "marketing": "Y",
                    "service": "Y"
                }
            }
        }
    
    # Apply the patch
    original_permissions = orchestrator._get_customer_permissions
    orchestrator._get_customer_permissions = patched_permissions.__get__(orchestrator)
    
    # Get call_back max_per_day value
    constraints_response = orchestrator.allocation_agent.get_constraints()
    constraints = constraints_response.get("constraints", {})
    call_back_max = constraints.get("call_back", {}).get("max_per_day", 2)
    
    logger.info(f"call_back max_per_day: {call_back_max}")
    
    # Track allocations
    allocations = []
    allocation_results = []
    
    # Try to allocate more than the limit to test enforcement
    allocation_count = min(num_customers, call_back_max + 3)  # Try to exceed by 3
    
    for i in range(1, allocation_count + 1):
        customer_id = f"U{200 + i}"
        
        logger.info(f"Attempting to force call_back for customer {customer_id} ({i}/{allocation_count})")
        
        # Process customer with forced call_back treatment
        result = orchestrator.process({
            "type": "process_customer_with_treatment",
            "customer_id": customer_id,
            "treatment_id": "call_back"
        })
        
        # Track results
        allocations.append({
            "customer_id": customer_id,
            "treatment": "call_back",
            "status": result.get("status"),
            "result": result
        })
        
        allocation_results.append(result)
        
        logger.info(f"Allocation for {customer_id}: {result.get('status')}")
        
        # Additional logging for debugging
        if result.get("status") == "error":
            logger.info(f"  Error reason: {result.get('explanation', '')}")
    
    # Restore the original permissions method
    orchestrator._get_customer_permissions = original_permissions
    
    # Get final constraint status
    constraints_after = orchestrator.allocation_agent.get_constraints()
    
    return {
        "allocations": allocations,
        "allocation_results": allocation_results,
        "call_back_max": call_back_max,
        "constraints_after": constraints_after
    }

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Test CVM constraint enforcement")
    parser.add_argument("--customers", type=int, default=10, 
                      help="Number of customers to process (default: 10)")
    parser.add_argument("--reset", action="store_true", 
                      help="Reset constraints before starting")
    parser.add_argument("--output", type=str, default="output/constraint_test_results.json",
                      help="Output file path (default: output/constraint_test_results.json)")
    parser.add_argument("--test-type", type=str, choices=["standard", "forced"], default="standard",
                      help="Type of test to run (standard or forced)")
    
    args = parser.parse_args()
    
    logger.info(f"Starting constraint test with {args.customers} customers, test type: {args.test_type}")
    
    if args.test_type == "forced":
        # Test forced allocations
        report = test_forced_allocations(args.customers)
    else:
        # Process customers with standard approach
        report = process_customers(args.customers, args.reset)
    
    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Test completed. Results saved to {output_path}")
    
    # Print summary to console
    print("\n--- CONSTRAINT TEST SUMMARY ---")
    print(f"Test type: {args.test_type}")
    
    if args.test_type == "forced":
        # Print forced allocation summary
        call_back_max = report.get("call_back_max", 2)
        allocations = report.get("allocations", [])
        successful = sum(1 for a in allocations if a.get("status") == "success")
        failed = sum(1 for a in allocations if a.get("status") == "error")
        
        print(f"call_back max_per_day: {call_back_max}")
        print(f"Total allocations attempted: {len(allocations)}")
        print(f"Successful allocations: {successful}")
        print(f"Failed allocations (expected after exceeding limit): {failed}")
        
        # Verify constraint was enforced
        if successful <= call_back_max:
            print("\nCONSTRAINT ENFORCED CORRECTLY ✓")
            print(f"Successfully limited call_back allocations to {call_back_max} per day")
        else:
            print("\nCONSTRAINT NOT ENFORCED CORRECTLY ✗")
            print(f"Expected maximum {call_back_max} allocations, but {successful} were allowed")
        
        # Print final constraint status
        constraints = report.get("constraints_after", {}).get("constraints", {})
        print("\nFinal constraint status:")
        for treatment, constraint in constraints.items():
            if "max_per_day" in constraint and "remaining_availability" in constraint:
                max_val = constraint["max_per_day"]
                remaining = constraint["remaining_availability"]
                used = max_val - remaining
                print(f"  {treatment}: {used}/{max_val} used ({remaining} remaining)")
    else:
        # Print standard allocation summary
        print(f"Total customers processed: {args.customers}")
        print("\nTreatment counts:")
        for treatment, count in report.get("treatment_counts", {}).items():
            print(f"  {treatment}: {count}")
        
        print("\nFinal constraint status:")
        for treatment, constraint in report.get("constraints_status", {}).items():
            if "max_per_day" in constraint and "remaining_availability" in constraint:
                max_val = constraint["max_per_day"]
                remaining = constraint["remaining_availability"]
                used = max_val - remaining
                print(f"  {treatment}: {used}/{max_val} used ({remaining} remaining)")
    
    print("\nTest completed successfully!")

def process_customers(num_customers, reset_constraints=False):
    """
    Process a specified number of customers and track treatment recommendations.
    
    Args:
        num_customers: Number of customers to process
        reset_constraints: Whether to reset constraints before starting
        
    Returns:
        Dictionary with treatment counts and results
    """
    # Load config
    config = load_config()
    
    # Reset constraints if requested
    if reset_constraints:
        logger.info("Resetting constraints to initial values")
        reset_daily_constraints(config)
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(config)
    
    # Track recommended treatments
    treatment_counts = Counter()
    results = []
    
    # Process customers
    for i in range(1, num_customers + 1):
        # Generate customer ID (using a simple pattern for test)
        customer_id = f"U{100 + i}"
        
        logger.info(f"Processing customer {customer_id} ({i}/{num_customers})")
        
        try:
            # Process customer
            result = orchestrator.process({
                "type": "process_customer",
                "customer_id": customer_id
            })
            
            # Record result
            treatment = result.get("selected_treatment", "unknown")
            if isinstance(treatment, dict):
                treatment_id = treatment.get("id", "unknown")
            else:
                treatment_id = treatment
                
            treatment_counts[treatment_id] += 1
            
            # Add to results
            results.append({
                "customer_id": customer_id,
                "selected_treatment": result.get("selected_treatment"),
                "status": result.get("status"),
                "explanation": result.get("explanation")
            })
            
            logger.info(f"Recommended treatment for {customer_id}: {treatment_id}")
            
        except Exception as e:
            logger.error(f"Error processing customer {customer_id}: {str(e)}")
            results.append({
                "customer_id": customer_id,
                "error": str(e)
            })
    
    # Check constraints status after processing
    constraints = orchestrator.allocation_agent.get_constraints()
    
    # Prepare final report
    report = {
        "total_customers": num_customers,
        "treatment_counts": dict(treatment_counts),
        "constraints_status": constraints.get("constraints", {}),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    
    return report

if __name__ == "__main__":
    main() 