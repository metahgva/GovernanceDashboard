import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Policy Stages Extractor")

# Function to fetch deliverables
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            auth=(API_KEY, API_KEY),
        )
        if response.status_code != 200:
            st.error(f"Error fetching deliverables: {response.status_code} - {response.text}")
            return None
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An exception occurred while fetching deliverables: {e}")
        return None

# Function to extract policies from deliverables
def extract_policies(deliverables):
    policies = {}
    for deliverable in deliverables:
        policy_id = deliverable.get("policyId", "unknown")
        policy_name = deliverable.get("policyName", "No Policy Name")
        if policy_id != "unknown":
            policies[policy_id] = policy_name
    return policies

# Function to fetch policy definition
@st.cache_data
def fetch_policy_definition(policy_id):
    try:
        url = f"{API_HOST}/governance/v1/policies/{policy_id}/definition"
        response = requests.get(url, auth=(API_KEY, API_KEY))  # Basic Auth
        if response.status_code != 200:
            st.error(f"Error fetching policy definition for {policy_id}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An exception occurred while fetching policy definition for {policy_id}: {e}")
        return None

# Fetch deliverables and extract policies
st.header("Fetching Deliverables")
deliverables = fetch_deliverables()

if deliverables:
    st.subheader("Deliverables Retrieved")
    st.write(f"Total Deliverables: {len(deliverables)}")

    st.header("Extracting Policies")
    policies = extract_policies(deliverables)

    if policies:
        st.subheader("Policies Extracted")
        for policy_id, policy_name in policies.items():
            st.write(f"Policy ID: {policy_id}, Policy Name: {policy_name}")

        st.header("Fetching Policy Definitions and Stages")
        for policy_id, policy_name in policies.items():
            st.subheader(f"Policy: {policy_name}")
            policy_definition = fetch_policy_definition(policy_id)
            if policy_definition:
                stages = policy_definition.get("stages", [])
                if stages:
                    st.write(f"Stages for {policy_name}:")
                    for stage in stages:
                        st.write(f"- {stage.get('name', 'Unnamed Stage')}")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch definition for policy {policy_name}.")
    else:
        st.warning("No policies found in the deliverables.")
else:
    st.warning("No deliverables found or an error occurred.")