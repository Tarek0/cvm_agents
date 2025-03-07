"""
CVM (Customer Value Management) System for Telecommunications.
Multi-Agent implementation for determining customer treatments.
"""
import os
import json
import argparse
import logging
from datetime import datetime
from typing import List

# Import the multi-agent orchestrator
from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def main() -> None:
    """
    Main function to process customer journey data using the multi-agent architecture.
    """
    parser = argparse.ArgumentParser(description="Process customer journey data using multi-agent architecture.")
    parser.add_argument("--customer_ids", help="Comma separated list of Customer IDs", default="U123")
    parser.add_argument("--output_file", help="Output JSON file", default="multi_agent_results.json")
    parser.add_argument("--log_level", help="Logging level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--max_workers", help="Maximum number of parallel workers", type=int, default=4)
    args = parser.parse_args()

    # Set logging level from command line argument
    logging.getLogger().setLevel(args.log_level)

    # Parse customer IDs
    customer_ids = [cid.strip() for cid in args.customer_ids.split(",")]
    
    try:
        logger.info(f"Starting multi-agent CVM processing for {len(customer_ids)} customers")
        
        # Initialize the orchestrator agent
        config = {
            "model_id": os.environ.get("MODEL_ID", "gpt-4o"),
            "enable_cache": True,
            "max_retries": 3,
            "timeout": 30
        }
        orchestrator = OrchestratorAgent(config)
        
        # Process the customers
        logger.info("Processing customers through multi-agent system")
        result_data = orchestrator.process({
            "type": "process_batch",
            "customer_ids": customer_ids
        })
        
        # Write results to output file
        with open(args.output_file, "w") as outfile:
            json.dump(result_data, outfile, indent=2)
        logger.info(f"Results written to {args.output_file}")
        
        # Print summary
        summary = result_data["summary"]
        logger.info("Processing complete:")
        logger.info(f"  Total customers: {summary['total_processed']}")
        logger.info(f"  Successful: {summary['successful']}")
        logger.info(f"  Failed: {summary['failed']}")
        
    except Exception as e:
        logger.error(f"Failed to process customers: {str(e)}")
        raise

if __name__ == "__main__":
    main() 