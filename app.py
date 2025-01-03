import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables Dashboard")

# Sidebar information
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch deliverables from the API
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            auth=(API_KEY, API_KEY),
        )
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Function to fetch approvals from the API
@st.cache_data
def get_approval_status():
    try:
        response = requests.get(f"{API_HOST}/governance/approvals", headers={"Authorization": f"Bearer {API_KEY}"})
        if response.status_code != 200:
            st.error(f"Error fetching approvals: {response.status_code}")
            return []
        return response.json().get("approvals", [])
    except Exception as e:
        st.error(f"An error occurred while fetching approvals: {e}")
        return []

# Function to fetch registered models from the API
@st.cache_data
def get_registered_models():
    try:
        response = requests.get(f"{API_HOST}/mlflow/registered-models", headers={"Authorization": f"Bearer {API_KEY}"})
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code}")
            return []
        return response.json().get("models", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

# Function to count governed models
def count_governed_models(registered_models, bundles):
    governed_models = set()
    for bundle in bundles:
        for target in bundle.get("targets", []):
            if target.get("type") == "ModelVersion":
                model_name = target.get("identifier", {}).get("name")
                if model_name in registered_models:
                    governed_models.add(model_name)
    return len(governed_models)

# Function to calculate project policy stats
def calculate_project_policy_stats(deliverables):
    total_projects = len(set(bundle.get("projectName", "Unknown") for bundle in deliverables))
    projects_with_policies = len(set(bundle.get("projectName") for bundle in deliverables if bundle.get("policyName")))
    projects_without_policies = total_projects - projects_with_policies

    with_policies_pct = (projects_with_policies / total_projects) * 100 if total_projects > 0 else 0
    without_policies_pct = 100 - with_policies_pct

    return total_projects, projects_with_policies, projects_without_policies, with_policies_pct, without_policies_pct

# Function to plot stages for policies
def plot_policy_stages(policy_name, stages):
    stage_names = list(stages.keys())
    stage_counts = [len(bundles) for bundles in stages.values()]

    fig, ax = plt.subplots()
    ax.bar(stage_names, stage_counts, color="skyblue")
    ax.set_title(f"Stage Tracking for Policy: {policy_name}")
    ax.set_xlabel("Stages")
    ax.set_ylabel("Number of Bundles")
    return fig

# Main dashboard logic
if not API_KEY:
    st.error("API Key is missing. Set the environment variable and restart the app.")
else:
    data = fetch_deliverables()
    if data:
        deliverables = data.get("data", [])
        if not deliverables:
            st.warning("No deliverables found.")
        else:
            # Summary section
            total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
            total_bundles = len(deliverables)

            # Additional metrics
            bundles_by_stage = defaultdict(int)
            bundles_by_status = defaultdict(int)
            for bundle in deliverables:
                bundles_by_stage[bundle.get("stage", "Unknown")] += 1
                bundles_by_status[bundle.get("state", "Unknown")] += 1

            # Registered models and governed models
            registered_models = [model["name"] for model in get_registered_models()]
            governed_model_count = count_governed_models(registered_models, deliverables)

            # Project stats
            total_projects, with_policies, without_policies, with_policies_pct, without_policies_pct = calculate_project_policy_stats(deliverables)

            # Summary Section with Metrics
            st.markdown("---")
            st.header("Summary")
            cols = st.columns(4)  # Create 4 evenly spaced columns for metrics
            cols[0].metric("Total Policies", total_policies)
            cols[1].metric("Total Bundles", total_bundles)
            cols[2].metric("Governed Models", governed_model_count)
            cols[3].metric("Total Projects", total_projects)

            # Bundles by Stage as Metrics
            st.subheader("Bundles by Stage")
            stage_cols = st.columns(len(bundles_by_stage))
            for i, (stage, count) in enumerate(bundles_by_stage.items()):
                stage_cols[i].metric(stage, count)

            # Bundles by Status as Metrics
            st.subheader("Bundles by Status")
            status_cols = st.columns(len(bundles_by_status))
            for i, (status, count) in enumerate(bundles_by_status.items()):
                status_cols[i].metric(status, count)

            # Projects with/without policies
            st.subheader("Projects with/without Policies")
            project_cols = st.columns(2)
            project_cols[0].metric("Projects with Policies", f"{with_policies} ({with_policies_pct:.1f}%)")
            project_cols[1].metric("Projects without Policies", f"{without_policies} ({without_policies_pct:.1f}%)")

            # Approval Section
            st.markdown("---")
            st.header("Pending Approvals")
            approvals = get_approval_status()
            pending_approvals = [approval for approval in approvals if approval["status"] == "Pending"]
            if pending_approvals:
                for approval in pending_approvals:
                    st.write(f"- {approval['bundleName']} (Policy: {approval['policyName']})")
            else:
                st.write("No pending approvals.")

            # Display bundles by policy and stage
            st.markdown("---")
            st.header("Bundles by Policy and Stage")
            bundles_per_policy_stage = defaultdict(lambda: defaultdict(list))
            for bundle in deliverables:
                policy_name = bundle.get("policyName", "No Policy Name")
                bundle_stage = bundle.get("stage", "No Stage")
                bundles_per_policy_stage[policy_name][bundle_stage].append(bundle)

            for policy_name, stages in bundles_per_policy_stage.items():
                policy_id = next(
                    (bundle.get("policyId") for bundle in deliverables if bundle.get("policyName") == policy_name),
                    "unknown",
                )
                policy_link = f"{API_HOST}/governance/policy/{policy_id}/editor"
                st.subheader(f"Policy: {policy_name}")
                st.markdown(f"[View Policy]({policy_link})", unsafe_allow_html=True)

                # Plot stages for the policy
                fig = plot_policy_stages(policy_name, stages)
                st.pyplot(fig)

                # Expandable sections for stages
                for stage, bundles in stages.items():
                    with st.expander(f"{stage} ({len(bundles)})"):
                        for bundle in bundles:
                            bundle_name = bundle.get("name", "Unnamed Bundle")
                            bundle_id = bundle.get("id", "")
                            project_owner = bundle.get("projectOwner", "unknown_user")
                            project_name = bundle.get("projectName", "unknown_project")
                            bundle_link = f"{API_HOST}/u/{project_owner}/{project_name}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
                            st.markdown(f"- [{bundle_name}]({bundle_link})", unsafe_allow_html=True)