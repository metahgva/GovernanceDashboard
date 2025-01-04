import requests
import streamlit as st
import os

# Load API Host and Key
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Function to fetch registered models
def fetch_registered_models():
    try:
        url = f"{API_HOST}/api/registeredmodels/v1"
        headers = {"X-Domino-Api-Key": API_KEY}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return None

        models = response.json().get("data", [])
        return models

    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return None

# Streamlit application
st.title("Domino Registered Models")

models = fetch_registered_models()

if models:
    st.subheader("Registered Models")
    if len(models) > 0:
        for model in models:
            model_name = model.get("name", "Unnamed Model")
            model_description = model.get("description", "No description provided")
            model_created_at = model.get("createdAt", "N/A")
            st.markdown(f"### {model_name}")
            st.write(f"**Description:** {model_description}")
            st.write(f"**Created At:** {model_created_at}")
    else:
        st.write("No registered models found.")
else:
    st.write("Failed to fetch registered models.")