import streamlit as st
import requests
import json

# Streamlit app title
st.title("Deliverables Dashboard")

# Input fields for API configuration
st.sidebar.header("API Configuration")
host = st.sidebar.text_input("API Host", "https://your-api-endpoint")
api_key = st.sidebar.text_input("API Key", type="password")
fetch_data = st.sidebar.button("Fetch Deliverables")

# Function to fetch deliverables from the API
def fetch_deliverables():
    try:
        # API request
        response = requests.get(
            f"{host}/guardrails/v1/deliverables",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Process data and display it
if fetch_data:
    st.write("Fetching deliverables...")
    data = fetch_deliverables()
    if data:
        deliverables = data.get("data", [])

        # Iterate through deliverables
        for deliverable in deliverables:
            # Extract data fields
            bundle_name = deliverable.get("name", "Unnamed Bundle")
            status = deliverable.get("state", "Unknown")
            policy_name = deliverable.get("policyName", "Unknown")
            stage = deliverable.get("stage", "Unknown")
            project_name = deliverable.get("projectName", "Unnamed Project")
            project_owner = deliverable.get("projectOwner", "Unknown Project Owner")
            bundle_owner = f"{deliverable.get('createdBy', {}).get('firstName', 'Unknown')} {deliverable.get('createdBy', {}).get('lastName', 'Unknown')}"
            targets = deliverable.get("targets", [])

            # Group attachments by type and collect their details
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

            # Display attachments
            st.write("**Attachments by Type:**")
            total_attachments = sum(len(names) for names in attachment_details.values())
            st.write(f"Total Attachments: {total_attachments}")
            for attachment_type, names in attachment_details.items():
                st.write(f"- **{attachment_type}:**")
                for name in names:
                    st.write(f"  - {name}")
            st.write("---")