import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Model Debugging App")

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to query the root API for debugging
@st.cache_data
def query_root_api():
    try:
        url = f"{API_HOST}/"
        headers = {"X-Domino-Api-Key": API_KEY}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return f"Error fetching root API: {response.status_code} - {response.text}"
        return response.text
    except Exception as e:
        return f"An error occurred while querying the root API: {e}"

# Function to fetch registered models using MLFlow
@st.cache_data
def fetch_mlflow_models():
    try:
        mlflow_url = f"{API_HOST}/api/2.0/preview/mlflow/registered-models/list"
        headers = {"X-Domino-Api-Key": API_KEY}
        response = requests.get(mlflow_url, headers=headers)
        if response.status_code != 200:
            return f"Error fetching models: {response.status_code} - {response.text}", []
        models = response.json().get("registered_models", [])
        return "Success", models
    except Exception as e:
        return f"An error occurred while fetching models: {e}", []

# Main App Logic
st.header("Root API Debugging")
root_api_response = query_root_api()
st.code(root_api_response)

st.header("MLFlow Models")
mlflow_status, mlflow_models = fetch_mlflow_models()
if mlflow_status != "Success":
    st.error(mlflow_status)
else:
    if not mlflow_models:
        st.write("No models found in MLFlow.")
    else:
        st.write(f"Found {len(mlflow_models)} models in MLFlow:")
        for model in mlflow_models:
            st.write(f"- **Name**: {model['name']}")
            st.write(f"  - **Creation Timestamp**: {model.get('creation_timestamp', 'N/A')}")
            st.write(f"  - **Last Updated Timestamp**: {model.get('last_updated_timestamp', 'N/A')}")
            st.write(f"  - **Description**: {model.get('description', 'N/A')}")