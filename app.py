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
st.sidebar.markdown("[Models](#models)", unsafe_allow_html=True)

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Fetch deliverables
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

# Fetch registered models
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

# Fetch policy details
def fetch_policy_details(policy_id):
    try:
        url = f"{API_HOST}/guardrails/v1/policies/{policy_id}"
        response = requests.get(url, auth=(API_KEY, API_KEY))
        if response.status_code != 200:
            st.error(f"Error fetching policy details for {policy_id}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching policy details for {policy_id}: {e}")
        return None

# Parse deliverable targets
def parse_targets(deliverables):
    targets_by_deliverable = defaultdict(list)
    for deliverable in deliverables:
        targets = deliverable.get("targets", [])
        for target in targets:
            if target.get("type") == "ModelVersion":
                identifier = target.get("identifier", {})
                model_name = identifier.get("name", "Unknown Model")
                version = identifier.get("version", "Unknown Version")
                created_by = target.get("createdBy", {}).get("userName", "unknown_user")
                targets_by_deliverable[deliverable["id"]].append({
                    "name": model_name,
                    "version": version,
                    "link": f"{API_HOST}/u/{created_by}/{deliverable.get('projectName', 'Unknown Project')}/model-registry/{model_name}/model-card?version={version}",
                })
    return targets_by_deliverable

# Visualize policy stages
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

# Main Dashboard Logic
deliverables = fetch_deliverables()
models = fetch_registered_models()
deliverable_targets = parse_targets(deliverables)

if deliverables:
    # Summary Section
    st.markdown("---")
    st.header("Summary")
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    governed_bundles = len([d for d in deliverables if d.get("policyName")])

    cols = st.columns(3)
    cols[0].metric("Total Policies", total_policies)
    cols[1].metric("Total Bundles", total_bundles)
    cols[2].metric("Governed Bundles", governed_bundles)

    # Policies Adoption Section
    st.markdown("---")
    st.header("Policies Adoption")
    policies = {bundle.get("policyId"): bundle.get("policyName") for bundle in deliverables if bundle.get("policyId")}

    for policy_id, policy_name in policies.items():
        st.subheader(f"Policy: {policy_name}")
        policy_details = fetch_policy_details(policy_id)
        if policy_details:
            stages = policy_details.get("stages", [])
            bundle_data_per_stage = defaultdict(list)
            for deliverable in deliverables:
                if deliverable.get("policyId") == policy_id:
                    stage_name = deliverable.get("stage", "Unknown Stage")
                    bundle_data_per_stage[stage_name].append({
                        "name": deliverable.get("name", "Unnamed Bundle"),
                        "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A"),
                    })
            fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
            st.pyplot(fig)

    # Governed Bundles Section
    st.markdown("---")
    st.header("Governed Bundles Details")
    for deliverable in deliverables:
        bundle_name = deliverable.get("name", "Unnamed Bundle")
        project_name = deliverable.get("projectName", "Unknown Project")
        bundle_link = f"{API_HOST}/u/{deliverable.get('createdBy', {}).get('userName', 'unknown_user')}/{project_name}/overview"

        st.subheader(f"Bundle: {bundle_name}")
        st.write(f"**Project:** {project_name}")
        st.markdown(f"[View Bundle Overview]({bundle_link})", unsafe_allow_html=True)

        # Associated Targets
        targets = deliverable_targets.get(deliverable["id"], [])
        if targets:
            st.write("**Associated Targets:**")
            for target in targets:
                st.write(f"- **Model Name:** {target['name']}, **Version:** {target['version']}")
                st.markdown(f"[View Model Version]({target['link']})", unsafe_allow_html=True)
        else:
            st.write("No associated targets.")
        st.write("---")

    # Models Section
    st.markdown("---")
    st.header("Models")
    for model in models:
        model_name = model.get("name", "Unnamed Model")
        project_name = model.get("project", {}).get("name", "Unknown Project")
        owner_username = model.get("ownerUsername", "Unknown Owner")
        model_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"

        # Governed Bundle Mapping
        governed_bundle = next(
            (deliverable.get("name") for deliverable in deliverables if any(
                t["name"] == model_name for t in deliverable_targets.get(deliverable["id"], [])
            )),
            "Not Governed",
        )

        st.write(f"- **Model Name:** {model_name}, **Project:** {project_name}, **Owner:** {owner_username}")
        st.write(f"  **Governed Bundle:** {governed_bundle}")
        st.markdown(f"[View Model Details]({model_link})", unsafe_allow_html=True)
else:
    st.warning("No deliverables or models found.")