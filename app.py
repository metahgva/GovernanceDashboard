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

# Display deliverables and associated ModelVersion targets
if deliverables:
    st.header("Deliverables and Associated Model Versions")
    deliverable_targets = {d["id"]: d.get("targets", []) for d in deliverables}

    for deliverable in deliverables:
        st.subheader(f"Deliverable: {deliverable['name']} (ID: {deliverable['id']})")
        targets = deliverable_targets.get(deliverable["id"], [])
        if targets:
            model_links = []
            for target in targets:
                # Only process ModelVersion targets
                if target.get("type") == "ModelVersion":
                    identifier = target.get("identifier", {})
                    model_name = identifier.get("name", "Unknown Model")
                    version = identifier.get("version", "Unknown Version")
                    created_by = target.get("createdBy", {}).get("userName", "unknown_user")
                    project_name = deliverable.get("projectName", "Unknown Project")
                    link = f"{API_HOST}/u/{created_by}/{project_name}/model-registry/{model_name}/model-card?version={version}"
                    model_links.append((model_name, version, link))
            
            if model_links:
                st.write("**ModelVersion Targets:**")
                for model_name, version, link in model_links:
                    st.write(f"- **Model Name:** {model_name}, **Version:** {version}")
                    st.markdown(f"[View Model Card]({link})", unsafe_allow_html=True)
            else:
                st.write("No ModelVersion targets found.")
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