import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Fetch Policies Debugging")

# Function to fetch all policies
def fetch_all_policies():
    try:
        url = f"{API_HOST}/governance/policies"
        st.write(f"Making request to {url}")  # Debug info
        response = requests.get(url, auth=(API_KEY, API_KEY))  # Using Basic Auth
        st.write(f"Response Status Code: {response.status_code}")  # Debug status code
        st.write(f"Response Text: {response.text}")  # Debug raw response
        if response.status_code != 200:
            return None
        return response.json().get("policies", [])
    except Exception as e:
        st.write(f"An error occurred: {e}")
        return None

# Fetch policies
policies = fetch_all_policies()

# Display policies
if policies:
    st.subheader("Policies")
    for policy in policies:
        st.write(policy)
else:
    st.write("No policies found or an error occurred.")