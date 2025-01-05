import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables and Projects Dashboard")

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details)", unsafe_allow_html=True)
st.sidebar.markdown("[Models Overview](#models-overview)", unsafe_allow_html=True)

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

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

# Function to fetch all projects
@st.cache_data
def fetch_all_projects():
    try:
        url = f"{API_HOST}/v4/projects"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching projects: {response.status_code} - {response.text}")
            return []
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching projects: {e}")
        return []

# Function to fetch registered models
@st.cache_data
def fetch_registered_models():
    try:
        url = f"{API_HOST}/api/registeredmodels/v1"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

# Main Dashboard Logic
deliverables = fetch_deliverables()
all_projects = fetch_all_projects()
models = fetch_registered_models()

# Calculate Summary Metrics
if deliverables:
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
    total_governed_bundles = len(governed_bundles)

    # Unique Projects
    unique_project_ids = {project.get("id") for project in all_projects if project.get("id")}
    governed_project_ids = {bundle.get("projectId") for bundle in governed_bundles if bundle.get("projectId")}
    total_projects = len(unique_project_ids)
    total_projects_with_bundles = len(governed_project_ids)

    # Models Metrics
    model_versions_in_bundles = set()
    for bundle in governed_bundles:
        for target in bundle.get("targets", []):
            if target.get("type") == "ModelVersion":
                identifier = target.get("identifier", {})
                model_versions_in_bundles.add((identifier.get("name"), identifier.get("version")))
    total_models_in_bundles = len(model_versions_in_bundles)

    # Display Summary Section
    st.markdown("---")
    st.header("Summary")
    # First Row of Metrics
    cols1 = st.columns(3)
    cols1[0].metric("Total Policies", total_policies)
    cols1[1].metric("Total Bundles", total_bundles)
    cols1[2].metric("Total Models", len(models))
    # Second Row of Metrics
    cols2 = st.columns(3)
    cols2[0].metric("Models in Bundles", total_models_in_bundles)
    cols2[1].metric("Total Projects", total_projects)
    cols2[2].metric("Projects with Bundles", total_projects_with_bundles)

    # Governed Bundles Section
    st.markdown("---")
    st.header("Governed Bundles Details")
    for bundle in governed_bundles:
        st.subheader(bundle.get("name", "Unnamed Bundle"))
        st.write(f"**Policy:** {bundle.get('policyName', 'Unknown')}")
        st.write(f"**Stage:** {bundle.get('stage', 'Unknown')}")
        st.write(f"**Created By:** {bundle.get('createdBy', {}).get('username', 'Unknown')}")
        st.write(f"**Targets:**")
        for target in bundle.get("targets", []):
            if target.get("type") == "ModelVersion":
                identifier = target.get("identifier", {})
                model_name = identifier.get("name", "Unknown Model")
                version = identifier.get("version", "Unknown Version")
                owner = bundle.get("createdBy", {}).get("username", "Unknown")
                project = bundle.get("projectName", "Unknown Project")
                link = f"{API_HOST}/u/{owner}/{project}/model-registry/{model_name}/model-card?version={version}"
                st.write(f"- **Name:** {model_name}, **Version:** {version}, [View Model]({link})")
        st.markdown("---")

    # Models Overview Section
    st.markdown("---")
    st.header("Models Overview")
    models_table = []
    for model in models:
        model_name = model.get("name", "Unnamed Model")
        project_name = model.get("project", {}).get("name", "Unknown Project")
        owner = model.get("ownerUsername", "Unknown User")
        governed = any(
            (model_name, version.get("version")) in model_versions_in_bundles
            for version in model.get("latestVersion", [])
        )
        models_table.append([model_name, project_name, owner, "Yes" if governed else "No"])

    st.write("### Models Details")
    st.write(
        "| Model Name | Project Name | Owner | Governed Bundle |\n"
        "|------------|--------------|-------|-----------------|\n"
        + "\n".join(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |" for row in models_table)
    )
else:
    st.warning("No deliverables found or an error occurred.")