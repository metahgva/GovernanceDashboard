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
st.sidebar.markdown("[Projects Without Bundles](#projects-without-bundles)", unsafe_allow_html=True)
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

# Function to fetch all models
@st.cache_data
def fetch_models():
    try:
        url = f"{API_HOST}/api/registeredmodels/v1"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching models: {e}")
        return []

# Function to fetch policy details
def fetch_policy_details(policy_id):
    try:
        url = f"{API_HOST}/guardrails/v1/policies/{policy_id}"
        response = requests.get(url, auth=(API_KEY, API_KEY))
        if response.status_code != 200:
            st.error(f"Error fetching policy details for {policy_id}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An exception occurred while fetching policy details for {policy_id}: {e}")
        return None

# Fetch data
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()
models = fetch_models()

# Prepare data for governed bundles and models
governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
model_versions_in_bundles = set()
for bundle in governed_bundles:
    for target in bundle.get("targets", []):
        if target["type"] == "ModelVersion":
            identifier = target.get("identifier", {})
            model_versions_in_bundles.add((identifier.get("name"), identifier.get("version")))

# Summary Section
st.markdown("---")
st.header("Summary")
cols = st.columns(3)
cols[0].metric("Total Policies", len(set(bundle.get("policyName") for bundle in deliverables)))
cols[1].metric("Total Bundles", len(deliverables))
cols[2].metric("Total Projects", len(all_projects))
cols = st.columns(2)
cols[0].metric("Total Models", len(models))
cols[1].metric("Models in Governed Bundles", len(model_versions_in_bundles))

# Models Overview Section
st.markdown("---")
st.header("Models Overview")

models_table = []
for model in models:
    model_name = model.get("name", "Unnamed Model")
    project_name = model.get("project", {}).get("name", "Unknown Project")
    owner = model.get("ownerUsername", "Unknown User")
    latest_version = model.get("latestVersion", [])
    
    # Ensure latest_version is iterable
    if isinstance(latest_version, list):
        governed = any(
            (model_name, version.get("version")) in model_versions_in_bundles
            for version in latest_version
        )
    else:
        governed = (model_name, latest_version) in model_versions_in_bundles

    models_table.append([model_name, project_name, owner, "Yes" if governed else "No"])

st.write("### Models Details")
st.write(
    "| Model Name | Project Name | Owner | Governed Bundle |\n"
    "|------------|--------------|-------|-----------------|\n"
    + "\n".join(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |" for row in models_table)
)

# Governed Bundles Section
st.markdown("---")
st.header("Governed Bundles Details")

for bundle in governed_bundles:
    bundle_name = bundle.get("name", "Unnamed Bundle")
    project_name = bundle.get("projectName", "Unnamed Project")
    owner_username = bundle.get("createdBy", {}).get("userName", "unknown_user")
    st.subheader(f"Governed Bundle: {bundle_name}")
    st.write(f"**Project:** {project_name}")
    st.write(f"**Owner:** {owner_username}")
    targets = bundle.get("targets", [])
    if targets:
        st.write("### Targets:")
        for target in targets:
            if target["type"] == "ModelVersion":
                model_name = target["identifier"].get("name", "Unknown Model")
                version = target["identifier"].get("version", "Unknown Version")
                st.write(f"- **Model:** {model_name} (Version: {version})")