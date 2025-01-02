import streamlit as st
import requests
import os
from collections import defaultdict

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech/")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables Dashboard")

# Sidebar information
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch deliverables from the API
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            auth=(API_KEY, API_KEY),
        )
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Fetch deliverables
if not API_KEY:
    st.error("API Key is missing. Set the environment variable and restart the app.")
else:
    data = fetch_deliverables()
    if data:
        deliverables = data.get("data", [])
        if not deliverables:
            st.warning("No deliverables found.")
        else:
            # Group bundles by policy and stage with detailed information
            bundles_per_policy_stage = defaultdict(lambda: defaultdict(list))
            for bundle in deliverables:
                policy_name = bundle.get("policyName", "No Policy Name")
                bundle_stage = bundle.get("stage", "No Stage")
                bundle_details = {
                    "name": bundle.get("name", "Unnamed Bundle"),
                    "createdAt": bundle.get("createdAt", "Unknown Date"),
                    "state": bundle.get("state", "Unknown State"),
                }
                bundles_per_policy_stage[policy_name][bundle_stage].append(bundle_details)

            # Display Total Counters
            total_bundles = len(deliverables)
            total_policies = len(bundles_per_policy_stage)
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Total Policies", value=total_policies)
            with col2:
                st.metric(label="Total Bundles", value=total_bundles)

            # Bundles by Policy and Stage
            st.write("### Bundles by Policy and Stage")
            for policy_name, stages in bundles_per_policy_stage.items():
                st.subheader(policy_name)
                for stage, bundles in stages.items():
                    st.write(f"**Stage:** {stage} ({len(bundles)} bundles)")
                    for bundle in bundles:
                        st.write(f"- **Bundle Name:** {bundle['name']}")
                        st.write(f"  - **Created At:** {bundle['createdAt']}")
                        st.write(f"  - **State:** {bundle['state']}")
                    st.write("---")
            st.write("---")

            # Detailed Deliverables Section
            for deliverable in deliverables:
                # Extract details
                bundle_name = deliverable.get("name", "Unnamed Bundle")
                status = deliverable.get("state", "Unknown")
                policy_name = deliverable.get("policyName", "Unknown")
                stage = deliverable.get("stage", "Unknown")
                project_name = deliverable.get("projectName", "Unnamed Project")
                project_owner = deliverable.get("projectOwner", "Unknown Project Owner")
                bundle_owner = f"{deliverable.get('createdBy', {}).get('firstName', 'Unknown')} {deliverable.get('createdBy', {}).get('lastName', 'Unknown')}"
                targets = deliverable.get("targets", [])

                # Group attachments by type
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

                # Attachments in collapsible sections
                st.write("**Attachments by Type:**")
                for attachment_type, names in attachment_details.items():
                    with st.expander(f"{attachment_type} ({len(names)} items)"):
                        for name in names:
                            st.write(f"- {name}")
                st.write("---")