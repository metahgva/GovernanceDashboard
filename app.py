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

# Function to fetch all projects
@st.cache_data
def fetch_all_projects():
    try:
        url = f"{API_HOST}/v4/projects"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching projects: {response.status_code} - {response.text}")
            return []
        return response.json()  # The API response is a list of projects
    except Exception as e:
        st.error(f"An error occurred while fetching projects: {e}")
        return []

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

# Main dashboard logic
if not API_KEY:
    st.error("API Key is missing. Set the environment variable and restart the app.")
else:
    # Fetch all projects
    all_projects = fetch_all_projects()
    all_project_ids = {project["id"] for project in all_projects}
    all_project_names = {project["name"]: project["id"] for project in all_projects}

    # Fetch deliverables
    data = fetch_deliverables()
    if data:
        deliverables = data.get("data", [])
        if not deliverables:
            st.warning("No deliverables found.")
        else:
            # Get the list of projects with bundles
            projects_with_bundles_ids = set(
                bundle.get("projectId") for bundle in deliverables if bundle.get("projectId")
            )

            # Find projects without bundles
            projects_without_bundles_ids = all_project_ids - projects_with_bundles_ids
            projects_without_bundles = [
                project["name"]
                for project in all_projects
                if project["id"] in projects_without_bundles_ids
            ]

            # Summary Section
            total_projects = len(all_project_ids)
            projects_with_bundles_count = len(projects_with_bundles_ids)
            projects_without_bundles_count = len(projects_without_bundles)
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
            cols = st.columns(4)
            cols[0].metric("Total Policies", total_policies)
            cols[1].metric("Total Bundles", total_bundles)
            cols[2].metric("Projects With Bundles", projects_with_bundles_count)
            cols[3].metric("Projects Without Bundles", projects_without_bundles_count)

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

            # Projects Without Bundles Section
            st.markdown("---")
            st.header("Projects Without Bundles")
            with st.expander("View Projects Without Bundles"):
                for project in projects_without_bundles:
                    project_id = all_project_names.get(project, "unknown")
                    project_link = f"{API_HOST}/u/{project_id}"  # Generate project link
                    st.markdown(f"- [{project}]({project_link})", unsafe_allow_html=True)

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

                for stage, bundles in stages.items():
                    with st.expander(f"{stage} ({len(bundles)})"):
                        for bundle in bundles:
                            bundle_name = bundle.get("name", "Unnamed Bundle")
                            bundle_id = bundle.get("id", "")
                            project_owner = bundle.get("projectOwner", "unknown_user")
                            project_name = bundle.get("projectName", "unknown_project")
                            bundle_link = (
                                f"{API_HOST}/u/{project_owner}/{project_name}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
                            )
                            st.markdown(f"- [{bundle_name}]({bundle_link})", unsafe_allow_html=True)