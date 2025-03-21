"""
CVM Control Center Application

A user interface for interacting with the CVM (Customer Value Management) System.
"""
import streamlit as st
import sys
import os
import json
import logging
import io
from datetime import datetime
from pathlib import Path

# Ensure we can import from the parent directory
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import orchestrator and necessary components
from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config

# Set up logging for the Streamlit UI
class StreamlitLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def emit(self, record):
        log_entry = self.formatter.format(record)
        self.logs.append(log_entry)
        # Keep only the last 100 log entries to prevent the list from growing too large
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

# Initialize the log handler if it doesn't exist in session state
if 'log_handler' not in st.session_state:
    st.session_state.log_handler = StreamlitLogHandler()
    # Set up the root logger to use our custom handler
    root_logger = logging.getLogger()
    root_logger.addHandler(st.session_state.log_handler)
    # Set the level based on environment or default to INFO
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    root_logger.setLevel(getattr(logging, log_level))

# Function to display logs in a collapsible box
def display_logs(section_title="System Logs"):
    # Add a horizontal rule to separate logs from content above
    st.markdown("---")
    st.write(f"## {section_title}")
    with st.expander(section_title, expanded=False):
        if not st.session_state.log_handler.logs:
            st.info("No logs available yet.")
        else:
            # Create a text area with the logs
            log_text = "\n".join(st.session_state.log_handler.logs)
            st.text_area("Real-time logs", log_text, height=200)
            # Add a button to clear logs
            if st.button("Clear Logs"):
                st.session_state.log_handler.logs = []
                st.rerun()

# Set page configuration - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="CVM Expert",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for red branding - added after set_page_config
st.markdown("""
<style>
    /* Main theme colors - red branding */
    :root {
        --primary-color: #e53935;
        --secondary-color: #ffcdd2;
        --background-color: #ffffff;
        --text-color: #212121;
    }
    
    /* Sidebar and header styling */
    .css-1d391kg, .css-1lsmgbg {
        background-color: #f8f8f8;
    }
    
    /* Headers with red color */
    h1, h2, h3 {
        color: var(--primary-color) !important;
    }
    
    /* Custom button styling */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    
    .stButton>button:hover {
        background-color: #c62828;
    }
    
    /* Info boxes with red border */
    .alert-info {
        background-color: #ffebee;
        border-left: 4px solid var(--primary-color);
    }
    
    /* Metric styling */
    .css-1wivap2 {
        color: var(--primary-color);
    }
</style>
""", unsafe_allow_html=True)

# Initialize the orchestrator agent with proper config
@st.cache_resource
def get_orchestrator():
    """Return a cached instance of the OrchestratorAgent"""
    config = load_config()
    
    # Add any necessary settings
    config.settings["model_id"] = os.environ.get("MODEL_ID", "gpt-4o")
    config.settings["enable_cache"] = True
    config.settings["max_retries"] = 3
    config.settings["timeout"] = 30
    
    return OrchestratorAgent(config)

# Load the orchestrator agent
orchestrator = get_orchestrator()

# Define pages for navigation
PAGES = {
    "Home Page": "dashboard",
    "Agentic NBA": "process_customer",
    "Gen AI Triggers": "trigger_management",
    "Treatment Management": "treatment_management"
}

# Initialize session state for navigation if not already set
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# Sidebar navigation
st.sidebar.title("CVM Expert: Control Center")
# Using a red-themed analytics icon
st.sidebar.image("https://img.icons8.com/color/96/000000/combo-chart--v2.png", width=100)

# Red separator below title
st.sidebar.markdown('<hr style="border-top: 3px solid #e53935;">', unsafe_allow_html=True)

# Get all available customer IDs for display throughout the app
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_customer_ids():
    """Retrieve all available customer IDs"""
    try:
        # Import here to avoid circular imports
        from src.tools.api_v2 import get_all_customer_ids as api_get_all_customer_ids
        return api_get_all_customer_ids()
    except Exception as e:
        st.error(f"Error loading customer IDs: {str(e)}")
        return []

# Check if we need to change pages based on session state
page_to_display = st.session_state.page
# Find the key (page name) that maps to the current page value
current_page_key = next((key for key, value in PAGES.items() if value == page_to_display), "Dashboard")

# Navigation selection with the current page pre-selected
selected_page = st.sidebar.radio("Navigation", list(PAGES.keys()), index=list(PAGES.keys()).index(current_page_key))

# Update session state if sidebar selection changes
if PAGES[selected_page] != st.session_state.page:
    st.session_state.page = PAGES[selected_page]

# Display page heading
st.title(f"CVM Expert")
st.markdown('<hr style="border-top: 2px solid #e53935; margin-bottom: 20px;">', unsafe_allow_html=True)

# Dashboard page
def dashboard_page():
    st.write("## Welcome to the CVM Expert Control Center")
    st.write("This CVM Expert - control center provides a centralized interface for managing the CVM activities.")

    # Add a descriptive explanation of the dashboard
    with st.expander("About the CVM Expert Control Center", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>About CVM Expert Control Center</strong>
            <p>A centralized dashboard providing key metrics and system status for your CVM operations. View customer counts, available treatments, system status, and access frequent actions all in one place.</p>
        </div>
        """, unsafe_allow_html=True)

    # Display overview cards in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total Customers", value=len(get_all_customer_ids()))
    
    with col2:
        treatments_count = len(orchestrator.treatment_manager.get_all_treatments())
        st.metric(label="Available Treatments", value=treatments_count)
    
    with col3:
        # Just count the predefined triggers plus "custom"
        st.metric(label="Available Triggers", value=6)
    
    # Display recent activity or system status
    st.write("## System Status")
    st.markdown('<div class="alert-info" style="padding: 20px; border-radius: 5px;">'
               '<strong>All agents are operational and ready to process requests.</strong>'
               '</div>', unsafe_allow_html=True)
    
    # Quick actions
    st.write("## Quick Actions")
    
    quick_col1, quick_col2 = st.columns(2)
    
    with quick_col1:
        if st.button("View Available Treatments"):
            logging.info("Navigating to Treatment Management page")
            st.session_state.page = "treatment_management"
            st.rerun()
    
    with quick_col2:
        if st.button("Process a Customer"):
            logging.info("Navigating to Process Customer page")
            st.session_state.page = "process_customer"
            st.rerun()
    
    # Display system logs at the bottom of the page
    display_logs()

# Customer processing page
def process_customer_page():
    st.write("## Agentic NBA")
    st.write("Process customers through the CVM system for personalized treatment recommendations.")
    
    # Add a descriptive explanation of the customer processing
    with st.expander("What is Agentic NBA?", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>What is Agentic NBA?</strong>
            <p>Agentic NBA uses AI to automatically determine and apply the best next-best-action for each customer. Process individuals or batches, filter available treatments, and get detailed justifications for each recommendation.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Get all available treatments to allow filtering
    treatment_filter_expander = st.expander("Treatment Selection Options", expanded=False)
    
    # Get all available treatments
    with treatment_filter_expander:
        st.write("### Limit Available Treatments")
        st.write("Select which treatments the system can choose from. If none are selected, all treatments will be available.")
        st.info("All treatments are selected by default. Use the buttons below to adjust your selection.")
        
        with st.spinner("Loading treatments..."):
            logging.info("Loading available treatments")
            treatments_result = orchestrator.process({
                "type": "list_treatments"
            })
            
            if treatments_result.get("status") == "success":
                logging.info(f"Successfully loaded {len(treatments_result.get('treatments', []))} treatments")
                all_treatments = treatments_result.get("treatments", [])
                
                # Store treatments by ID for lookup
                treatments_by_id = {t.get("id"): t for t in all_treatments}
                
                # Create options for display with format "Display Name (ID)"
                treatment_options = [f"{t.get('display_name', 'Unknown')} ({t.get('id')})" for t in all_treatments]
                
                # Initialize session state for selected treatments if it doesn't exist
                if "selected_treatments" not in st.session_state:
                    # Default to all treatments selected
                    st.session_state.selected_treatments = treatment_options
                
                # Add Select All and Clear All buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All Treatments", key="select_all_treatments"):
                        logging.info("Selecting all treatments")
                        st.session_state.selected_treatments = treatment_options
                        st.rerun()
                
                with col2:
                    if st.button("Clear All Treatments", key="clear_all_treatments"):
                        logging.info("Clearing all selected treatments")
                        st.session_state.selected_treatments = []
                        st.rerun()
                
                # Create filters for common channels/types
                st.write("### Filter by Treatment Type")
                
                # Remove the checkboxes and directly categorize treatments
                
                # Group treatments by type
                sms_options = [option for option in treatment_options if "sms" in option.lower()]
                email_options = [option for option in treatment_options if "email" in option.lower()]
                call_options = [option for option in treatment_options if "call" in option.lower()]
                
                # All other options
                filtered_options = sms_options + email_options + call_options
                other_options = [option for option in treatment_options if option not in filtered_options]
                
                # Display treatment categories with select buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if sms_options:
                        st.write("#### SMS Treatments")
                        if st.button("Select All SMS", key="select_all_sms"):
                            current = set(st.session_state.selected_treatments)
                            st.session_state.selected_treatments = list(current.union(set(sms_options)))
                            st.rerun()
                
                with col2:
                    if email_options:
                        st.write("#### Email Treatments")
                        if st.button("Select All Email", key="select_all_email"):
                            current = set(st.session_state.selected_treatments)
                            st.session_state.selected_treatments = list(current.union(set(email_options)))
                            st.rerun()
                
                with col3:
                    if call_options:
                        st.write("#### Call Treatments")
                        if st.button("Select All Call", key="select_all_call"):
                            current = set(st.session_state.selected_treatments)
                            st.session_state.selected_treatments = list(current.union(set(call_options)))
                            st.rerun()
                
                # Display count of selected treatments
                st.write(f"### Selected Treatments: {len(st.session_state.selected_treatments)}/{len(treatment_options)}")
                
                # Other treatments section
                if other_options:
                    st.write("#### Other Treatments")
                    if st.button("Select All Other", key="select_all_other"):
                        current = set(st.session_state.selected_treatments)
                        st.session_state.selected_treatments = list(current.union(set(other_options)))
                        st.rerun()
                
                # Show count of selected treatments
                if st.session_state.selected_treatments:
                    st.write(f"### Selected Treatments: {len(st.session_state.selected_treatments)}/{len(treatment_options)}")
                
                # Let users select which treatments to enable
                selected_treatment_options = st.multiselect(
                    "Select Treatments to Include", 
                    treatment_options,
                    default=st.session_state.selected_treatments
                )
                
                # Update session state
                st.session_state.selected_treatments = selected_treatment_options
                
                # Extract treatment IDs from the selected options
                selected_treatment_ids = []
                for option in selected_treatment_options:
                    # Extract ID from the format "Display Name (ID)"
                    treatment_id = option.split("(")[-1].rstrip(")")
                    selected_treatment_ids.append(treatment_id)
                
                # Show a warning if no treatments selected
                if not selected_treatment_ids:
                    st.info("No treatments selected. All available treatments will be considered.")
                else:
                    # Show selected treatments as a list - don't use an expander here since we're already in one
                    st.write("### Selected Treatments")
                    for treatment in selected_treatment_options:
                        st.write(f"- {treatment}")
            else:
                st.error(f"Error loading treatments: {treatments_result.get('message', 'Unknown error')}")
                selected_treatment_ids = []
    
    # Customer Processing Section (combining functionality from both tabs)
    st.write("## Customer Processing")
    
    # Get all customer IDs
    all_customer_ids = get_all_customer_ids()
    
    # Initialize session state for selected customers if it doesn't exist
    if "batch_selected_customers" not in st.session_state:
        st.session_state.batch_selected_customers = []
    
    # Check if we have pre-selected customers from trigger page
    if hasattr(st.session_state, 'triggered_customers') and st.session_state.triggered_customers:
        st.session_state.batch_selected_customers = st.session_state.triggered_customers
        # Clear the triggered customers after using it
        st.session_state.triggered_customers = []
    
    # Customer selection with session state
    selected_customers = st.multiselect("Select Customers", all_customer_ids, 
                                        default=st.session_state.batch_selected_customers)
    
    # Update session state when the selection changes
    st.session_state.batch_selected_customers = selected_customers
    
    # Quick select buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="select_all_batch"):
            st.session_state.batch_selected_customers = all_customer_ids
            st.rerun()
    
    with col2:
        if st.button("Clear Selection", key="clear_all_batch"):
            st.session_state.batch_selected_customers = []
            st.rerun()
    
    # Input field for customer IDs as text
    custom_ids = st.text_input("Or Enter Customer IDs (comma-separated)")
    
    # Process button
    if st.button("Process Customers with Agentic NBA", key="process_batch"):
        # Combine selected IDs and custom IDs
        ids_to_process = selected_customers
        
        if custom_ids:
            custom_id_list = [cid.strip() for cid in custom_ids.split(",")]
            ids_to_process.extend(custom_id_list)
        
        # Remove duplicates
        ids_to_process = list(set(ids_to_process))
        
        if not ids_to_process:
            st.error("Please select at least one customer to process")
            logging.error("No customers selected for processing")
        else:
            logging.info(f"Starting to process {len(ids_to_process)} customers")
            with st.spinner(f"Processing {len(ids_to_process)} customers..."):
                # Process each customer with optimal treatment selection
                results = []
                progress_bar = st.progress(0)
                
                # Create API request for batch processing
                api_request = {
                    "type": "process_batch",
                    "customer_ids": ids_to_process
                }
                
                # Add treatment filtering if treatments are selected
                if selected_treatment_ids:
                    logging.info(f"Filtering to {len(selected_treatment_ids)} selected treatments")
                    api_request["allowed_treatments"] = selected_treatment_ids
                
                # Process all customers in a single batch request
                logging.info(f"Sending batch processing request: {str(api_request)}")
                results = orchestrator.process(api_request)
                logging.info("Batch processing completed")
                
                st.success(f"Batch processing complete: {len(ids_to_process)} customers processed")
                
                # Only proceed if we have results to display
                if results:
                    # Display results in a table
                    result_data = []
                    
                    # Count different error types
                    permission_errors = 0
                    allocation_errors = 0
                    other_errors = 0
                    successful = 0
                    
                    # Process the list of results returned by the batch API call
                    for r in results:
                        customer_id = r.get("customer_id", "unknown")
                        status = r.get("status", "unknown")
                        
                        if status == "success":
                            successful += 1
                        
                        # Get appropriate message based on status
                        message = r.get("message", "")
                        explanation = r.get("explanation", "")
                        
                        if status == "error":
                            if "error" in r:
                                message = r.get("error", "")
                            elif "permission" in explanation.lower():
                                message = "Permission Error: " + explanation
                                permission_errors += 1
                            elif "allocat" in explanation.lower():
                                message = "Allocation Error: " + explanation
                                allocation_errors += 1
                            else:
                                message = explanation or message
                                other_errors += 1
                        elif status == "success":
                            if "explanation" in r:
                                message = r.get("explanation")[:100] + "..." if len(r.get("explanation", "")) > 100 else r.get("explanation", "")
                            else:
                                message = "Success"
                        
                        # Get the treatment information
                        if isinstance(r.get("selected_treatment"), dict):
                            treatment_name = r.get("selected_treatment", {}).get("display_name", "Unknown")
                        elif isinstance(r.get("selected_treatment"), str):
                            treatment_name = r.get("selected_treatment", "Unknown")
                        else:
                            treatment_name = "Unknown"
                        
                        result_data.append({
                            "Customer ID": customer_id,
                            "Treatment": treatment_name,
                            "Explanation": message
                        })
                    
                    # Show summary statistics
                    st.write("### Processing Summary")
                    summary_cols = st.columns(4)
                    with summary_cols[0]:
                        st.metric("Successful", successful)
                    
                    failed = len(results) - successful
                    if failed > 0:
                        with summary_cols[1]:
                            st.metric("Failed", failed, delta=-failed, delta_color="inverse")
                        if permission_errors > 0:
                            with summary_cols[2]:
                                st.metric("Permission Errors", permission_errors, delta=-permission_errors, delta_color="inverse")
                        if allocation_errors > 0:
                            with summary_cols[3]:
                                st.metric("Allocation Errors", allocation_errors, delta=-allocation_errors, delta_color="inverse")
                    
                    # Display the results table
                    st.write("### Processing Results")
                    st.dataframe(result_data, use_container_width=True)
                    
                    # Offer download of results
                    import json as json_module
                    result_str = json_module.dumps(results, indent=2)
                    st.download_button(
                        label="Download Results (JSON)",
                        data=result_str,
                        file_name="agentic_nba_results.json",
                        mime="application/json"
                    )

    # Display system logs at the bottom of the page
    display_logs()

# Trigger management page
def trigger_management_page():
    st.write("## Gen AI Triggers")
    st.write("Identify customers based on specific trigger criteria.")
    
    # Add a descriptive explanation of trigger management
    with st.expander("What is a Gen AI Trigger?", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>What is a Gen AI Trigger?</strong>
            <p>Identify customers matching specific criteria using AI-powered analysis. Use predefined triggers (network issues, billing disputes, churn risk) or create custom ones with natural language. Export results or immediately process matched customers with appropriate treatments.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Remove logs display from here
    
    # Trigger type selection
    trigger_types = ["network_issues", "billing_disputes", "churn_risk", 
                    "high_value", "roaming_issues", "custom"]
    
    selected_trigger = st.selectbox("Select Trigger Type", trigger_types)
    logging.debug(f"Selected trigger type: {selected_trigger}")
    
    # For custom triggers, provide a description field
    custom_description = ""
    if selected_trigger == "custom":
        custom_description = st.text_area("Custom Trigger Description", 
                                         "Describe what to look for in customer interactions")
    
    # Customer selection - all or specific
    use_all_customers = st.checkbox("Use All Available Customers")
    
    specific_customers = []
    if not use_all_customers:
        all_customer_ids = get_all_customer_ids()
        specific_customers = st.multiselect("Select Specific Customers", all_customer_ids)
    
    # Output format
    output_format = st.selectbox("Output Format", ["text", "json", "csv"])
    
    # Trigger button
    if st.button("Trigger Customers"):
        logging.info(f"Starting customer triggering with trigger type: {selected_trigger}")
        if selected_trigger == "custom":
            logging.info(f"Custom trigger description: {custom_description}")
        
        with st.spinner("Identifying customers..."):
            # Build request message
            message = {
                "type": "trigger_customers",
                "trigger_type": selected_trigger,
                "output_format": output_format
            }
            
            # Add custom description if needed
            if selected_trigger == "custom" and custom_description:
                message["custom_trigger"] = {"description": custom_description}
            
            # Add customer IDs
            if use_all_customers:
                message["use_all_customers"] = True
                # Also include the actual customer IDs
                customer_ids = get_all_customer_ids()
                message["customer_ids"] = customer_ids
                logging.info(f"Using all {len(customer_ids)} customers")
            else:
                message["customer_ids"] = specific_customers
                logging.info(f"Using {len(specific_customers)} selected customers")
            
            # Process the trigger request
            logging.info(f"Sending trigger request: {str(message)}")
            result = orchestrator.process(message)
            logging.info("Trigger processing completed")
            
            # Display results
            if result.get("status") == "success":
                match_count = result.get('total_matches', 0)
                logging.info(f"Found {match_count} matching customers")
                st.success(f"Found {match_count} matching customers")
                
                # Display matches in a table
                if result.get("matches"):
                    match_data = []
                    for match in result.get("matches"):
                        match_data.append({
                            "Customer ID": match.get("customer_id"),
                            "Reason": match.get("reason", "")
                        })
                    
                    st.write("### Matching Customers")
                    st.table(match_data)
                    
                    # Option to process these customers
                    if st.button("Process These Customers"):
                        logging.info(f"Sending {match_count} matched customers to processing page")
                        st.session_state.triggered_customers = [m.get("customer_id") for m in result.get("matches")]
                        st.session_state.page = "process_customer"
                        st.rerun()
            else:
                error_msg = result.get('message', 'Unknown error')
                logging.error(f"Error during trigger processing: {error_msg}")
                st.error(f"Error: {error_msg}")

    # Display system logs at the bottom of the page
    display_logs()

# Treatment management page
def treatment_management_page():
    st.write("## Treatment Management")
    
    # Add a descriptive explanation of treatment management
    with st.expander("What is Treatment Management?", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>What is Treatment Management?</strong>
            <p>Control the actions your CVM system can take with customers. View, add, update, or remove treatments, and configure resource limits and priorities. Easily manage your marketing action inventory to meet evolving customer needs.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Remove logs display from here
    
    # Create tabs for different treatment operations
    tab1, tab2, tab3, tab4 = st.tabs(["List Treatments", "Add Treatment", "Update Treatment", "Remove Treatment"])
    
    with tab1:
        st.write("### Available Treatments")
        
        # Option to show only custom treatments
        custom_only = st.checkbox("Show Custom Treatments Only")
        
        # Get treatments
        with st.spinner("Loading treatments..."):
            logging.info("Loading treatments" + (" (custom only)" if custom_only else ""))
            treatments_result = orchestrator.process({
                "type": "list_treatments",
                "custom_only": custom_only
            })
            
            if treatments_result.get("status") == "success":
                treatments = treatments_result.get("treatments", [])
                logging.info(f"Successfully loaded {len(treatments)} treatments")
                
                # Display treatments in a table
                if treatments:
                    treatment_data = []
                    for t in treatments:
                        treatment_data.append({
                            "ID": t.get("id"),
                            "Name": t.get("display_name"),
                            "Description": t.get("description"),
                            "Custom": "Yes" if t.get("is_custom") else "No"
                        })
                    
                    st.table(treatment_data)
                else:
                    st.info("No treatments found")
                    logging.info("No treatments found with the current filter")
            else:
                error_msg = treatments_result.get('message', 'Unknown error')
                logging.error(f"Error loading treatments: {error_msg}")
                st.error(f"Error: {error_msg}")
    
    with tab2:
        st.write("### Add New Treatment")
        
        # Treatment input options
        treatment_name = st.text_input("Treatment Name")
        treatment_description = st.text_area("Treatment Description")
        
        # Advanced options
        with st.expander("Advanced Options"):
            max_per_day = st.number_input("Maximum Per Day", min_value=1, value=10)
            cost_per_contact = st.number_input("Cost Per Contact (£)", min_value=0.0, value=1.0)
            priority = st.slider("Priority (1-5)", min_value=1, max_value=5, value=3)
        
        # Add button
        if st.button("Add Treatment"):
            if not treatment_name or not treatment_description:
                st.error("Treatment name and description are required")
                logging.error("Attempted to add treatment without name or description")
            else:
                logging.info(f"Adding new treatment: {treatment_name}")
                # Create treatment JSON
                treatment_json = {
                    "display_name": treatment_name,
                    "description": treatment_description,
                    "constraints": {
                        "max_per_day": max_per_day,
                        "cost_per_contact_pounds": cost_per_contact,
                        "priority": priority
                    }
                }
                
                with st.spinner("Adding treatment..."):
                    logging.info(f"Sending add treatment request: {str(treatment_json)}")
                    result = orchestrator.process({
                        "type": "add_treatment",
                        "treatment_data": treatment_json
                    })
                    
                    if result.get("status") == "success":
                        treatment_id = result.get('treatment_id')
                        logging.info(f"Treatment added successfully with ID: {treatment_id}")
                        st.success(f"Treatment added successfully with ID: {treatment_id}")
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        logging.error(f"Error adding treatment: {error_msg}")
                        st.error(f"Error: {error_msg}")
    
    with tab3:
        st.write("### Update Treatment")
        
        # Get all treatment IDs
        with st.spinner("Loading treatments..."):
            logging.info("Loading treatments for update")
            treatments_result = orchestrator.process({
                "type": "list_treatments"
            })
            
            if treatments_result.get("status") == "success":
                treatments = treatments_result.get("treatments", [])
                treatment_ids = [t.get("id") for t in treatments]
                logging.info(f"Loaded {len(treatments)} treatments for update selection")
                
                # Select treatment to update
                selected_treatment_id = st.selectbox("Select Treatment", treatment_ids)
                
                # Get current treatment details
                current_treatment = next((t for t in treatments if t.get("id") == selected_treatment_id), {})
                
                # Update fields
                new_description = st.text_area("New Description", 
                                             value=current_treatment.get("description", ""))
                
                # Update button
                if st.button("Update Treatment"):
                    logging.info(f"Updating treatment: {selected_treatment_id}")
                    with st.spinner("Updating treatment..."):
                        result = orchestrator.process({
                            "type": "update_treatment",
                            "treatment_id": selected_treatment_id,
                            "description": new_description
                        })
                        
                        if result.get("status") == "success":
                            logging.info(f"Treatment {selected_treatment_id} updated successfully")
                            st.success(f"Treatment {selected_treatment_id} updated successfully!")
                        else:
                            error_msg = result.get('message', 'Unknown error')
                            logging.error(f"Error updating treatment: {error_msg}")
                            st.error(f"Error: {error_msg}")
            else:
                error_msg = treatments_result.get('message', 'Unknown error')
                logging.error(f"Error loading treatments for update: {error_msg}")
                st.error(f"Error loading treatments: {error_msg}")
    
    with tab4:
        st.write("### Remove Treatment")
        
        # Get all treatment IDs
        with st.spinner("Loading treatments..."):
            logging.info("Loading custom treatments for removal")
            treatments_result = orchestrator.process({
                "type": "list_treatments",
                "custom_only": True  # Only allow removing custom treatments
            })
            
            if treatments_result.get("status") == "success":
                treatments = treatments_result.get("treatments", [])
                treatment_ids = [t.get("id") for t in treatments]
                logging.info(f"Loaded {len(treatments)} custom treatments for potential removal")
                
                if treatment_ids:
                    # Select treatment to remove
                    selected_treatment_id = st.selectbox("Select Treatment to Remove", treatment_ids)
                    
                    # Confirmation
                    st.warning("This action cannot be undone!")
                    confirm = st.checkbox("I understand that this treatment will be permanently removed")
                    
                    # Remove button
                    if st.button("Remove Treatment") and confirm:
                        logging.info(f"Removing treatment: {selected_treatment_id}")
                        with st.spinner("Removing treatment..."):
                            result = orchestrator.process({
                                "type": "remove_treatment",
                                "treatment_id": selected_treatment_id
                            })
                            
                            if result.get("status") == "success":
                                logging.info(f"Treatment {selected_treatment_id} removed successfully")
                                st.success(f"Treatment {selected_treatment_id} removed successfully!")
                            else:
                                error_msg = result.get('message', 'Unknown error')
                                logging.error(f"Error removing treatment: {error_msg}")
                                st.error(f"Error: {error_msg}")
                else:
                    st.info("No custom treatments available to remove")
                    logging.info("No custom treatments available to remove")
            else:
                error_msg = treatments_result.get('message', 'Unknown error')
                logging.error(f"Error loading treatments for removal: {error_msg}")
                st.error(f"Error loading treatments: {error_msg}")

    # Display system logs at the bottom of the page
    display_logs()

# Display the selected page based on session state
if st.session_state.page == "dashboard":
    dashboard_page()
elif st.session_state.page == "process_customer":
    process_customer_page()
elif st.session_state.page == "trigger_management":
    trigger_management_page()
elif st.session_state.page == "treatment_management":
    treatment_management_page() 