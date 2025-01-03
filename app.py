import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Fetch All Policy Stages with Debugging (Basic Auth)")

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch all policies with debug logging
def fetch_all_policies():
    try:
        url = f"{API_HOST}/governance/policies"
        st.write(f"Debug: Making request to {url}")  # Debug info
        response = requests.get(url, auth=(API_KEY, API_KEY))  # Use Basic Auth like in fetch_deliverables
        st.write(f"Debug: Raw Response - {response.text}")  # Log raw response
        if response.status_code != 200:
            st.error(f"Error fetching policies: {response.status_code} - {response.text}")
            return []
        return response.json().get("policies", [])
    except Exception as e:
        st.error(f"An error occurred while fetching policies: {e}")
        return []

# Fetch all policies
policies = fetch_all_policies()
if policies:
    st.subheader("Policies and Stages")
    for policy in policies:
        policy_name = policy.get("name", "Unnamed Policy")
        policy_id = policy.get("id", "Unknown ID")
        st.write(f"Policy: {policy_name} (ID: {policy_id})")
else:
    st.error("No policies found.")