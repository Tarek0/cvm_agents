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
import shlex
from typing import List, Dict, Any, Optional, Tuple

from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config
from src.tools.api_v2 import get_all_customer_ids

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class CvmShell(cmd.Cmd):
    """Interactive shell for the CVM system."""
    
    intro = f"""
    {Colors.BOLD}{Colors.BLUE}=========================================
    CVM Interactive Shell
    Type 'help' or '?' to list commands.
    Type 'exit' or 'quit' to exit the shell.
    =========================================
    
    Available categories:
      - customers: Load and view customer data
      - triggers:  Find customers matching criteria
      - treatments: Apply treatments to customers
      - multi-agent: Run the multi-agent system
      - results: Save and view results
    {Colors.END}
    """
    prompt = f'{Colors.BOLD}{Colors.GREEN}cvm> {Colors.END}'
    
    def __init__(self):
        """Initialize the shell with an orchestrator agent."""
        super().__init__()
        try:
            config = load_config()
            self.orchestrator = OrchestratorAgent(config)
            self.current_customer = None
            self.loaded_customer_data = None
            self.trigger_results = None
            self.process_results = None
            self.multi_agent_results = None
            
            # Ensure output directory exists
            self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
            os.makedirs(self.output_dir, exist_ok=True)
            
            logger.info("CVM shell initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing CVM shell: {str(e)}")
            raise
    
    def do_exit(self, arg):
        """Exit the shell."""
        print(f"{Colors.YELLOW}Goodbye!{Colors.END}")
        return True
        
    def do_quit(self, arg):
        """Exit the shell."""
        return self.do_exit(arg)
    
    def emptyline(self):
        """Do nothing on empty line."""
        pass
    
    # ==== CUSTOMER COMMANDS ====
    
    def do_list_customers(self, arg):
        """List all available customer IDs.
        
        Usage: list_customers
        """
        try:
            customer_ids = get_all_customer_ids()
            if not customer_ids:
                print(f"{Colors.RED}No customer IDs found.{Colors.END}")
                return
                
            print(f"{Colors.BOLD}{Colors.BLUE}Available customers ({len(customer_ids)}):  {Colors.END}")
            # Display in columns
            column_width = 10
            num_columns = 5
            for i in range(0, len(customer_ids), num_columns):
                row = customer_ids[i:i+num_columns]
                print("  " + "".join(f"{cid:<{column_width}}" for cid in row))
        except Exception as e:
            print(f"{Colors.RED}Error listing customers: {str(e)}{Colors.END}")
        
    def do_load(self, arg):
        """Load customer data for analysis.
        
        Usage: load <customer_id>
        Example: load U130
        """
        if not arg:
            print(f"{Colors.RED}Please provide a customer ID.{Colors.END}")
            print(f"Use {Colors.CYAN}list_customers{Colors.END} to see available customer IDs.")
            return
            
        try:
            customer_id = arg.strip()
            print(f"Loading data for customer {Colors.BOLD}{customer_id}{Colors.END}...")
            
            # Fetch customer data using the DataAgent via orchestrator
            message = {
                "type": "get_customer_data",
                "customer_id": customer_id
            }
            
            result = self.orchestrator.process(message)
            if result.get("status") == "success":
                self.current_customer = customer_id
                self.loaded_customer_data = result.get("data", {})
                
                print(f"{Colors.GREEN}Customer {Colors.BOLD}{customer_id}{Colors.END}{Colors.GREEN} loaded successfully.{Colors.END}")
                self._display_customer_summary(customer_id, self.loaded_customer_data)
            else:
                print(f"{Colors.RED}Error: {result.get('message', 'Unknown error')}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error loading customer: {str(e)}{Colors.END}")
    
    def _display_customer_summary(self, customer_id, data):
        """Display a summary of customer data."""
        if not data:
            print(f"{Colors.YELLOW}No data available for customer {customer_id}.{Colors.END}")
            return
            
        print(f"\n{Colors.BOLD}{Colors.BLUE}Customer Summary for {customer_id}:{Colors.END}")
        
        for data_type, records in data.items():
            if records:
                print(f"  {Colors.CYAN}{data_type}:{Colors.END} {len(records)} records")
            
        # If available, show churn probability
        churn_scores = data.get("churn_scores", [])
        if churn_scores:
            latest_churn = churn_scores[-1]  # Assuming the last one is the most recent
            prob = latest_churn.get("churn_probability", "N/A")
            risk_factors = latest_churn.get("risk_factors", [])
            sat_score = latest_churn.get("recent_satisfaction_score", "N/A")
            
            print(f"\n  {Colors.BOLD}Churn Risk:{Colors.END} {self._format_probability(prob)}")
            print(f"  {Colors.BOLD}Risk Factors:{Colors.END} {', '.join(risk_factors)}")
            print(f"  {Colors.BOLD}Satisfaction Score:{Colors.END} {sat_score}/5")
    
    def _format_probability(self, prob):
        """Format probability with color coding."""
        if not isinstance(prob, (int, float)):
            return f"{Colors.YELLOW}{prob}{Colors.END}"
            
        if prob < 0.3:
            return f"{Colors.GREEN}{prob:.2f}{Colors.END}"
        elif prob < 0.6:
            return f"{Colors.YELLOW}{prob:.2f}{Colors.END}"
        else:
            return f"{Colors.RED}{prob:.2f}{Colors.END}"
    
    # ==== TRIGGER COMMANDS ====
    
    def do_list_triggers(self, arg):
        """List all available trigger types.
        
        Usage: list_triggers
        """
        try:
            response = self.orchestrator.process({"type": "list_triggers"})
            
            if response.get("status") == "success":
                print(f"\n{Colors.BOLD}{Colors.BLUE}Available Triggers:{Colors.END}")
                for trigger_name in response.get("available_triggers", []):
                    print(f"  - {Colors.CYAN}{trigger_name}{Colors.END}")
                print(f"\n{Colors.BOLD}For custom triggers, provide a natural language description:{Colors.END}")
                print(f'Example: {Colors.CYAN}trigger custom "Customers mentioning dogs or pets"{Colors.END}')
            else:
                print(f"{Colors.RED}Error listing triggers: {response.get('message', 'Unknown error')}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.END}")
    
    def do_trigger(self, arg):
        """Trigger customers based on criteria.
        
        Usage: trigger <trigger_type> [description] [--customer-ids IDs | --all-customers] [--output format] [--output-file filename]
        
        Examples:
          trigger network_issues
          trigger custom "Customers mentioning dogs or pets"
          trigger high_value --customer-ids U123,U124,U125
          trigger churn_risk --all-customers --output json --output-file high_risk.json
        """
        try:
            args = self._parse_trigger_args(arg)
            if not args:
                return
                
            trigger_type, custom_trigger, customer_ids, output_format, output_file = args
            
            print(f"Triggering customers with {Colors.BOLD}{trigger_type}{Colors.END}...")
            
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
                print(f"{Colors.GREEN}Found {Colors.BOLD}{results.get('total_matches', 0)}{Colors.END}{Colors.GREEN} matching customers.{Colors.END}")
                for i, match in enumerate(results.get("matches", []), 1):
                    reason = match.get("reason", "")
                    # Truncate long reasons but keep them readable
                    if len(reason) > 100:
                        reason = reason[:97] + "..."
                    print(f"{i}. Customer {Colors.BOLD}{match.get('customer_id')}{Colors.END}: {reason}")
                    
                # If output file specified, save the results
                if output_file:
                    self._save_results(results, output_format, output_file)
            else:
                print(f"{Colors.RED}Error: {results.get('message', 'Unknown error')}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error triggering customers: {str(e)}{Colors.END}")
    
    def _parse_trigger_args(self, arg_string):
        """Parse trigger command arguments."""
        if not arg_string:
            print(f"{Colors.RED}Please provide a trigger type.{Colors.END}")
            print(f"Use {Colors.CYAN}list_triggers{Colors.END} to see available trigger types.")
            return None
        
        # Parse the arguments using shlex to handle quoted strings properly
        args = shlex.split(arg_string)
        trigger_type = args[0]
        
        # Default values
        custom_trigger = None
        customer_ids = []
        output_format = "text"
        output_file = None
        
        # Process arguments
        i = 1
        while i < len(args):
            if args[i] == "--customer-ids" and i + 1 < len(args):
                customer_ids = [cid.strip() for cid in args[i+1].split(",")]
                i += 2
            elif args[i] == "--all-customers":
                customer_ids = get_all_customer_ids()
                i += 1
            elif args[i] == "--output" and i + 1 < len(args):
                output_format = args[i+1]
                i += 2
            elif args[i] == "--output-file" and i + 1 < len(args):
                output_file = args[i+1]
                i += 2
            elif trigger_type == "custom" and not custom_trigger:
                custom_trigger = args[i]
                i += 1
            else:
                i += 1
        
        # Validate arguments
        if trigger_type == "custom" and not custom_trigger:
            print(f"{Colors.RED}Please provide a description for the custom trigger.{Colors.END}")
            return None
            
        if not customer_ids:
            customer_ids = get_all_customer_ids()
            print(f"{Colors.YELLOW}No customer IDs specified, using all available customers.{Colors.END}")
            
        if output_format not in ["text", "json", "csv"]:
            print(f"{Colors.RED}Invalid output format: {output_format}. Using 'text' instead.{Colors.END}")
            output_format = "text"
        
        return (trigger_type, custom_trigger, customer_ids, output_format, output_file)
    
    # ==== PROCESS COMMANDS ====
    
    def do_process(self, arg):
        """Process customers with treatments based on trigger criteria.
        
        Usage: process <trigger_type> <treatment_id> [description] [--customer-ids IDs | --all-customers] [--output format] [--output-file filename]
        
        Examples:
          process network_issues service_sms
          process custom service_call "Customers mentioning dogs or pets"
          process high_value loyalty_offer --customer-ids U123,U124
          process churn_risk retention_special --all-customers --output json --output-file retention_results.json
        """
        try:
            args = self._parse_process_args(arg)
            if not args:
                return
                
            trigger_type, treatment_id, custom_trigger, customer_ids, output_format, output_file = args
            
            print(f"Processing customers with trigger {Colors.BOLD}{trigger_type}{Colors.END} and treatment {Colors.BOLD}{treatment_id}{Colors.END}...")
            
            # Call the orchestrator to process customers
            process_message = {
                "type": "trigger_and_process",
                "customer_ids": customer_ids,
                "trigger_type": trigger_type,
                "custom_trigger": custom_trigger,
                "treatment_id": treatment_id
            }
            
            results = self.orchestrator.process(process_message)
            self.process_results = results
            
            if results.get("status") == "success":
                matches = len(results.get("trigger_results", {}).get("matches", []))
                processed = len(results.get("process_results", []))
                
                print(f"{Colors.GREEN}Found {Colors.BOLD}{matches}{Colors.END}{Colors.GREEN} matching customers.{Colors.END}")
                print(f"{Colors.GREEN}Processed {Colors.BOLD}{processed}{Colors.END}{Colors.GREEN} customers with treatment {Colors.BOLD}{treatment_id}{Colors.END}{Colors.GREEN}.{Colors.END}")
                
                # Display processing results
                process_results = results.get("process_results", [])
                if process_results:
                    print(f"\n{Colors.BOLD}{Colors.BLUE}Processing Results:{Colors.END}")
                    for i, result in enumerate(process_results, 1):
                        customer_id = result.get("customer_id", "")
                        treatment = result.get("selected_treatment", {}).get("display_name", "None")
                        status = result.get("status", "unknown")
                        status_color = Colors.GREEN if status == "success" else Colors.RED
                        
                        print(f"{i}. Customer {Colors.BOLD}{customer_id}{Colors.END}: {Colors.BOLD}{treatment}{Colors.END} - Status: {status_color}{status}{Colors.END}")
                
                # If output file specified, save the results
                if output_file:
                    self._save_results(results, output_format, output_file)
            else:
                print(f"{Colors.RED}Error: {results.get('message', 'Unknown error')}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error processing customers: {str(e)}{Colors.END}")
    
    def _parse_process_args(self, arg_string):
        """Parse process command arguments."""
        if not arg_string:
            print(f"{Colors.RED}Please provide a trigger type and treatment ID.{Colors.END}")
            print(f"Use {Colors.CYAN}list_triggers{Colors.END} to see available trigger types.")
            return None
        
        # Parse the arguments using shlex to handle quoted strings properly
        args = shlex.split(arg_string)
        
        if len(args) < 2:
            print(f"{Colors.RED}Please provide both a trigger type and a treatment ID.{Colors.END}")
            return None
            
        trigger_type = args[0]
        treatment_id = args[1]
        
        # Default values
        custom_trigger = None
        customer_ids = []
        output_format = "text"
        output_file = None
        
        # Process arguments
        i = 2
        while i < len(args):
            if args[i] == "--customer-ids" and i + 1 < len(args):
                customer_ids = [cid.strip() for cid in args[i+1].split(",")]
                i += 2
            elif args[i] == "--all-customers":
                customer_ids = get_all_customer_ids()
                i += 1
            elif args[i] == "--output" and i + 1 < len(args):
                output_format = args[i+1]
                i += 2
            elif args[i] == "--output-file" and i + 1 < len(args):
                output_file = args[i+1]
                i += 2
            elif trigger_type == "custom" and not custom_trigger:
                custom_trigger = args[i]
                i += 1
            else:
                i += 1
        
        # Validate arguments
        if trigger_type == "custom" and not custom_trigger:
            print(f"{Colors.RED}Please provide a description for the custom trigger.{Colors.END}")
            return None
            
        if not customer_ids:
            customer_ids = get_all_customer_ids()
            print(f"{Colors.YELLOW}No customer IDs specified, using all available customers.{Colors.END}")
            
        if output_format not in ["text", "json", "csv"]:
            print(f"{Colors.RED}Invalid output format: {output_format}. Using 'text' instead.{Colors.END}")
            output_format = "text"
        
        return (trigger_type, treatment_id, custom_trigger, customer_ids, output_format, output_file)
    
    # ==== MULTI-AGENT COMMANDS ====
    
    def do_multi_agent(self, arg):
        """Run the multi-agent processing system on specified customers.
        
        Usage: multi_agent [--customer-ids IDs] [--output-file filename]
        
        Examples:
          multi_agent --customer-ids U123,U124,U125
          multi_agent --customer-ids U123 --output-file single_agent_results.json
        """
        try:
            args = self._parse_multi_agent_args(arg)
            if not args:
                return
                
            customer_ids, output_file = args
            
            print(f"Running multi-agent processing for {Colors.BOLD}{len(customer_ids)}{Colors.END} customers...")
            
            # Call the orchestrator to process the batch
            result_data = self.orchestrator.process({
                "type": "process_batch",
                "customer_ids": customer_ids
            })
            
            self.multi_agent_results = result_data
            
            # Save results to file
            output_path = os.path.join(self.output_dir, output_file)
            with open(output_path, "w") as outfile:
                json.dump(result_data, outfile, indent=2)
                
            print(f"{Colors.GREEN}Results written to {Colors.BOLD}{output_path}{Colors.END}{Colors.GREEN}.{Colors.END}")
            
            # Print summary based on the result structure
            if isinstance(result_data, list):
                total = len(result_data)
                failed = sum(1 for item in result_data if item.get("status") == "error")
                successful = total - failed
                
                print(f"\n{Colors.BOLD}{Colors.BLUE}Processing complete:{Colors.END}")
                print(f"  Total customers: {Colors.BOLD}{total}{Colors.END}")
                print(f"  Successful: {Colors.GREEN}{successful}{Colors.END}")
                print(f"  Failed: {Colors.RED}{failed}{Colors.END}")
                
                # Display some result details
                if total > 0:
                    print(f"\n{Colors.BOLD}{Colors.BLUE}Result details:{Colors.END}")
                    for i, item in enumerate(result_data[:5], 1):  # Show first 5 only
                        status = item.get("status", "unknown")
                        status_color = Colors.GREEN if status == "success" else Colors.RED
                        cid = item.get("customer_id", "unknown")
                        message = item.get("message", "")
                        if len(message) > 80:
                            message = message[:77] + "..."
                            
                        print(f"  {i}. Customer {Colors.BOLD}{cid}{Colors.END}: {status_color}{status}{Colors.END}" + 
                              (f" - {message}" if message else ""))
                    
                    if total > 5:
                        print(f"  ... and {total-5} more (see output file for complete results)")
            elif isinstance(result_data, dict) and "summary" in result_data:
                summary = result_data["summary"]
                print(f"\n{Colors.BOLD}{Colors.BLUE}Processing complete:{Colors.END}")
                print(f"  Total customers: {Colors.BOLD}{summary['total_processed']}{Colors.END}")
                print(f"  Successful: {Colors.GREEN}{summary['successful']}{Colors.END}")
                print(f"  Failed: {Colors.RED}{summary['failed']}{Colors.END}")
            else:
                print(f"{Colors.GREEN}Processing complete. Results written to output file.{Colors.END}")
                
        except Exception as e:
            print(f"{Colors.RED}Error running multi-agent processing: {str(e)}{Colors.END}")
    
    def _parse_multi_agent_args(self, arg_string):
        """Parse multi-agent command arguments."""
        # Default values
        customer_ids = ["U123"]  # Default customer ID
        output_file = "multi_agent_results.json"  # Default output file
        
        if not arg_string:
            print(f"{Colors.YELLOW}Using default customer ID: U123{Colors.END}")
            print(f"{Colors.YELLOW}Using default output file: {output_file}{Colors.END}")
            return (customer_ids, output_file)
        
        # Parse the arguments using shlex to handle quoted strings properly
        args = shlex.split(arg_string)
        
        # Process arguments
        i = 0
        while i < len(args):
            if args[i] == "--customer-ids" and i + 1 < len(args):
                customer_ids = [cid.strip() for cid in args[i+1].split(",")]
                i += 2
            elif args[i] == "--output-file" and i + 1 < len(args):
                output_file = args[i+1]
                i += 2
            else:
                i += 1
        
        return (customer_ids, output_file)
    
    # ==== RESULT MANAGEMENT COMMANDS ====
    
    def do_save(self, arg):
        """Save current results to file.
        
        Usage: save <result_type> <filename>
        
        Examples:
          save trigger pet_interests.json
          save process network_treatment_results.json
          save multi_agent customer_processing.json
        """
        if not arg:
            print(f"{Colors.RED}Please provide a result type and filename.{Colors.END}")
            print(f"Valid result types: trigger, process, multi_agent")
            return
            
        args = arg.split(maxsplit=1)
        if len(args) < 2:
            print(f"{Colors.RED}Please provide both a result type and filename.{Colors.END}")
            return
            
        result_type = args[0]
        filename = args[1]
        
        # Determine which results to save
        results = None
        if result_type == "trigger":
            results = self.trigger_results
        elif result_type == "process":
            results = self.process_results
        elif result_type == "multi_agent":
            results = self.multi_agent_results
        else:
            print(f"{Colors.RED}Invalid result type: {result_type}{Colors.END}")
            print(f"Valid result types: trigger, process, multi_agent")
            return
            
        if not results:
            print(f"{Colors.RED}No {result_type} results to save. Run a {result_type} command first.{Colors.END}")
            return
            
        try:
            # Construct the full path in the output directory
            output_path = os.path.join(self.output_dir, os.path.basename(filename))
            
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            
            print(f"{Colors.GREEN}Results saved to {Colors.BOLD}{output_path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error saving results: {str(e)}{Colors.END}")
    
    def _save_results(self, results, output_format, output_file):
        """Save results in the specified format to file."""
        try:
            from src.trigger_customers_cli import format_trigger_results, format_process_results
            
            # Determine the appropriate formatter based on result type
            if "matches" in results:
                formatter = format_trigger_results
            elif "process_results" in results:
                formatter = format_process_results
            else:
                # Default to JSON dumping if no specific formatter found
                formatted_output = json.dumps(results, indent=2)
            
            # Format the output if a formatter was found
            if 'formatter' in locals():
                formatted_output = formatter(results, output_format)
            
            # Construct the full path in the output directory
            output_path = os.path.join(self.output_dir, os.path.basename(output_file))
            
            with open(output_path, "w") as f:
                f.write(formatted_output)
            
            print(f"{Colors.GREEN}Results saved to {Colors.BOLD}{output_path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error saving results: {str(e)}{Colors.END}")
            
    # ==== HELP AND DOCUMENTATION ====
    
    def do_help_categories(self, arg):
        """Show available command categories."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}Command Categories:{Colors.END}")
        print(f"  {Colors.BOLD}customers{Colors.END}: list_customers, load")
        print(f"  {Colors.BOLD}triggers{Colors.END}: list_triggers, trigger")
        print(f"  {Colors.BOLD}treatments{Colors.END}: process")
        print(f"  {Colors.BOLD}multi-agent{Colors.END}: multi_agent")
        print(f"  {Colors.BOLD}results{Colors.END}: save")
        print(f"  {Colors.BOLD}system{Colors.END}: exit, quit, help")
        print(f"\nType {Colors.CYAN}help <command>{Colors.END} for detailed information on a specific command.")

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
