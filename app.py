import streamlit as st
import requests
import os
from collections import defaultdict

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables and Models Dashboard")

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
            return []
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching deliverables: {e}")
        return []

# Function to fetch registered models
@st.cache_data
def fetch_registered_models():
    try:
        response = requests.get(
            f"{API_HOST}/api/registeredmodels/v1",
            headers={"X-Domino-Api-Key": API_KEY},
        )
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

# Main logic
deliverables = fetch_deliverables()
models = fetch_registered_models()

# Display deliverables and associated targets
if deliverables:
    st.header("Deliverables and Targets")
    deliverable_targets = {d["id"]: d.get("targets", []) for d in deliverables}

    for deliverable in deliverables:
        st.subheader(f"Deliverable: {deliverable['name']} (ID: {deliverable['id']})")
        targets = deliverable_targets.get(deliverable["id"], [])
        if targets:
            st.write("**Targets (Attachments):**")
            for target in targets:
                # Debugging step to display the full target structure
                st.write("Target Debug Info:", target)
                
                # Safe access to target fields
                target_name = target.get("name", "Unnamed Target")
                target_type = target.get("type", "Unknown Type")
                target_id = target.get("targetId", "Unknown Target ID")
                st.write(f"- **Name:** {target_name}, **Type:** {target_type}, **Target ID:** {target_id}")
        else:
            st.write("No targets found for this deliverable.")
else:
    st.warning("No deliverables found.")

# Display registered models
if models:
    st.header("Registered Models")
    st.write(f"Total Registered Models: {len(models)}")

    st.write("Models List:")
    for model in models:
        model_name = model.get("name", "Unnamed Model")
        project_name = model.get("project", {}).get("name", "Unknown Project")
        owner_username = model.get("ownerUsername", "Unknown Owner")
        model_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"
        st.write(f"- **Name:** {model_name}, **Project:** {project_name}, **Owner:** {owner_username}")
        st.markdown(f"[View Model Details]({model_link})", unsafe_allow_html=True)
else:
    st.warning("No registered models found.")