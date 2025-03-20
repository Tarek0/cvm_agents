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
    page_title="CVM Control Center",
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
    "Dashboard": "dashboard",
    "Customer Processing": "process_customer",
    "Trigger Management": "trigger_management",
    "Treatment Management": "treatment_management",
    "Batch Operations": "batch_operations"
}

# Sidebar navigation
st.sidebar.title("CVM Control Center")
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

# Navigation selection
selected_page = st.sidebar.radio("Navigation", list(PAGES.keys()))

# Display page heading
st.title(f"CVM Control Center - {selected_page}")
st.markdown('<hr style="border-top: 2px solid #e53935; margin-bottom: 20px;">', unsafe_allow_html=True)

# Dashboard page
def dashboard_page():
    st.write("## Welcome to the CVM Control Center")
    st.write("This control center provides a centralized interface for managing the Customer Value Management system.")

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
    st.write("## Process Customer")
    st.write("Select a customer to process through the CVM system.")
    
    # Get all customer IDs
    customer_ids = get_all_customer_ids()
    
    # Customer selection
    selected_customer = st.selectbox("Select Customer ID", customer_ids)
    
    if st.button("Process Customer"):
        with st.spinner("Processing customer..."):
            result = orchestrator.process({
                "type": "process_customer",
                "customer_id": selected_customer
            })
            
            # Display results
            st.success(f"Customer {selected_customer} processed successfully!")
            st.json(result)

# Trigger management page
def trigger_management_page():
    st.write("## Trigger Management")
    st.write("Identify customers based on specific trigger criteria.")
    
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
                        st.session_state.page = "batch_operations"
                        st.rerun()
            else:
                st.error(f"Error: {result.get('message', 'Unknown error')}")

# Treatment management page
def treatment_management_page():
    st.write("## Treatment Management")
    
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

# Batch operations page
def batch_operations_page():
    st.write("## Batch Operations")
    st.write("Process multiple customers at once.")
    
    # Get all customer IDs
    all_customer_ids = get_all_customer_ids()
    
    # Check if we have pre-selected customers from trigger page
    if hasattr(st.session_state, 'triggered_customers') and st.session_state.triggered_customers:
        selected_customers = st.multiselect("Select Customers", all_customer_ids, 
                                          default=st.session_state.triggered_customers)
        # Clear the session after using it
        st.session_state.triggered_customers = []
    else:
        selected_customers = st.multiselect("Select Customers", all_customer_ids)
    
    # Quick select buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All"):
            selected_customers = all_customer_ids
            st.rerun()
    
    with col2:
        if st.button("Clear Selection"):
            selected_customers = []
            st.rerun()
    
    # Input field for customer IDs as text
    custom_ids = st.text_input("Or Enter Customer IDs (comma-separated)")
    
    # Treatment selection for batch processing
    treatments_result = orchestrator.process({
        "type": "list_treatments"
    })
    
    if treatments_result.get("status") == "success":
        treatments = treatments_result.get("treatments", [])
        treatment_options = {t.get("display_name", "Unknown"): t.get("id") for t in treatments}
        
        selected_treatment_name = st.selectbox("Select Treatment", list(treatment_options.keys()))
        selected_treatment_id = treatment_options.get(selected_treatment_name)
        
        # Process button
        process_clicked = st.button("Process Batch")
        
        if process_clicked:
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
                    # Use process_batch with specific treatment instead of individual calls
                    result = orchestrator.process({
                        "type": "process_batch",
                        "customer_ids": ids_to_process,
                        "treatment_id": selected_treatment_id
                    })
                    
                    # Check if we got a proper batch result
                    if result.get("status") == "success" and "results" in result:
                        results = result.get("results", [])
                        
                        # Show summary of results
                        successful = sum(1 for r in results if r.get("status") == "success")
                        failed = len(results) - successful
                        
                        if failed > 0:
                            st.warning(f"Batch processing complete: {successful} successful, {failed} failed")
                        else:
                            st.success(f"Batch processing complete: All {successful} customers processed successfully")
                        
                        # Display results in a table
                        result_data = []
                        for r in results:
                            customer_id = r.get("customer_id", "unknown")
                            status = r.get("status", "unknown")
                            # Get appropriate message based on status
                            message = r.get("message", "")
                            if status == "error" and "error" in r:
                                message = r.get("error", "")
                            elif status == "success" and "result" in r:
                                message = "Success"
                            
                            # Get the actually applied treatment
                            applied_treatment = r.get("treatment", {}).get("display_name", selected_treatment_name) if r.get("treatment") else selected_treatment_name
                            
                            result_data.append({
                                "Customer ID": customer_id,
                                "Status": status,
                                "Message": message,
                                "Treatment": applied_treatment
                            })
                        
                        st.write("### Processing Results")
                        st.table(result_data)
                    else:
                        # Handle case where batch processing failed entirely
                        st.error(f"Batch processing failed: {result.get('message', 'Unknown error')}")
                        if "results" in result:
                            # Try to show individual results if available
                            st.write("### Processing Results")
                            st.json(result.get("results", []))
    else:
        st.error(f"Error loading treatments: {treatments_result.get('message', 'Unknown error')}")

# Display the selected page
if PAGES[selected_page] == "dashboard":
    dashboard_page()
elif PAGES[selected_page] == "process_customer":
    process_customer_page()
elif PAGES[selected_page] == "trigger_management":
    trigger_management_page()
elif PAGES[selected_page] == "treatment_management":
    treatment_management_page()
elif PAGES[selected_page] == "batch_operations":
    batch_operations_page() 