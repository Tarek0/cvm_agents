#!/usr/bin/env python
"""
Dynamic Treatment CLI

This script provides a command-line interface for managing custom treatments
in the CVM system and processing customers with those treatments.
"""

import argparse
import json
import logging
import sys
from typing import Dict, Any, List

from src.utils.config import load_config
from src.agents.orchestrator_agent import OrchestratorAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger('dynamic_treatment_cli')

def setup_argparse() -> argparse.ArgumentParser:
    """Set up command-line arguments parser."""
    parser = argparse.ArgumentParser(
        description="Dynamic Treatment CLI for the CVM system"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add treatment command
    add_parser = subparsers.add_parser("add", help="Add a new custom treatment")
    add_parser.add_argument(
        "description", 
        help="Text description of the treatment (use quotes for multi-word descriptions)"
    )
    add_parser.add_argument(
        "--id", 
        dest="treatment_id",
        help="Optional custom ID for the treatment"
    )
    
    # Update treatment command
    update_parser = subparsers.add_parser("update", help="Update an existing custom treatment")
    update_parser.add_argument(
        "treatment_id", 
        help="ID of the treatment to update"
    )
    update_parser.add_argument(
        "description", 
        help="New description for the treatment"
    )
    
    # Remove treatment command
    remove_parser = subparsers.add_parser("remove", help="Remove a custom treatment")
    remove_parser.add_argument(
        "treatment_id", 
        help="ID of the treatment to remove"
    )
    
    # List treatments command
    list_parser = subparsers.add_parser("list", help="List all treatments")
    list_parser.add_argument(
        "--custom-only", 
        action="store_true",
        help="List only custom treatments"
    )
    list_parser.add_argument(
        "--output", 
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    # Get help for treatments
    help_parser = subparsers.add_parser("help", help="Get help for defining treatments")
    
    # Process customer with custom treatments
    process_parser = subparsers.add_parser(
        "process", 
        help="Process a customer using available treatments"
    )
    process_parser.add_argument(
        "customer_id", 
        help="ID of the customer to process"
    )
    process_parser.add_argument(
        "--output", 
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    # Process batch of customers
    batch_parser = subparsers.add_parser(
        "batch", 
        help="Process a batch of customers"
    )
    batch_parser.add_argument(
        "customer_ids", 
        help="Comma-separated list of customer IDs"
    )
    batch_parser.add_argument(
        "--output", 
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    # Introspect a specific treatment
    get_parser = subparsers.add_parser(
        "get", 
        help="Get details of a specific treatment"
    )
    get_parser.add_argument(
        "treatment_id", 
        help="ID of the treatment to get"
    )
    get_parser.add_argument(
        "--output", 
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    return parser

def format_treatment_output(treatment: Dict[str, Any], indent: int = 0) -> str:
    """Format a treatment for text output."""
    spaces = " " * indent
    output = [
        f"{spaces}ID: {treatment.get('id')}",
        f"{spaces}Display Name: {treatment.get('display_name')}",
        f"{spaces}Description: {treatment.get('description')}",
        f"{spaces}Enabled: {treatment.get('enabled', True)}",
    ]
    
    if treatment.get('is_custom'):
        output.append(f"{spaces}Custom: Yes")
    
    if treatment.get('created_at'):
        output.append(f"{spaces}Created: {treatment.get('created_at')}")
    
    if treatment.get('updated_at'):
        output.append(f"{spaces}Updated: {treatment.get('updated_at')}")
    
    return "\n".join(output)

def format_treatments_list(treatments: List[Dict[str, Any]], output_format: str) -> str:
    """Format a list of treatments for output."""
    if output_format == "json":
        return json.dumps(treatments, indent=2)
    
    # Text format
    if not treatments:
        return "No treatments found."
    
    result = []
    for i, treatment in enumerate(treatments):
        if i > 0:
            result.append("")  # Add blank line between treatments
        result.append(format_treatment_output(treatment))
    
    return "\n".join(result)

def format_process_result(result: Dict[str, Any], output_format: str) -> str:
    """Format a processing result for output."""
    if output_format == "json":
        return json.dumps(result, indent=2)
    
    # Text format
    status = result.get("status", "unknown")
    if status == "error":
        return f"Error: {result.get('message', 'Unknown error')}"
    
    lines = [
        f"Customer: {result.get('customer_id')}",
        f"Status: {status}",
        f"Selected Treatment: {result.get('selected_treatment', 'none')}",
        "",
        "Explanation:",
        result.get('explanation', 'No explanation provided')
    ]
    
    return "\n".join(lines)

def format_batch_results(results: List[Dict[str, Any]], output_format: str) -> str:
    """Format batch processing results for output."""
    if output_format == "json":
        return json.dumps(results, indent=2)
    
    # Text format
    if not results:
        return "No results."
    
    lines = []
    for i, result in enumerate(results):
        if i > 0:
            lines.append("\n" + "-" * 40 + "\n")  # Add separator
        lines.append(format_process_result(result, "text"))
    
    return "\n".join(lines)

def main() -> None:
    """Main CLI function."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize orchestrator agent
    orchestrator = OrchestratorAgent()
    
    if args.command == "add":
        result = orchestrator.process({
            "type": "add_treatment",
            "description": args.description,
            "treatment_id": args.treatment_id
        })
        
        if result.get("status") == "success":
            print(f"Treatment added successfully with ID: {result['treatment_id']}")
            print(format_treatment_output(result["treatment"]))
        else:
            print(f"Error: {result.get('message', 'Failed to add treatment')}")
    
    elif args.command == "update":
        result = orchestrator.process({
            "type": "update_treatment",
            "treatment_id": args.treatment_id,
            "description": args.description
        })
        
        if result.get("status") == "success":
            print(f"Treatment updated successfully: {args.treatment_id}")
            print(format_treatment_output(result["treatment"]))
        else:
            print(f"Error: {result.get('message', 'Failed to update treatment')}")
    
    elif args.command == "remove":
        result = orchestrator.process({
            "type": "remove_treatment",
            "treatment_id": args.treatment_id
        })
        
        if result.get("status") == "success":
            print(result.get("message", "Treatment removed successfully"))
        else:
            print(f"Error: {result.get('message', 'Failed to remove treatment')}")
    
    elif args.command == "list":
        result = orchestrator.process({
            "type": "list_treatments",
            "custom_only": args.custom_only
        })
        
        if result.get("status") == "success":
            print(format_treatments_list(result.get("treatments", []), args.output))
        else:
            print(f"Error: {result.get('message', 'Failed to list treatments')}")
    
    elif args.command == "help":
        result = orchestrator.process({
            "type": "get_treatment_help"
        })
        
        if result.get("status") == "success":
            print(result.get("help_text", "No help available"))
        else:
            print(f"Error: {result.get('message', 'Failed to get help')}")
    
    elif args.command == "process":
        result = orchestrator.process({
            "type": "process_customer",
            "customer_id": args.customer_id
        })
        
        print(format_process_result(result, args.output))
    
    elif args.command == "batch":
        customer_ids = [id.strip() for id in args.customer_ids.split(",")]
        result = orchestrator.process({
            "type": "process_batch",
            "customer_ids": customer_ids
        })
        
        print(format_batch_results(result, args.output))
    
    elif args.command == "get":
        # First get all treatments
        result = orchestrator.process({
            "type": "list_treatments",
            "custom_only": False
        })
        
        if result.get("status") != "success":
            print(f"Error: {result.get('message', 'Failed to list treatments')}")
            return
        
        # Find the specific treatment
        treatment = next(
            (t for t in result.get("treatments", []) if t.get("id") == args.treatment_id), 
            None
        )
        
        if not treatment:
            print(f"Error: Treatment with ID '{args.treatment_id}' not found")
            return
        
        if args.output == "json":
            print(json.dumps(treatment, indent=2))
        else:
            print(format_treatment_output(treatment))

if __name__ == "__main__":
    main() 