import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Policy Stages Debugging with Guardrails API")

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

# Function to fetch policy details using the Guardrails `/policies/{id}` endpoint
def fetch_policy_details(policy_id):
    try:
        url = f"{API_HOST}/guardrails/v1/policies/{policy_id}"
        st.write(f"Fetching policy details: {url}")  # Debug URL
        response = requests.get(url, auth=(API_KEY, API_KEY))  # Basic Auth
        st.write(f"Response Status Code: {response.status_code}")  # Debug Status Code
        st.write(f"Response Text: {response.text}")  # Debug Raw Response
        if response.status_code != 200:
            st.error(f"Error fetching policy details for {policy_id}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An exception occurred while fetching policy details for {policy_id}: {e}")
        return None

# Main App Logic
st.header("Fetching Deliverables")
deliverables = fetch_deliverables()

if deliverables:
    st.subheader("Deliverables Retrieved")
    st.write(f"Total Deliverables: {len(deliverables)}")

    st.header("Extracting Policies")
    policies = {}
    for deliverable in deliverables:
        policy_id = deliverable.get("policyId", "unknown")
        policy_name = deliverable.get("policyName", "No Policy Name")
        if policy_id != "unknown":
            policies[policy_id] = policy_name

    if policies:
        st.subheader("Policies Extracted")
        for policy_id, policy_name in policies.items():
            st.write(f"Policy ID: {policy_id}, Policy Name: {policy_name}")

        st.header("Fetching Policy Details and Debugging")
        for policy_id, policy_name in policies.items():
            st.subheader(f"Policy: {policy_name}")
            policy_details = fetch_policy_details(policy_id)
            if policy_details:
                stages = policy_details.get("stages", [])
                if stages:
                    st.write(f"Stages for {policy_name}:")
                    for stage in stages:
                        st.write(f"- {stage.get('name', 'Unnamed Stage')}")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch details for policy {policy_name}.")
    else:
        st.warning("No policies found in the deliverables.")
else:
    st.warning("No deliverables found or an error occurred.")