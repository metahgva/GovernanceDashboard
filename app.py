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
st.sidebar.markdown("[Governed Bundles](#governed-bundles)", unsafe_allow_html=True)
st.sidebar.markdown("[Projects Without Bundles](#projects-without-bundles)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Detailed Bundles](#detailed-bundles)", unsafe_allow_html=True)

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
            return None
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching deliverables: {e}")
        return None

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

# Function to calculate project stats
def calculate_project_stats(all_projects, deliverables):
    quick_start_projects = [
        project for project in all_projects if "quick-start" in project["name"].lower()
    ]
    quick_start_project_ids = {project["id"] for project in quick_start_projects}

    non_quick_start_projects = [
        project for project in all_projects if project["id"] not in quick_start_project_ids
    ]

    bundled_projects = {bundle.get("projectName", "unknown_project") for bundle in deliverables}
    projects_without_bundles = [
        project for project in non_quick_start_projects if project["name"] not in bundled_projects
    ]

    return non_quick_start_projects, quick_start_projects, projects_without_bundles

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

if deliverables:
    # Summary Section
    st.markdown("---")
    st.header("Summary")
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)

    cols = st.columns(2)
    cols[0].metric("Total Policies", total_policies)
    cols[1].metric("Total Bundles", total_bundles)

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
                    # Collect bundle data per stage
                    bundle_data_per_stage = defaultdict(list)
                    for deliverable in deliverables:
                        if deliverable.get("policyId") == policy_id:
                            stage_name = deliverable.get("stage", "Unknown Stage")
                            bundle_data_per_stage[stage_name].append({
                                "name": deliverable.get("name", "Unnamed Bundle"),
                                "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A")
                            })

                    # Plot the stages and bundles
                    fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
                    st.pyplot(fig)

                    # List bundles in each stage
                    for stage_name, bundles in bundle_data_per_stage.items():
                        st.write(f"- **Stage: {stage_name}** ({len(bundles)})")
                        with st.expander(f"View Bundles in {stage_name}"):
                            for bundle in bundles:
                                st.write(f"- {bundle['name']} (Moved: {bundle['stageUpdateTime']})")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch details for policy {policy_name}.")
else:
    st.warning("No deliverables found or an error occurred.")