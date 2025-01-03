import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Fetch All Policy Stages")

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch all policies
def fetch_all_policies():
    try:
        st.write("Fetching all policies...")  # Debug info
        response = requests.get(
            f"{API_HOST}/governance/policies",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        if response.status_code != 200:
            st.error(f"Error fetching policies: {response.status_code} - {response.text}")
            return []
        return response.json().get("policies", [])
    except Exception as e:
        st.error(f"An error occurred while fetching policies: {e}")
        return []

# Function to fetch policy definition
def fetch_policy_definition(policy_id):
    try:
        response = requests.get(
            f"{API_HOST}/governance/policies/{policy_id}/definition",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        if response.status_code != 200:
            st.error(f"Error fetching policy definition for {policy_id}: {response.status_code} - {response.text}")
            return {}
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching policy definition for {policy_id}: {e}")
        return {}

# Fetch all policies and their stages
policies = fetch_all_policies()
if policies:
    st.subheader("Policy Stages")
    for policy in policies:
        policy_id = policy.get("id", "Unknown ID")
        policy_name = policy.get("name", "Unnamed Policy")
        st.write(f"Fetching stages for policy: **{policy_name}** (ID: {policy_id})")  # Debug info
        
        # Fetch stages for the policy
        policy_definition = fetch_policy_definition(policy_id)
        stages = policy_definition.get("stages", [])
        if stages:
            st.write(f"Stages for {policy_name}:")
            for stage in stages:
                st.write(f"- {stage.get('name', 'Unnamed Stage')}")
        else:
            st.warning(f"No stages found for {policy_name}.")
else:
    st.error("No policies found.")