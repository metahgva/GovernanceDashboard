import streamlit as st
import requests
import json
import os

# Load API Host and Key from environment variables
API_HOST = os.getenv("API_HOST", "")
API_KEY = os.getenv("API_KEY", "")

# Streamlit app title
st.title("Deliverables Dashboard")

# Sidebar information (no manual input needed)
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Button to fetch deliverables
fetch_data = st.sidebar.button("Fetch Deliverables")

# Function to fetch deliverables from the API
def fetch_deliverables():
    try:
        # API request
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Fetch and display deliverables
if fetch_data:
    if not API_KEY:
        st.error("API Key is missing. Set the environment variable and restart the app.")
    else:
        st.write("Fetching deliverables...")
        data = fetch_deliverables()
        if data:
            deliverables = data.get("data", [])
            # Display deliverables (same as before)
            for deliverable in deliverables:
                # Extract details and display
                bundle_name = deliverable.get("name", "Unnamed Bundle")
                status = deliverable.get("state", "Unknown")
                policy_name = deliverable.get("policyName", "Unknown")
                stage = deliverable.get("stage", "Unknown")
                project_name = deliverable.get("projectName", "Unnamed Project")
                project_owner = deliverable.get("projectOwner", "Unknown Project Owner")
                bundle_owner = f"{deliverable.get('createdBy', {}).get('firstName', 'Unknown')} {deliverable.get('createdBy', {}).get('lastName', 'Unknown')}"
                targets = deliverable.get("targets", [])
                # Group attachments by type and list details
                attachment_details = {}
                for target in targets:
                    attachment_type = target.get("type", "Unknown")
                    if attachment_type == "ModelVersion":
                        model_name = target.get("identifier", {}).get("name", "Unnamed Model")
                        model_version = target.get("identifier", {}).get("version", "Unknown Version")
                        attachment_name = f"{model_name} (Version: {model_version})"
                    else:
                        attachment_name = target.get("identifier", {}).get("filename", "Unnamed Attachment")
                    if attachment_type not in attachment_details:
                        attachment_details[attachment_type] = []
                    attachment_details[attachment_type].append(attachment_name)
                # Display bundle details
                st.subheader(f"Bundle: {bundle_name}")
                st.write(f"**Status:** {status}")
                st.write(f"**Policy Name:** {policy_name}")
                st.write(f"**Stage:** {stage}")
                st.write(f"**Project Name:** {project_name}")
                st.write(f"**Project Owner:** {project_owner}")
                st.write(f"**Bundle Owner:** {bundle_owner}")
                # Attachments
                st.write("**Attachments by Type:**")
                for attachment_type, names in attachment_details.items():
                    st.write(f"- **{attachment_type}:**")
                    for name in names:
                        st.write(f"  - {name}")
                st.write("---")