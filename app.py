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
st.sidebar.markdown("[Models and Mapping](#models-and-mapping)", unsafe_allow_html=True)

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

# Function to fetch all models
@st.cache_data
def fetch_all_models():
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
deliverables = fetch_deliverables()
models = fetch_all_models()

# Parse Deliverables to Extract Targets
deliverable_targets = defaultdict(list)
for deliverable in deliverables:
    targets = deliverable.get("targets", [])
    for target in targets:
        if target["type"] == "ModelVersion":
            model_name = target["identifier"]["name"]
            model_version = target["identifier"]["version"]
            model_id = target["id"]
            owner_username = target["createdBy"]["userName"]
            project_name = deliverable.get("projectName", "Unknown Project")
            link = f"{API_HOST}/u/{owner_username}/{project_name}/model-registry/{model_name}/model-card?version={model_version}"
            deliverable_targets[deliverable["name"]].append({
                "name": model_name,
                "version": model_version,
                "link": link,
            })

# Calculate Summary Metrics
total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
total_bundles = len(deliverables)
models_in_bundles = {target["name"] for targets in deliverable_targets.values() for target in targets}
total_models_in_bundles = len(models_in_bundles)

all_projects = {model.get("project", {}).get("name", "Unknown Project") for model in models}
total_projects = len(all_projects)

projects_with_bundles = {deliverable.get("projectName", "Unknown Project") for deliverable in deliverables}
total_projects_with_bundles = len(projects_with_bundles)

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

                for stage_name, bundles in bundle_data_per_stage.items():
                    st.write(f"- **Stage: {stage_name}** ({len(bundles)})")
                    with st.expander(f"View Bundles in {stage_name}"):
                        for bundle in bundles:
                            st.write(f"- {bundle['name']} (Moved: {bundle['stageUpdateTime']})")
            else:
                st.warning(f"No stages found for policy {policy_name}.")
        else:
            st.error(f"Could not fetch details for policy {policy_name}.")

# Governed Bundles Section
st.markdown("---")
st.header("Governed Bundles Details")

for bundle_name, targets in deliverable_targets.items():
    st.subheader(bundle_name)
    st.write(f"**Deliverable Targets (Models):**")
    for target in targets:
        st.write(f"- **Name:** {target['name']}, **Version:** {target['version']}")
        st.markdown(f"[View Model Version]({target['link']})", unsafe_allow_html=True)

# Models and Mapping Section
st.markdown("---")
st.header("Models and Mapping to Governed Bundles")

model_mapping = []
for model in models:
    model_name = model.get("name", "Unnamed Model")
    project_name = model.get("project", {}).get("name", "Unknown Project")
    owner = model.get("ownerUsername", "unknown_user")
    governed_bundles = [bundle_name for bundle_name, targets in deliverable_targets.items()
                        if any(target["name"] == model_name for target in targets)]

    model_mapping.append({
        "name": model_name,
        "project": project_name,
        "owner": owner,
        "bundles": governed_bundles,
    })

for model in model_mapping:
    st.subheader(model["name"])
    st.write(f"**Project:** {model['project']}")
    st.write(f"**Owner:** {model['owner']}")
    if model["bundles"]:
        st.write("**Governed Bundles:**")
        for bundle in model["bundles"]:
            st.write(f"- {bundle}")
    else:
        st.write("**Governed Bundles:** None")