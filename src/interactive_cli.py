#!/usr/bin/env python3
"""
Interactive CLI for CVM Agents

This CLI provides an interactive shell for managing customer value management operations.
It supports loading customer data, triggering customers, and applying treatments.
"""

import os
import cmd
import json
import argparse
import logging
from typing import List, Dict, Any, Optional

from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CvmShell(cmd.Cmd):
    """Interactive shell for the CVM system."""
    
    intro = """
    =========================================
    CVM Interactive Shell
    Type 'help' or '?' to list commands.
    Type 'exit' or 'quit' to exit the shell.
    =========================================
    """
    prompt = 'cvm> '
    
    def __init__(self):
        """Initialize the shell with an orchestrator agent."""
        super().__init__()
        try:
            config = load_config()
            self.orchestrator = OrchestratorAgent(config)
            self.current_customer = None
            self.trigger_results = None
            logger.info("CVM shell initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing CVM shell: {str(e)}")
            raise
    
    def do_exit(self, arg):
        """Exit the shell."""
        print("Goodbye!")
        return True
        
    def do_quit(self, arg):
        """Exit the shell."""
        return self.do_exit(arg)
        
    def do_load(self, arg):
        """Load customer data for analysis.
        
        Usage: load <customer_id>
        """
        if not arg:
            print("Please provide a customer ID.")
            return
            
        try:
            customer_id = arg.strip()
            # Here you would load the customer data
            print(f"Loading data for customer {customer_id}...")
            # This is a placeholder for the real implementation
            self.current_customer = customer_id
            print(f"Customer {customer_id} loaded successfully.")
        except Exception as e:
            print(f"Error loading customer: {str(e)}")
    
    def do_trigger(self, arg):
        """Trigger customers based on criteria.
        
        Usage: trigger <trigger_type> [description]
        Example: trigger network_issues
                 trigger custom "Customers mentioning dogs or pets"
        """
        args = arg.split(maxsplit=1)
        if not args:
            print("Please provide a trigger type.")
            return
            
        trigger_type = args[0]
        custom_trigger = args[1] if len(args) > 1 else None
        
        if trigger_type == "custom" and not custom_trigger:
            print("Please provide a description for the custom trigger.")
            return
            
        try:
            # Get all customer IDs for now - in a real implementation
            # you might want to be more selective
            from src.tools.api_v2 import get_all_customer_ids
            customer_ids = get_all_customer_ids()
            
            print(f"Triggering {len(customer_ids)} customers with {trigger_type}...")
            
            # Call the orchestrator to trigger customers
            trigger_message = {
                "type": "trigger_customers",
                "customer_ids": customer_ids,
                "trigger_type": trigger_type,
                "custom_trigger": custom_trigger
            }
            
            results = self.orchestrator.process(trigger_message)
            self.trigger_results = results
            
            if results.get("status") == "success":
                print(f"Found {results.get('total_matches', 0)} matching customers.")
                for i, match in enumerate(results.get("matches", []), 1):
                    print(f"{i}. Customer {match.get('customer_id')}: {match.get('reason')[:100]}...")
            else:
                print(f"Error: {results.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error triggering customers: {str(e)}")
    
    def do_process(self, arg):
        """Process a customer with a treatment.
        
        Usage: process <customer_id> <treatment_id>
        """
        args = arg.split()
        if len(args) < 2:
            print("Please provide a customer ID and treatment ID.")
            return
            
        customer_id = args[0]
        treatment_id = args[1]
        
        try:
            print(f"Processing customer {customer_id} with treatment {treatment_id}...")
            
            # Call the orchestrator to process the customer
            result = self.orchestrator.process_customer_with_treatment(customer_id, treatment_id)
            
            if result.get("status") == "success":
                print(f"Treatment applied successfully: {result.get('explanation')}")
            else:
                print(f"Error: {result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error processing customer: {str(e)}")
    
    def do_save(self, arg):
        """Save current results to file.
        
        Usage: save <filename>
        Example: save trigger_results.json
        """
        if not arg:
            print("Please provide a filename.")
            return
            
        if not self.trigger_results:
            print("No results to save. Run a trigger command first.")
            return
            
        try:
            filename = arg.strip()
            
            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Construct the full path in the output directory
            output_path = os.path.join(output_dir, os.path.basename(filename))
            
            with open(output_path, "w") as f:
                json.dump(self.trigger_results, f, indent=2)
            
            print(f"Results saved to {output_path}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")

def main():
    """Main function to run the interactive CLI."""
    parser = argparse.ArgumentParser(description="Interactive CLI for CVM Agents")
    parser.add_argument("--log-level", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO",
                        help="Set the logging level")
    
    args = parser.parse_args()
    
    # Set the logging level
    logging.getLogger().setLevel(args.log_level)
    
    # Start the shell
    try:
        shell = CvmShell()
        shell.cmdloop()
    except Exception as e:
        logger.error(f"Error running CVM shell: {str(e)}")
        raise

if __name__ == "__main__":
    main()
