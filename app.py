import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Registered Models Debugging App")

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch registered models
def fetch_registered_models():
    try:
        url = f"{API_HOST}/model-monitoring/v1/models"
        headers = {"X-Domino-Api-Key": API_KEY}
        response = requests.get(url, headers=headers)
        
        # Debug information
        st.write("**Request URL:**", url)
        st.write("**Response Status Code:**", response.status_code)
        st.write("**Response Text:**", response.text)

        if response.status_code != 200:
            st.error(f"Error fetching models: {response.status_code} - {response.text}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

# Main App Logic
st.header("Registered Models")
models = fetch_registered_models()

if not models:
    st.warning("No models found or an error occurred.")
else:
    st.success(f"Found {len(models)} registered models.")
    for model in models:
        model_name = model.get("name", "Unnamed Model")
        model_id = model.get("id", "N/A")
        model_owner = model.get("owner", {}).get("username", "Unknown")
        st.write(f"- **Model Name:** {model_name}")
        st.write(f"  - **Model ID:** {model_id}")
        st.write(f"  - **Owner:** {model_owner}")
        st.write("---")