import json
import os
import logging
from typing import List, Dict, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Update the data_root to be relative to this file's location
data_root = os.path.join(os.path.dirname(__file__), "data")

def load_json_file(filepath: str):
    """
    Load a JSON file and return its contents.
    If the JSON is an object with a "data" key, that value is returned.
    """
    with open(filepath, 'r') as file:
        data = json.load(file)
    # If data is a dict and contains a "data" key, return that
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data

def get_call_transcripts(customer_id: str) -> list:
    """
    Returns the call transcripts for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'call_transcripts.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_web_transcripts(customer_id: str) -> list:
    """
    Returns the web transcripts for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'web_transcripts.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_web_clicks(customer_id: str) -> list:
    """
    Returns the web clicks for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'web_clicks.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_network_data(customer_id: str) -> list:
    """
    Returns the network performance data for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'network_data.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_offer_recommendations(customer_id: str) -> list:
    """
    Returns the offer recommendations for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'offer_recommendations.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_churn_scores(customer_id: str) -> list:
    """
    Returns the churn score records for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'churn_score.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_usage_data(customer_id: str) -> list:
    """
    Returns the usage data records for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'usage_data.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def get_billing_data(customer_id: str) -> list:
    """
    Returns the billing data records for the given customer from the data_root folder.
    """
    filepath = os.path.join(data_root, 'billing_data.json')
    records = load_json_file(filepath)
    return [record for record in records if isinstance(record, dict) and record.get("customer_id") == customer_id]

def load_customer_data(customer_id: str) -> Dict[str, Any]:
    """
    Load all data for a single customer from all data sources
    """
    logger.debug(f"Loading data for customer {customer_id}")
    
    data_types = {
        'call_transcripts': 'call_transcripts.json',
        'web_transcripts': 'web_transcripts.json',
        'web_clicks': 'web_clicks.json',
        'network_data': 'network_data.json',
        'offer_recommendations': 'offer_recommendations.json',
        'churn_scores': 'churn_score.json',
        'usage_data': 'usage_data.json',
        'billing_data': 'billing_data.json'
    }
    
    customer_data = {}
    
    # Load data from each source
    for data_type, filename in data_types.items():
        filepath = os.path.join(data_root, filename)
        try:
            logger.debug(f"Loading {data_type} for customer {customer_id}")
            records = load_json_file(filepath)
            customer_records = [r for r in records if isinstance(r, dict) and r.get("customer_id") == customer_id]
            customer_data[data_type] = customer_records
            logger.debug(f"Found {len(customer_records)} {data_type} records for customer {customer_id}")
        except Exception as e:
            logger.error(f"Error loading {filename} for customer {customer_id}: {str(e)}")
            customer_data[data_type] = []
    
    return customer_data

def load_all_customer_data(customer_ids: List[str]) -> Dict[str, Any]:
    """
    Load data for multiple customers in parallel
    """
    logger.debug(f"Loading data for customers: {customer_ids}")
    all_data = {}
    
    for customer_id in customer_ids:
        try:
            logger.debug(f"Loading data for customer {customer_id}")
            customer_data = load_customer_data(customer_id)
            all_data[customer_id] = customer_data
            logger.debug(f"Successfully loaded data for customer {customer_id}")
        except Exception as e:
            logger.error(f"Error loading data for customer {customer_id}: {str(e)}")
            raise
    
    logger.debug(f"Successfully loaded data for all {len(customer_ids)} customers")
    return all_data

def build_customer_journey(customer_id: str, all_data: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> List[Dict[str, Any]]:
    """
    Combines all events for a customer into a single ordered journey.
    Each event is expected to have a "date" field in the format YYYY-MM-DD.

    Args:
        customer_id: The customer ID to build journey for
        all_data: Optional pre-loaded data for all customers

    Returns:
        List of events in chronological order
    """
    events = []
    
    if all_data is None:
        # Legacy mode - load data individually
        events.extend(get_call_transcripts(customer_id))
        events.extend(get_web_transcripts(customer_id))
        events.extend(get_web_clicks(customer_id))
        events.extend(get_network_data(customer_id))
        events.extend(get_offer_recommendations(customer_id))
        events.extend(get_churn_scores(customer_id))
        events.extend(get_usage_data(customer_id))
        events.extend(get_billing_data(customer_id))
    else:
        # Use pre-loaded data
        for data_type, records in all_data.items():
            customer_records = [
                record for record in records 
                if isinstance(record, dict) and record.get("customer_id") == customer_id
            ]
            events.extend(customer_records)
    
    # Sort events by date
    events.sort(key=lambda event: event.get("date", ""))
    
    return events

def get_all_customer_ids() -> list:
    """
    Returns a list of all customer IDs found in the data files.
    """
    # Load customer IDs from call_transcripts.json as it should contain all customers
    filepath = os.path.join(data_root, 'call_transcripts.json')
    records = load_json_file(filepath)
    
    # Extract unique customer IDs
    customer_ids = list(set(record.get("customer_id") for record in records 
                           if isinstance(record, dict) and "customer_id" in record))
    
    return sorted(customer_ids)

if __name__ == "__main__":
    # For customer 'U123', retrieve data using the latest functions from the adjusted data_root folder.
    customer_id = "U123"

    #clicks = get_web_clicks(customer_id)
    #print("Web Clicks for {}: {}".format(customer_id, clicks))

    #transcripts = get_web_transcripts(customer_id)
    #print("Web Transcripts for {}: {}".format(customer_id, transcripts))

    #calls = get_call_transcripts(customer_id)
    #print("Call Transcripts for {}: {}".format(customer_id, calls))

    #network = get_network_data(customer_id)
    #print("Network Data for {}: {}".format(customer_id, network))

    #offers = get_offer_recommendations(customer_id)
    #print("Offer Recommendations for {}: {}".format(customer_id, offers))

    #churn = get_churn_scores(customer_id)
    #print("Churn Score Data for {}: {}".format(customer_id, churn))

    #usage = get_usage_data(customer_id)
    #print("Usage Data for {}: {}".format(customer_id, usage))

    #billing = get_billing_data(customer_id)
    #print("Billing Data for {}: {}".format(customer_id, billing))
    
    # Build and display the complete customer journey
    journey = build_customer_journey(customer_id)
    print("Customer Journey for {}: {}".format(customer_id, journey))


