#!/usr/bin/env python3
"""
Customer Trigger CLI

A command-line interface for triggering customers based on specific criteria
and applying treatments to the triggered customers.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional

from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config

def setup_argparse() -> argparse.ArgumentParser:
    """Set up argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Trigger customers based on specific criteria and apply treatments"
    )
    
    # Main command options
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Trigger command
    trigger_parser = subparsers.add_parser("trigger", help="Trigger customers based on criteria")
    trigger_parser.add_argument(
        "--customer-ids", 
        type=str, 
        help="Comma-separated list of customer IDs to analyze"
    )
    trigger_parser.add_argument(
        "--all-customers", 
        action="store_true", 
        help="Use all available customer IDs"
    )
    trigger_parser.add_argument(
        "--trigger-type", 
        type=str, 
        choices=["network_issues", "billing_disputes", "churn_risk", "high_value", "roaming_issues", "custom"],
        required=True,
        help="Type of trigger to apply"
    )
    trigger_parser.add_argument(
        "--description", 
        type=str, 
        help="Description of what to look for in customer interactions (for custom triggers)"
    )
    trigger_parser.add_argument(
        "--keywords", 
        type=str, 
        help="[Deprecated] Comma-separated keywords for custom trigger"
    )
    trigger_parser.add_argument(
        "--data-types", 
        type=str, 
        default="call_transcripts,web_transcripts",
        help="[Deprecated] Comma-separated data types to search in for custom trigger"
    )
    trigger_parser.add_argument(
        "--output", 
        type=str, 
        default="text",
        choices=["text", "json", "csv"],
        help="Output format"
    )
    trigger_parser.add_argument(
        "--output-file", 
        type=str, 
        help="Output file path (defaults to stdout)"
    )
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Trigger and process customers with treatment")
    process_parser.add_argument(
        "--customer-ids", 
        type=str, 
        help="Comma-separated list of customer IDs to analyze"
    )
    process_parser.add_argument(
        "--all-customers", 
        action="store_true", 
        help="Use all available customer IDs"
    )
    process_parser.add_argument(
        "--trigger-type", 
        type=str, 
        choices=["network_issues", "billing_disputes", "churn_risk", "high_value", "roaming_issues", "custom"],
        required=True,
        help="Type of trigger to apply"
    )
    process_parser.add_argument(
        "--description", 
        type=str, 
        help="Description of what to look for in customer interactions (for custom triggers)"
    )
    process_parser.add_argument(
        "--keywords", 
        type=str, 
        help="[Deprecated] Comma-separated keywords for custom trigger"
    )
    process_parser.add_argument(
        "--data-types", 
        type=str, 
        default="call_transcripts,web_transcripts",
        help="[Deprecated] Comma-separated data types to search in for custom trigger"
    )
    process_parser.add_argument(
        "--treatment", 
        type=str, 
        required=True,
        help="Treatment ID to apply to matching customers"
    )
    process_parser.add_argument(
        "--output", 
        type=str, 
        default="text",
        choices=["text", "json", "csv"],
        help="Output format"
    )
    process_parser.add_argument(
        "--output-file", 
        type=str, 
        help="Output file path (defaults to stdout)"
    )
    
    # List triggers command
    list_parser = subparsers.add_parser("list-triggers", help="List available triggers")
    
    return parser

def get_all_customer_ids() -> List[str]:
    """Get all available customer IDs from the data files."""
    # Import here to avoid circular imports
    from src.tools.api_v2 import get_all_customer_ids as api_get_all_customer_ids
    
    try:
        return api_get_all_customer_ids()
    except Exception as e:
        print(f"Error loading customer IDs: {str(e)}", file=sys.stderr)
        return []

def format_trigger_results(results: Dict[str, Any], output_format: str) -> str:
    """Format trigger results based on specified output format."""
    if output_format == "json":
        return json.dumps(results, indent=2)
    
    elif output_format == "csv":
        if results.get("status") != "success":
            return f"Error: {results.get('message', 'Unknown error')}"
        
        lines = ["customer_id,match_reason"]
        for match in results.get("matches", []):
            customer_id = match.get("customer_id", "")
            reason = match.get("reason", "").replace(",", ";").replace("\n", " ")
            lines.append(f"{customer_id},{reason}")
        
        return "\n".join(lines)
    
    else:  # text format
        if results.get("status") != "success":
            return f"Error: {results.get('message', 'Unknown error')}"
        
        lines = [
            f"Trigger Results: {results.get('trigger_applied', 'unknown')}",
            f"Total Matches: {results.get('total_matches', 0)}",
            "-" * 50
        ]
        
        for match in results.get("matches", []):
            lines.append(f"Customer ID: {match.get('customer_id', '')}")
            lines.append(f"Reason: {match.get('reason', '')}")
            lines.append("-" * 50)
        
        return "\n".join(lines)

def format_process_results(results: Dict[str, Any], output_format: str) -> str:
    """Format processing results based on specified output format."""
    if output_format == "json":
        return json.dumps(results, indent=2)
    
    elif output_format == "csv":
        if results.get("status") != "success":
            return f"Error: {results.get('message', 'Unknown error')}"
        
        lines = ["customer_id,treatment,status,explanation"]
        for result in results.get("process_results", []):
            customer_id = result.get("customer_id", "")
            treatment = result.get("selected_treatment", {}).get("display_name", "None")
            status = result.get("status", "unknown")
            explanation = result.get("explanation", "").replace(",", ";").replace("\n", " ")
            lines.append(f"{customer_id},{treatment},{status},{explanation}")
        
        return "\n".join(lines)
    
    else:  # text format
        if results.get("status") != "success":
            return f"Error: {results.get('message', 'Unknown error')}"
        
        lines = [
            "Processing Results",
            f"Total Matches: {results.get('matches', 0)}",
            f"Total Processed: {results.get('processed', 0)}",
            "-" * 50
        ]
        
        # Show trigger results first
        trigger_results = results.get("trigger_results", {})
        if trigger_results.get("matches"):
            lines.append("\nTriggered Customers:")
            for match in trigger_results["matches"]:
                lines.append(f"Customer ID: {match.get('customer_id', '')}")
                lines.append(f"Reason: {match.get('reason', '')}")
                lines.append("-" * 30)
        
        # Then show processing results
        if results.get("process_results"):
            lines.append("\nProcessing Results:")
            for result in results["process_results"]:
                lines.append(f"Customer ID: {result.get('customer_id', '')}")
                lines.append(f"Treatment: {result.get('selected_treatment', {}).get('display_name', 'None')}")
                lines.append(f"Status: {result.get('status', 'unknown')}")
                lines.append(f"Explanation: {result.get('explanation', '')}")
                lines.append("-" * 30)
        
        return "\n".join(lines)

def write_output(content: str, output_file: Optional[str] = None):
    """Write output to file or stdout."""
    if output_file:
        try:
            with open(output_file, "w") as f:
                f.write(content)
            print(f"Results written to {output_file}")
        except Exception as e:
            print(f"Error writing to output file: {str(e)}", file=sys.stderr)
            print(content)
    else:
        print(content)

def main() -> None:
    """Run the CLI tool."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading configuration: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Handle list-triggers command
    if args.command == "list-triggers":
        orchestrator = OrchestratorAgent(config)
        response = orchestrator.process({"type": "list_triggers"})
        
        if response.get("status") == "success":
            print("\nAvailable Triggers:")
            print("------------------")
            for trigger_name in response.get("available_triggers", []):
                print(f"- {trigger_name}")
            print("\nFor custom triggers, provide a natural language description of what to look for:")
            print('Example: --trigger-type custom --description "Customers mentioning dogs or pets"')
        else:
            print(f"Error listing triggers: {response.get('message', 'Unknown error')}")
        return
    
    # Get customer IDs
    customer_ids = []
    if args.all_customers:
        customer_ids = get_all_customer_ids()
        if not customer_ids:
            print("No customer IDs found or error occurred.", file=sys.stderr)
            sys.exit(1)
    elif args.customer_ids:
        customer_ids = [id.strip() for id in args.customer_ids.split(",")]
    else:
        print("Either --customer-ids or --all-customers must be specified", file=sys.stderr)
        sys.exit(1)
        
    # Setup custom trigger if needed
    custom_trigger = None
    if args.trigger_type == "custom":
        if not args.description:
            print("--description must be specified for custom trigger", file=sys.stderr)
            sys.exit(1)
            
        # For custom triggers, just pass the description string directly
        custom_trigger = args.description
    
    # Initialize orchestrator agent
    orchestrator = OrchestratorAgent(config)
    
    # Handle trigger command
    if args.command == "trigger":
        trigger_message = {
            "type": "trigger_customers",
            "customer_ids": customer_ids,
            "trigger_type": args.trigger_type,
            "custom_trigger": custom_trigger
        }
        
        results = orchestrator.process(trigger_message)
        formatted_output = format_trigger_results(results, args.output)
        write_output(formatted_output, args.output_file)
        
    # Handle process command
    elif args.command == "process":
        # Trigger and process in one call
        process_message = {
            "type": "trigger_and_process",
            "customer_ids": customer_ids,
            "trigger_type": args.trigger_type,
            "custom_trigger": custom_trigger,
            "treatment_id": args.treatment
        }
        
        results = orchestrator.process(process_message)
        
        if results.get("status") != "success":
            print(f"Error: {results.get('message', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
            
        formatted_output = format_process_results(results, args.output)
        write_output(formatted_output, args.output_file)
        
if __name__ == "__main__":
    main() 