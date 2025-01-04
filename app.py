import streamlit as st
import requests
import os
from collections import defaultdict

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
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching deliverables: {e}")
        return None

# Function to fetch policy details using the Guardrails `/policies/{id}` endpoint
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

# Function to calculate bundles by policy and stage
def calculate_policy_stages(deliverables):
    bundles_per_policy_stage = defaultdict(lambda: defaultdict(list))
    for bundle in deliverables:
        policy_name = bundle.get("policyName", "No Policy Name")
        bundle_stage = bundle.get("stage", "No Stage")
        bundles_per_policy_stage[policy_name][bundle_stage].append(bundle)
    return bundles_per_policy_stage

# Main Dashboard Logic
all_projects = fetch_all_projects()
deliverables_data = fetch_deliverables()

if not all_projects:
    st.error("No projects retrieved from the API.")
else:
    if deliverables_data:
        deliverables = deliverables_data.get("data", [])
        if not deliverables:
            st.warning("No deliverables found.")
        else:
            # Summary Section
            st.markdown("---")
            st.header("Summary")
            total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
            total_bundles = len(deliverables)
            non_quick_start_projects, quick_start_projects, projects_without_bundles = calculate_project_stats(
                all_projects, deliverables
            )
            total_projects = len(non_quick_start_projects)
            total_bundled_projects = len(non_quick_start_projects) - len(projects_without_bundles)
            total_projects_without_bundles = len(projects_without_bundles)
            quick_start_count = len(quick_start_projects)

            cols = st.columns(4)
            cols[0].metric("Total Policies", total_policies)
            cols[1].metric("Total Bundles", total_bundles)
            cols[2].metric("Projects with Bundles", total_bundled_projects)
            cols[3].metric("Projects without Bundles", total_projects_without_bundles)

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
                            st.write(f"**Stages for Policy {policy_name}:**")
                            for stage in stages:
                                stage_name = stage["name"]
                                bundles_in_stage = [
                                    bundle for bundle in deliverables
                                    if bundle.get("policyId") == policy_id and bundle.get("stage") == stage_name
                                ]
                                st.write(f"- **Stage: {stage_name}** ({len(bundles_in_stage)})")
                                with st.expander(f"View Bundles in {stage_name}"):
                                    for bundle in bundles_in_stage:
                                        bundle_name = bundle.get("name", "Unnamed Bundle")
                                        project_name = bundle.get("projectName", "unknown_project")
                                        owner_username = bundle.get("createdBy", {}).get("username", "unknown_user")
                                        bundle_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"
                                        st.markdown(f"- [{bundle_name}]({bundle_link})", unsafe_allow_html=True)
                        else:
                            st.warning(f"No stages found for policy {policy_name}.")
                    else:
                        st.error(f"Could not fetch details for policy {policy_name}.")

            # Projects Without Bundles Section
            st.markdown("---")
            st.header("Projects Without Bundles")
            if not projects_without_bundles:
                st.write("All projects have bundles.")
            else:
                with st.expander(f"Projects Without Bundles ({len(projects_without_bundles)})"):
                    for project in projects_without_bundles:
                        project_name = project.get("name", "unknown_project")
                        owner_username = project.get("ownerUsername", "unknown_user")
                        project_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"
                        st.markdown(f"- [{project_name}]({project_link})", unsafe_allow_html=True)

            # Governed Bundles Section
            st.markdown("---")
            st.header("Governed Bundles Details")
            for deliverable in deliverables:
                bundle_name = deliverable.get("name", "Unnamed Bundle")
                status = deliverable.get("state", "Unknown")
                policy_name = deliverable.get("policyName", "Unknown")
                stage = deliverable.get("stage", "Unknown")
                project_name = deliverable.get("projectName", "Unnamed Project")
                owner_username = deliverable.get("createdBy", {}).get("username", "unknown_user")
                bundle_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"
                st.subheader(bundle_name)
                st.markdown(f"[View Bundle Details]({bundle_link})", unsafe_allow_html=True)
                st.write(f"**Status:** {status}")
                st.write(f"**Policy Name:** {policy_name}")
                st.write(f"**Stage:** {stage}")