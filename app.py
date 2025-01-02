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
            # Summary section
            total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
            total_bundles = len(deliverables)

            st.markdown("---")
            st.header("Summary")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Policies", total_policies)
            with col2:
                st.metric("Total Bundles", total_bundles)

            # Group bundles by policy and stage
            bundles_per_policy_stage = defaultdict(lambda: defaultdict(list))
            for bundle in deliverables:
                policy_name = bundle.get("policyName", "No Policy Name")
                bundle_stage = bundle.get("stage", "No Stage")
                bundles_per_policy_stage[policy_name][bundle_stage].append(bundle)

            # Display bundles by policy and stage
            st.markdown("---")
            st.header("Bundles by Policy and Stage")
            for policy_name, stages in bundles_per_policy_stage.items():
                policy_id = next(
                    (bundle.get("policyId") for bundle in deliverables if bundle.get("policyName") == policy_name),
                    "unknown",
                )
                policy_link = f"{API_HOST}/governance/policy/{policy_id}/editor"
                st.subheader(f"Policy: {policy_name}")
                st.markdown(f"[View Policy]({policy_link})", unsafe_allow_html=True)

                for stage, bundles in stages.items():
                    with st.expander(f"{stage} ({len(bundles)})"):
                        for bundle in bundles:
                            bundle_name = bundle.get("name", "Unnamed Bundle")
                            bundle_id = bundle.get("id", "")
                            project_owner = bundle.get("projectOwner", "unknown_user")
                            project_name = bundle.get("projectName", "unknown_project")
                            policy_id = bundle.get("policyId", "")
                            bundle_link = (
                                f"{API_HOST}/u/{project_owner}/{project_name}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
                            )
                            st.markdown(f"- [{bundle_name}]({bundle_link})", unsafe_allow_html=True)