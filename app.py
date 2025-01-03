import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Debugging Policy Fetching")

# Function to fetch all policies
def fetch_all_policies():
    try:
        url = f"{API_HOST}/governance/policies"
        st.write(f"Requesting: {url}")  # Debug info
        response = requests.get(url, auth=(API_KEY, API_KEY))  # Basic Auth
        st.write(f"Status Code: {response.status_code}")  # Debug status code

        # Debug raw response content
        st.write("Raw Response Content:")
        #st.code(response.text)

        if response.status_code != 200:
            st.error(f"Error fetching policies: {response.status_code}")
            return None

        # Ensure the response is JSON
        try:
            data = response.json()
        except Exception as e:
            st.error(f"Response is not JSON: {e}")
            return None

        return data.get("policies", [])
    except Exception as e:
        st.error(f"An exception occurred: {e}")
        return None

# Fetch policies
st.header("Fetching Policies")
policies = fetch_all_policies()

# Display fetched policies
if policies:
    st.subheader("Policies Retrieved")
    for policy in policies:
        st.write(policy)
else:
    st.warning("No policies found or an error occurred.")