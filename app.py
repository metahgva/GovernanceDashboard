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

# Function to visualize policies with stages
def plot_policy_stages(policy_name, stages, bundle_data):
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(stage_names, bundle_counts, color="skyblue", edgecolor="black")
    ax.set_title(f"Policy: {policy_name}")
    ax.set_xlabel("Stages")
    ax.set_ylabel("Number of Bundles")
    ax.yaxis.get_major_locator().set_params(integer=True)  # Force Y-axis to use whole numbers
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig

# Main Dashboard Logic
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()
models = fetch_registered_models()

if deliverables:
    # Summary Section
    st.markdown("---")
    st.header("Summary")
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
    total_governed_bundles = len(governed_bundles)
    total_projects = len(all_projects)
    projects_with_bundles = len(set(bundle.get("projectId") for bundle in governed_bundles))
    total_models = len(models)
    governed_models = len(
        {
            target.get("identifier", {}).get("name")
            for bundle in governed_bundles
            for target in bundle.get("targets", [])
            if target.get("type") == "ModelVersion"
        }
    )

    # Display summary metrics
    cols = st.columns(3)
    cols[0].metric("Total Policies", total_policies)
    cols[1].metric("Governed Bundles", total_governed_bundles)
    cols[2].metric("Projects with Bundles", projects_with_bundles)

    cols = st.columns(3)
    cols[0].metric("Total Projects", total_projects)
    cols[1].metric("Total Models", total_models)
    cols[2].metric("Governed Models", governed_models)

    # Policies Adoption Section
    st.markdown("---")
    st.header("Policies Adoption")
    policies = {bundle.get("policyId"): bundle.get("policyName") for bundle in deliverables if bundle.get("policyId")}

    if policies:
        for policy_id, policy_name in policies.items():
            st.subheader(f"Policy: {policy_name}")
            policy_details = fetch_policy_details(policy_id)

            if policy_details:
                stages = policy_details.get("stages", [])
                if stages:
                    bundle_data_per_stage = defaultdict(list)
                    for deliverable in deliverables:
                        if deliverable.get("policyId") == policy_id:
                            stage_name = deliverable.get("stage", "Unknown Stage")
                            bundle_data_per_stage[stage_name].append({
                                "name": deliverable.get("name", "Unnamed Bundle"),
                                "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A")
                            })

                    fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
                    st.pyplot(fig)

# Governed Bundles Section
st.markdown("---")
st.header("Governed Bundles Details")
for bundle in governed_bundles:
    bundle_name = bundle.get("name", "Unnamed Bundle")
    policy_name = bundle.get("policyName", "Unknown")
    targets = bundle.get("targets", [])
    if targets:
        st.write(f"**Bundle Name:** {bundle_name}, **Policy Name:** {policy_name}")
        for target in targets:
            if target.get("type") == "ModelVersion":
                name = target["identifier"].get("name")
                version = target["identifier"].get("version")
                model_link = f"{API_HOST}/model-registry/{name}/model-card?version={version}"
                st.markdown(f"- **Model:** {name} (Version {version}) [View]({model_link})")

else:
    st.warning("No deliverables found or an error occurred.")