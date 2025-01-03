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

# Function to fetch all stages for a policy
@st.cache_data
def fetch_policy_stages(policy_id):
    try:
        response = requests.get(f"{API_HOST}/governance/policy/{policy_id}/editor", headers={"Authorization": f"Bearer {API_KEY}"})
        if response.status_code != 200:
            st.error(f"Error fetching policy stages: {response.status_code}")
            return []
        policy_data = response.json()
        return [stage["name"] for stage in policy_data.get("stages", [])]
    except Exception as e:
        st.error(f"An error occurred while fetching policy stages: {e}")
        return []

# Function to plot stages for policies
def plot_policy_stages(policy_name, stages, all_stages):
    stage_counts = {stage: len(stages.get(stage, [])) for stage in all_stages}

    fig, ax = plt.subplots()
    ax.bar(stage_counts.keys(), stage_counts.values(), color="skyblue")
    ax.set_title(f"Stage Tracking for Policy: {policy_name}")
    ax.set_xlabel("Stages")
    ax.set_ylabel("Number of Bundles")
    plt.xticks(rotation=45)
    return fig

# Fetch deliverables
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

            # Summary Section with Metrics
            st.markdown("---")
            st.header("Summary")
            cols = st.columns(4)  # Create 4 evenly spaced columns for metrics
            cols[0].metric("Total Policies", total_policies)
            cols[1].metric("Total Bundles", total_bundles)

            # Bundles by Stage as Metrics
            stage_metrics = list(bundles_by_stage.items())
            for i, (stage, count) in enumerate(stage_metrics):
                cols[(i + 2) % 4].metric(stage, count)

            # Bundles by Status as Metrics
            status_metrics = list(bundles_by_status.items())
            for i, (status, count) in enumerate(status_metrics):
                cols[(i + len(stage_metrics) + 2) % 4].metric(status, count)

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
                # Corrected policy deep link
                policy_link = f"{API_HOST}/governance/policy/{policy_id}/editor"
                st.subheader(f"Policy: {policy_name}")
                st.markdown(f"[View Policy]({policy_link})", unsafe_allow_html=True)

                # Fetch all stages from the policy editor
                all_stages = fetch_policy_stages(policy_id)

                # Plot stages for the policy
                fig = plot_policy_stages(policy_name, stages, all_stages)
                st.pyplot(fig)

                # Expandable sections for stages
                for stage in all_stages:
                    bundle_list = stages.get(stage, [])
                    with st.expander(f"{stage} ({len(bundle_list)})"):
                        for bundle in bundle_list:
                            bundle_name = bundle.get("name", "Unnamed Bundle")
                            bundle_id = bundle.get("id", "")
                            project_owner = bundle.get("projectOwner", "unknown_user")
                            project_name = bundle.get("projectName", "unknown_project")
                            bundle_link = (
                                f"{API_HOST}/u/{project_owner}/{project_name}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
                            )
                            st.markdown(f"- [{bundle_name}]({bundle_link})", unsafe_allow_html=True)