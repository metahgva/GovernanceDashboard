import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

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

# Functions to fetch data from APIs
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(f"{API_HOST}/guardrails/v1/deliverables", auth=(API_KEY, API_KEY))
        if response.status_code != 200:
            st.error(f"Error fetching deliverables: {response.status_code} - {response.text}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching deliverables: {e}")
        return []

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

@st.cache_data
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

# Helper function to plot policies with stages
def plot_policy_stages(policy_name, stages, bundle_data):
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(stage_names, bundle_counts, color="skyblue", edgecolor="black")
    ax.set_title(f"Policy: {policy_name}")
    ax.set_xlabel("Stages")
    ax.set_ylabel("Number of Bundles")
    ax.yaxis.get_major_locator().set_params(integer=True)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig

# Helper function to parse task descriptions
def parse_task_description(description):
    try:
        start = description.find("[")
        end = description.find("]")
        bundle_name = description[start + 1 : end]
        link_start = description.find("(")
        link_end = description.find(")")
        bundle_link = description[link_start + 1 : link_end]
        bundle_link = f"{API_HOST}{bundle_link}"
        return bundle_name, bundle_link
    except Exception:
        return None, None

# Fetch data
deliverables = fetch_deliverables()
projects = fetch_all_projects()
models = fetch_registered_models()

# Summary Section
st.markdown("---")
st.header("Summary")

# Calculate metrics
total_projects = len(projects)
total_models = len(models)
governed_bundles = [d for d in deliverables if d.get("policyName")]
governed_models = set(
    (target["identifier"]["name"], target["identifier"]["version"])
    for d in governed_bundles
    for target in d.get("targets", [])
    if target["type"] == "ModelVersion"
)

summary_metrics = {
    "Total Projects": total_projects,
    "Total Models": total_models,
    "Total Policies": len(set(d.get("policyName") for d in governed_bundles)),
    "Total Bundles": len(governed_bundles),
    "Governed Models": len(governed_models),
}

# Display metrics
cols = st.columns(3)
for i, (key, value) in enumerate(summary_metrics.items()):
    cols[i % 3].metric(key, value)

# Policies Adoption Section
st.markdown("---")
st.header("Policies Adoption")
policies = {d.get("policyId"): d.get("policyName") for d in governed_bundles if d.get("policyId")}

if policies:
    for policy_id, policy_name in policies.items():
        st.subheader(policy_name)
        policy_details = fetch_policy_details(policy_id)
        if policy_details:
            stages = policy_details.get("stages", [])
            stage_data = defaultdict(list)
            for deliverable in governed_bundles:
                if deliverable.get("policyId") == policy_id:
                    stage_data[deliverable.get("stage", "Unknown Stage")].append(deliverable["name"])
            for stage, bundles in stage_data.items():
                st.write(f"**{stage}**: {len(bundles)} bundles")
                for bundle in bundles:
                    st.write(f"- {bundle}")

# Governed Bundles Section
st.markdown("---")
st.header("Governed Bundles Details")
for bundle in governed_bundles:
    st.subheader(bundle["name"])
    st.write(f"Policy: {bundle['policyName']}")
    st.write(f"Stage: {bundle.get('stage', 'Unknown')}")
    for target in bundle.get("targets", []):
        if target["type"] == "ModelVersion":
            model_name = target["identifier"]["name"]
            version = target["identifier"]["version"]
            link = f"{API_HOST}/u/{target['createdBy']['userName']}/{model_name}/model-registry/{model_name}/model-card?version={version}"
            st.write(f"- Model: [{model_name} v{version}]({link})")

# Models Overview Section
st.markdown("---")
st.header("Models Overview")
for model in models:
    governed = any(
        (target["identifier"]["name"], target["identifier"]["version"]) == (model["name"], model.get("latestVersion"))
        for d in governed_bundles
        for target in d.get("targets", [])
        if target["type"] == "ModelVersion"
    )
    st.subheader(model["name"])
    st.write(f"Project: {model['project']['name']}")
    st.write(f"Owner: {model['ownerUsername']}")
    st.write(f"Governed Bundle: {'Yes' if governed else 'No'}")