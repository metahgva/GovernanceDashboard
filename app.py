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

# Main Logic
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()
registered_models = fetch_registered_models()

# Summary Section
st.markdown("---")
st.header("Summary")
if deliverables and all_projects and registered_models:
    total_projects = len(all_projects)
    governed_projects = len(set(bundle["projectId"] for bundle in deliverables if bundle.get("projectId")))
    total_models = len(registered_models)
    governed_models = len({t["identifier"]["name"] for d in deliverables for t in d.get("targets", []) if t["type"] == "ModelVersion"})

    cols = st.columns(3)
    cols[0].metric("Total Policies", len(set(d["policyName"] for d in deliverables if d.get("policyName"))))
    cols[1].metric("Total Governed Bundles", len(deliverables))
    cols[2].metric("Pending Tasks", len([d for d in deliverables if d.get("state") == "Pending"]))

    cols = st.columns(4)
    cols[0].metric("Total Projects", total_projects)
    cols[1].metric("Governed Projects", governed_projects)
    cols[2].metric("Total Models", total_models)
    cols[3].metric("Governed Models", governed_models)
else:
    st.warning("Insufficient data to display summary.")

# Policies Adoption Section
st.markdown("---")
st.header("Policies Adoption")
if deliverables:
    policies = {d["policyId"]: d["policyName"] for d in deliverables if d.get("policyId")}
    for policy_id, policy_name in policies.items():
        st.subheader(f"Policy: {policy_name}")
        bundles_in_policy = [d for d in deliverables if d.get("policyId") == policy_id]
        bundle_count_by_stage = defaultdict(int)
        for d in bundles_in_policy:
            bundle_count_by_stage[d["stage"]] += 1

        # Bar chart visualization
        fig, ax = plt.subplots()
        ax.bar(bundle_count_by_stage.keys(), bundle_count_by_stage.values(), color="skyblue", edgecolor="black")
        ax.set_title(f"Bundles in Policy: {policy_name}")
        ax.set_ylabel("Count")
        ax.set_xlabel("Stages")
        st.pyplot(fig)
else:
    st.warning("No policies data available.")

# Governed Bundles Section
st.markdown("---")
st.header("Governed Bundles Details")
if deliverables:
    for deliverable in deliverables:
        st.subheader(deliverable["name"])
        st.write(f"**Policy Name:** {deliverable.get('policyName', 'N/A')}")
        st.write(f"**Stage:** {deliverable.get('stage', 'N/A')}")
        targets = deliverable.get("targets", [])
        if targets:
            st.write("**Targets:**")
            for target in targets:
                if target["type"] == "ModelVersion":
                    model_name = target["identifier"]["name"]
                    version = target["identifier"]["version"]
                    creator = target["createdBy"]["userName"]
                    link = f"{API_HOST}/u/{creator}/{model_name}/model-registry/{model_name}/model-card?version={version}"
                    st.markdown(f"- [{model_name} (Version {version})]({link})")
else:
    st.warning("No governed bundles to display.")

# Models Overview Section
st.markdown("---")
st.header("Models Overview")
if registered_models:
    model_details = []
    for model in registered_models:
        name = model["name"]
        project = model["project"]["name"]
        owner = model["ownerUsername"]
        governed = any(
            t["identifier"]["name"] == name and t["type"] == "ModelVersion"
            for d in deliverables
            for t in d.get("targets", [])
        )
        status = "Governed" if governed else "Not Governed"
        model_details.append((name, project, owner, status))

    st.write("### All Models")
    st.table(model_details)
else:
    st.warning("No models found.")