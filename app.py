import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Policy Stages Test App")

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch policy definition
def fetch_policy_definition(policy_id):
    st.write(f"Fetching policy definition for Policy ID: {policy_id}")  # Debug info
    try:
        response = requests.get(
            f"{API_HOST}/governance/policies/{policy_id}/definition",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        if response.status_code != 200:
            st.error(f"Error fetching policy definition: {response.status_code} - {response.text}")
            return {}
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching policy definition: {e}")
        return {}

# Input Policy ID for testing
policy_id = st.text_input("Enter Policy ID", value="")

# Fetch and display policy stages
if policy_id:
    policy_definition = fetch_policy_definition(policy_id)
    if policy_definition:
        st.subheader(f"Policy Stages for Policy ID: {policy_id}")
        
        # Debug: Display full response
        st.write("Policy Definition Response (Debug Info):")
        st.json(policy_definition)
        
        stages = policy_definition.get("stages", [])
        if stages:
            st.write(f"Found {len(stages)} stages:")
            for stage in stages:
                st.write(f"- Stage Name: {stage['name']}")
        else:
            st.warning("No stages found in the policy definition.")