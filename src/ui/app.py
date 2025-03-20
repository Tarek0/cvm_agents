"""
CVM Control Center Application

A user interface for interacting with the CVM (Customer Value Management) System.
"""
import streamlit as st
import sys
import os
import json
from pathlib import Path

# Ensure we can import from the parent directory
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import orchestrator and necessary components
from src.agents.orchestrator_agent import OrchestratorAgent
from src.utils.config import load_config

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
            <p>The Dashboard provides a overview of your Agentic CVM system and key metrics. Here you can:</p>
            <ul>
                <li>View the total number of customers in your database</li>
                <li>See the count of available treatments that can be applied</li>
                <li>Monitor the number of Gen AI trigger types available for customer identification</li>
                <li>Check the operational status of all system components</li>
                <li>Access quick links to frequently used functions</li>
            </ul>
            <p>This dashboard is designed to give you a quick snapshot of system capabilities and health at a glance.</p>
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
            st.session_state.page = "treatment_management"
            st.rerun()
    
    with quick_col2:
        if st.button("Process a Customer"):
            st.session_state.page = "process_customer"
            st.rerun()

# Customer processing page
def process_customer_page():
    st.write("## Agentic NBA")
    st.write("Process customers through the CVM system for personalized treatment recommendations.")
    
    # Add a descriptive explanation of the customer processing
    with st.expander("What is Agentic NBA?", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>What is Agentic NBA?</strong>
            <p>This feature allows you to process customers through the CVM system for personalized treatment recommendations. With Agentic NBA, you can:</p>
            <ul>
                <li>Process an individual customer or multiple customers at once</li>
                <li>Have the system intelligently determine the best treatment for each customer</li>
                <li>Limit which treatments the system can select from</li>
                <li>Analyze customer journey data and context</li>
                <li>View detailed processing results including treatment justification</li>
                <li>Get insights into each customer's journey and optimal treatment path</li>
            </ul>
            <p>The intelligent agent system evaluates each customer individually, respecting their permissions and considering resource constraints to determine the best possible treatment.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Get all available treatments to allow filtering
    treatment_filter_expander = st.expander("Treatment Selection Options", expanded=False)
    
    # Get all available treatments
    with treatment_filter_expander:
        st.write("### Limit Available Treatments")
        st.write("Select which treatments the system can choose from. If none are selected, all treatments will be available.")
        
        with st.spinner("Loading treatments..."):
            treatments_result = orchestrator.process({
                "type": "list_treatments"
            })
            
            if treatments_result.get("status") == "success":
                all_treatments = treatments_result.get("treatments", [])
                
                # Store treatments by ID for lookup
                treatments_by_id = {t.get("id"): t for t in all_treatments}
                
                # Create options for display with format "Display Name (ID)"
                treatment_options = [f"{t.get('display_name', 'Unknown')} ({t.get('id')})" for t in all_treatments]
                
                # Initialize session state for selected treatments if it doesn't exist
                if "selected_treatments" not in st.session_state:
                    st.session_state.selected_treatments = []
                
                # Add Select All and Clear All buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All Treatments", key="select_all_treatments"):
                        st.session_state.selected_treatments = treatment_options
                        st.rerun()
                
                with col2:
                    if st.button("Clear All Treatments", key="clear_all_treatments"):
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
        else:
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
                    api_request["allowed_treatments"] = selected_treatment_ids
                
                # Process all customers in a single batch request
                results = orchestrator.process(api_request)
                
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
                            "Status": status,
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
                    import json
                    result_str = json.dumps(results, indent=2)
                    st.download_button(
                        label="Download Results (JSON)",
                        data=result_str,
                        file_name="agentic_nba_results.json",
                        mime="application/json"
                    )

# Trigger management page
def trigger_management_page():
    st.write("## Gen AI Triggers")
    st.write("Identify customers based on specific trigger criteria.")
    
    # Add a descriptive explanation of trigger management
    with st.expander("What is an Gen AI Trigger?", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>What is Trigger Management?</strong>
            <p>AI Triggers lets you identify customers who match specific criteria or exhibit particular behaviors. You can:</p>
            <ul>
                <li>Use predefined triggers like network issues, billing disputes, or churn risk</li>
                <li>Create custom triggers using natural language descriptions</li>
                <li>Apply triggers to your entire customer base or a specific subset</li>
                <li>Export results in various formats (text, JSON, CSV)</li>
                <li>Instantly process matched customers with appropriate treatments</li>
            </ul>
            <p>This feature is essential for proactive customer management, allowing you to identify and address issues before they escalate, target specific customer segments, or launch targeted marketing campaigns.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Trigger type selection
    trigger_types = ["network_issues", "billing_disputes", "churn_risk", 
                    "high_value", "roaming_issues", "custom"]
    
    selected_trigger = st.selectbox("Select Trigger Type", trigger_types)
    
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
                message["customer_ids"] = get_all_customer_ids()
            else:
                message["customer_ids"] = specific_customers
            
            # Process the trigger request
            result = orchestrator.process(message)
            
            # Display results
            if result.get("status") == "success":
                st.success(f"Found {result.get('total_matches', 0)} matching customers")
                
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
                        st.session_state.triggered_customers = [m.get("customer_id") for m in result.get("matches")]
                        st.session_state.page = "process_customer"
                        st.rerun()
            else:
                st.error(f"Error: {result.get('message', 'Unknown error')}")

# Treatment management page
def treatment_management_page():
    st.write("## Treatment Management")
    
    # Add a descriptive explanation of treatment management
    with st.expander("What is Treatment Management?", expanded=False):
        st.markdown("""
        <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #e53935;">
            <strong>What is Treatment Management?</strong>
            <p>Treatment Management provides complete control over the actions your CVM system can take with customers. With this feature, you can:</p>
            <ul>
                <li>View all available treatments in the system</li>
                <li>Add custom treatments with specific parameters and constraints</li>
                <li>Update existing treatment descriptions and properties</li>
                <li>Remove custom treatments that are no longer needed</li>
                <li>Set resource limits and priorities for each treatment</li>
            </ul>
            <p>This capability ensures your CVM system has the right set of actions available to address customer needs, launch new initiatives, or support marketing campaigns. All treatments can be configured with resource constraints to prevent overuse.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Create tabs for different treatment operations
    tab1, tab2, tab3, tab4 = st.tabs(["List Treatments", "Add Treatment", "Update Treatment", "Remove Treatment"])
    
    with tab1:
        st.write("### Available Treatments")
        
        # Option to show only custom treatments
        custom_only = st.checkbox("Show Custom Treatments Only")
        
        # Get treatments
        with st.spinner("Loading treatments..."):
            treatments_result = orchestrator.process({
                "type": "list_treatments",
                "custom_only": custom_only
            })
            
            if treatments_result.get("status") == "success":
                treatments = treatments_result.get("treatments", [])
                
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
            else:
                st.error(f"Error: {treatments_result.get('message', 'Unknown error')}")
    
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
            else:
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
                    result = orchestrator.process({
                        "type": "add_treatment",
                        "treatment_data": treatment_json
                    })
                    
                    if result.get("status") == "success":
                        st.success(f"Treatment added successfully with ID: {result.get('treatment_id')}")
                    else:
                        st.error(f"Error: {result.get('message', 'Unknown error')}")
    
    with tab3:
        st.write("### Update Treatment")
        
        # Get all treatment IDs
        with st.spinner("Loading treatments..."):
            treatments_result = orchestrator.process({
                "type": "list_treatments"
            })
            
            if treatments_result.get("status") == "success":
                treatments = treatments_result.get("treatments", [])
                treatment_ids = [t.get("id") for t in treatments]
                
                # Select treatment to update
                selected_treatment_id = st.selectbox("Select Treatment", treatment_ids)
                
                # Get current treatment details
                current_treatment = next((t for t in treatments if t.get("id") == selected_treatment_id), {})
                
                # Update fields
                new_description = st.text_area("New Description", 
                                             value=current_treatment.get("description", ""))
                
                # Update button
                if st.button("Update Treatment"):
                    with st.spinner("Updating treatment..."):
                        result = orchestrator.process({
                            "type": "update_treatment",
                            "treatment_id": selected_treatment_id,
                            "description": new_description
                        })
                        
                        if result.get("status") == "success":
                            st.success(f"Treatment {selected_treatment_id} updated successfully!")
                        else:
                            st.error(f"Error: {result.get('message', 'Unknown error')}")
            else:
                st.error(f"Error loading treatments: {treatments_result.get('message', 'Unknown error')}")
    
    with tab4:
        st.write("### Remove Treatment")
        
        # Get all treatment IDs
        with st.spinner("Loading treatments..."):
            treatments_result = orchestrator.process({
                "type": "list_treatments",
                "custom_only": True  # Only allow removing custom treatments
            })
            
            if treatments_result.get("status") == "success":
                treatments = treatments_result.get("treatments", [])
                treatment_ids = [t.get("id") for t in treatments]
                
                if treatment_ids:
                    # Select treatment to remove
                    selected_treatment_id = st.selectbox("Select Treatment to Remove", treatment_ids)
                    
                    # Confirmation
                    st.warning("This action cannot be undone!")
                    confirm = st.checkbox("I understand that this treatment will be permanently removed")
                    
                    # Remove button
                    if st.button("Remove Treatment") and confirm:
                        with st.spinner("Removing treatment..."):
                            result = orchestrator.process({
                                "type": "remove_treatment",
                                "treatment_id": selected_treatment_id
                            })
                            
                            if result.get("status") == "success":
                                st.success(f"Treatment {selected_treatment_id} removed successfully!")
                            else:
                                st.error(f"Error: {result.get('message', 'Unknown error')}")
                else:
                    st.info("No custom treatments available to remove")
            else:
                st.error(f"Error loading treatments: {treatments_result.get('message', 'Unknown error')}")

# Display the selected page based on session state
if st.session_state.page == "dashboard":
    dashboard_page()
elif st.session_state.page == "process_customer":
    process_customer_page()
elif st.session_state.page == "trigger_management":
    trigger_management_page()
elif st.session_state.page == "treatment_management":
    treatment_management_page() 